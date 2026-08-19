#!/usr/bin/env python3
"""
Mix External Data into Training + Retrain
==========================================
Theo yêu cầu GVHD: cắt 100-200 mẫu từ dữ liệu ngoài nguồn (external)
đưa vào training set để giảm domain shift và cải thiện external accuracy.

Quy trình:
  1. Load toàn bộ internal dataset (data/dataset_samples)
  2. Lấy N mẫu từ external (data/external_vietnamese_test) cho mỗi lớp
  3. Ghép vào train split (KHÔNG để lẫn vào val/test để đo đúng)
  4. Train lại 3 model: cross_scale_attention_lite, aasist_lite, cbam_resnet_lite
  5. Đánh giá lại trên toàn bộ external (phần KHÔNG dùng để train)
  6. So sánh trước/sau

Chạy:
  python ml/mix_external_and_retrain.py
  python ml/mix_external_and_retrain.py --mix-per-class 150 --epochs 12 --seed 42
"""
from __future__ import annotations

import argparse
import json
import random
import wave
from pathlib import Path

import numpy as np
import tensorflow as tf
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score, recall_score,
    roc_auc_score, roc_curve,
)
from sklearn.model_selection import train_test_split


# ---------------------------------------------------------------------------
# Audio I/O (reused from existing scripts)
# ---------------------------------------------------------------------------
def load_wave_numpy(path: str, target_sr: int = 16000) -> np.ndarray:
    with wave.open(path, "rb") as wf:
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
    if sample_width != 2:
        raise ValueError(f"Unsupported sample width: {path}")
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    audio = audio / float(np.iinfo(np.int16).max)
    if sample_rate != target_sr:
        tgt = max(1, int(round(len(audio) / sample_rate * target_sr)))
        src_idx = np.linspace(0, len(audio) - 1, len(audio), dtype=np.float32)
        tgt_idx = np.linspace(0, len(audio) - 1, tgt, dtype=np.float32)
        audio = np.interp(tgt_idx, src_idx, audio).astype(np.float32)
    return audio


# ---------------------------------------------------------------------------
# Collect file paths
# ---------------------------------------------------------------------------
def collect_files(root: Path, seed: int, limit: int = 0) -> tuple[list[str], list[int]]:
    rng = random.Random(seed)
    paths, labels = [], []
    for label_name, label in (("bonafide", 0), ("spoof", 1)):
        d = root / label_name
        if not d.exists():
            continue
        files = sorted(str(p) for p in d.rglob("*.wav"))
        if limit > 0:
            rng.shuffle(files)
            files = files[:limit]
        paths.extend(files)
        labels.extend([label] * len(files))
    return paths, labels


# ---------------------------------------------------------------------------
# TF Dataset builder (mirrors benchmark_android_models.py)
# ---------------------------------------------------------------------------
SAMPLE_RATE   = 16000
MAX_DUR_SEC   = 4.0
TARGET_LEN    = int(SAMPLE_RATE * MAX_DUR_SEC)
N_MFCC        = 40
N_FFT         = 512
HOP_LENGTH    = 160


def _load_pad(path: tf.Tensor) -> tf.Tensor:
    audio = tf.py_function(
        func=lambda p: load_wave_numpy(p.numpy().decode(), SAMPLE_RATE),
        inp=[path], Tout=tf.float32,
    )
    audio.set_shape([None])
    audio = audio[:TARGET_LEN]
    pad = tf.maximum(0, TARGET_LEN - tf.shape(audio)[0])
    return tf.pad(audio, [[0, pad]])


def _augment(audio: tf.Tensor) -> tf.Tensor:
    gain = tf.random.uniform([], -6.0, 6.0)
    audio = audio * tf.pow(10.0, gain / 20.0)
    max_shift = tf.cast(tf.round(0.10 * TARGET_LEN), tf.int32)
    shift = tf.random.uniform([], -max_shift, max_shift + 1, dtype=tf.int32)
    audio = tf.roll(audio, shift=shift, axis=0)
    rms = tf.sqrt(tf.reduce_mean(tf.square(audio)) + 1e-8)
    snr = tf.random.uniform([], 12.0, 30.0)
    noise_rms = rms / tf.pow(10.0, snr / 20.0)
    noise = tf.random.normal(tf.shape(audio), stddev=noise_rms)
    audio = tf.cond(tf.random.uniform([]) < 0.75, lambda: audio + noise, lambda: audio)
    return tf.clip_by_value(audio, -1.0, 1.0)


def _audio_to_features(audio: tf.Tensor) -> tf.Tensor:
    """Log-Mel spectrogram features (same as benchmark_android_models.py)."""
    stft = tf.signal.stft(audio, frame_length=N_FFT, frame_step=HOP_LENGTH, pad_end=True)
    power = tf.square(tf.abs(stft))
    num_mel = 80
    lin_to_mel = tf.signal.linear_to_mel_weight_matrix(
        num_mel_bins=num_mel, num_spectrogram_bins=N_FFT // 2 + 1,
        sample_rate=SAMPLE_RATE, lower_edge_hertz=80.0, upper_edge_hertz=7600.0,
    )
    mel = tf.matmul(power, lin_to_mel)
    log_mel = tf.math.log(mel + 1e-6)  # [T, 80]
    return log_mel


def _acoustic_features(audio: tf.Tensor) -> tf.Tensor:
    """8 hand-crafted features (same as existing pipeline)."""
    rms = tf.sqrt(tf.reduce_mean(tf.square(audio)) + 1e-8)
    mean_abs = tf.reduce_mean(tf.abs(audio))
    signs = tf.cast(audio < 0, tf.float32)
    zcr = tf.reduce_mean(tf.abs(signs[1:] - signs[:-1]))
    peak = tf.reduce_max(tf.abs(audio))
    crest = tf.clip_by_value(peak / (rms + 1e-8), 0.0, 10.0)
    clipping = tf.reduce_mean(tf.cast(tf.abs(audio) > 0.98, tf.float32))
    dyn_range = tf.reduce_max(audio) - tf.reduce_min(audio)
    dur = tf.cast(tf.shape(audio)[0], tf.float32) / SAMPLE_RATE
    return tf.stack([rms, mean_abs, zcr, peak, crest, clipping, dyn_range, dur])


def make_dataset(paths, labels, augment: bool, batch_size: int, seed: int) -> tf.data.Dataset:
    ds = tf.data.Dataset.from_tensor_slices((paths, labels))
    if augment:
        ds = ds.shuffle(len(paths), seed=seed)

    def process(path, label):
        audio = _load_pad(path)
        if augment:
            audio = _augment(audio)
        spec = _audio_to_features(audio)          # [T, 80]
        acou = _acoustic_features(audio)           # [8]
        return (spec, acou), tf.cast(label, tf.float32)

    return (
        ds.map(process, num_parallel_calls=tf.data.AUTOTUNE)
          .batch(batch_size)
          .prefetch(tf.data.AUTOTUNE)
    )


# ---------------------------------------------------------------------------
# Model builders (simplified from benchmark_android_models.py)
# ---------------------------------------------------------------------------
def build_cross_scale_attention_lite(input_shape, n_acoustic=8):
    spec_in = tf.keras.Input(shape=input_shape, name="spec")
    acou_in = tf.keras.Input(shape=(n_acoustic,), name="acoustic")

    x = tf.keras.layers.Conv2D(16, 3, padding="same", activation="relu")(
        tf.keras.layers.Reshape((*input_shape, 1))(spec_in))
    x = tf.keras.layers.MaxPooling2D(2)(x)
    x = tf.keras.layers.Conv2D(32, 3, padding="same", activation="relu")(x)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)

    a = tf.keras.layers.Dense(32, activation="relu")(acou_in)
    fused = tf.keras.layers.Concatenate()([x, a])
    fused = tf.keras.layers.Dense(64, activation="relu")(fused)
    fused = tf.keras.layers.Dropout(0.3)(fused)
    out = tf.keras.layers.Dense(1)(fused)

    model = tf.keras.Model(inputs=[spec_in, acou_in], outputs=out,
                           name="cross_scale_attention_lite")
    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-3),
        loss=tf.keras.losses.BinaryCrossentropy(from_logits=True),
        metrics=[tf.keras.metrics.BinaryAccuracy(name="accuracy")],
    )
    return model


def build_aasist_lite(input_shape, n_acoustic=8):
    spec_in = tf.keras.Input(shape=input_shape, name="spec")
    acou_in = tf.keras.Input(shape=(n_acoustic,), name="acoustic")

    x = tf.keras.layers.Conv2D(8, 3, padding="same", activation="relu")(
        tf.keras.layers.Reshape((*input_shape, 1))(spec_in))
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    a = tf.keras.layers.Dense(16, activation="relu")(acou_in)
    fused = tf.keras.layers.Concatenate()([x, a])
    fused = tf.keras.layers.Dense(32, activation="relu")(fused)
    out = tf.keras.layers.Dense(1)(fused)

    model = tf.keras.Model(inputs=[spec_in, acou_in], outputs=out,
                           name="aasist_lite")
    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-3),
        loss=tf.keras.losses.BinaryCrossentropy(from_logits=True),
        metrics=[tf.keras.metrics.BinaryAccuracy(name="accuracy")],
    )
    return model


def build_cbam_resnet_lite(input_shape, n_acoustic=8):
    spec_in = tf.keras.Input(shape=input_shape, name="spec")
    acou_in = tf.keras.Input(shape=(n_acoustic,), name="acoustic")

    x = tf.keras.layers.Reshape((*input_shape, 1))(spec_in)
    shortcut = tf.keras.layers.Conv2D(32, 1, padding="same")(x)
    x = tf.keras.layers.Conv2D(32, 3, padding="same", activation="relu")(x)
    x = tf.keras.layers.Conv2D(32, 3, padding="same")(x)
    x = tf.keras.layers.Add()([x, shortcut])
    x = tf.keras.layers.ReLU()(x)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    a = tf.keras.layers.Dense(32, activation="relu")(acou_in)
    fused = tf.keras.layers.Concatenate()([x, a])
    fused = tf.keras.layers.Dense(64, activation="relu")(fused)
    fused = tf.keras.layers.Dropout(0.3)(fused)
    out = tf.keras.layers.Dense(1)(fused)

    model = tf.keras.Model(inputs=[spec_in, acou_in], outputs=out,
                           name="cbam_resnet_lite")
    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-3),
        loss=tf.keras.losses.BinaryCrossentropy(from_logits=True),
        metrics=[tf.keras.metrics.BinaryAccuracy(name="accuracy")],
    )
    return model


MODEL_BUILDERS = {
    "cross_scale_attention_lite": build_cross_scale_attention_lite,
    "aasist_lite":                build_aasist_lite,
    "cbam_resnet_lite":           build_cbam_resnet_lite,
}


# ---------------------------------------------------------------------------
# Evaluation helpers
# ---------------------------------------------------------------------------
def predict_probs(model, ds) -> tuple[np.ndarray, np.ndarray]:
    all_logits, all_labels = [], []
    for (spec_b, acou_b), lbl_b in ds:
        logits = model([spec_b, acou_b], training=False).numpy().reshape(-1)
        all_logits.append(logits)
        all_labels.append(lbl_b.numpy())
    logits = np.concatenate(all_logits)
    labels = np.concatenate(all_labels).astype(np.int32)
    probs = 1.0 / (1.0 + np.exp(-logits))
    return probs, labels


def compute_eer(fpr, tpr):
    fnr = 1 - tpr
    idx = np.argmin(np.abs(fpr - fnr))
    return float((fpr[idx] + fnr[idx]) / 2)


def evaluate_probs(probs, labels, threshold=0.5):
    pred = (probs >= threshold).astype(np.int32)
    tn = int(np.sum((pred == 0) & (labels == 0)))
    fp = int(np.sum((pred == 1) & (labels == 0)))
    fn = int(np.sum((pred == 0) & (labels == 1)))
    tp = int(np.sum((pred == 1) & (labels == 1)))
    try:
        auc = float(roc_auc_score(labels, probs))
        fpr, tpr, _ = roc_curve(labels, probs)
        eer = compute_eer(fpr, tpr)
    except Exception:
        auc, eer = 0.0, 0.0
    return {
        "accuracy":  float(accuracy_score(labels, pred)),
        "precision": float(precision_score(labels, pred, zero_division=0)),
        "recall":    float(recall_score(labels, pred, zero_division=0)),
        "f1":        float(f1_score(labels, pred, zero_division=0)),
        "auc":       auc,
        "eer":       eer,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--internal-root",  default="data/dataset_samples",        type=Path)
    parser.add_argument("--external-root",  default="data/external_vietnamese_test", type=Path)
    parser.add_argument("--output-dir",     default="ml/artifacts/mixed_retrain",   type=Path)
    parser.add_argument("--mix-per-class",  default=150, type=int,
                        help="Số mẫu external mỗi lớp đưa vào training (thầy đề xuất 100-200)")
    parser.add_argument("--epochs",         default=12,  type=int)
    parser.add_argument("--batch-size",     default=32,  type=int)
    parser.add_argument("--seed",           default=42,  type=int)
    args = parser.parse_args()

    tf.random.set_seed(args.seed)
    np.random.seed(args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------- load data
    print("Loading internal dataset...")
    int_paths, int_labels = collect_files(args.internal_root, args.seed)
    print(f"  Internal: {len(int_paths)} files "
          f"(bonafide={int_labels.count(0)}, spoof={int_labels.count(1)})")

    print("Loading external dataset...")
    ext_paths, ext_labels = collect_files(args.external_root, args.seed)
    print(f"  External: {len(ext_paths)} files "
          f"(bonafide={ext_labels.count(0)}, spoof={ext_labels.count(1)})")

    # ---------------------------------------------------------------- split external
    # Lấy mix_per_class mẫu mỗi lớp để đưa vào training
    # Phần còn lại giữ nguyên làm external test set
    rng = random.Random(args.seed)

    ext_by_class = {0: [], 1: []}
    for p, l in zip(ext_paths, ext_labels):
        ext_by_class[l].append(p)

    mix_paths, mix_labels = [], []
    remaining_paths, remaining_labels = [], []

    for label, files in ext_by_class.items():
        shuffled = files[:]
        rng.shuffle(shuffled)
        n_mix = min(args.mix_per_class, len(shuffled))
        mix_paths.extend(shuffled[:n_mix])
        mix_labels.extend([label] * n_mix)
        remaining_paths.extend(shuffled[n_mix:])
        remaining_labels.extend([label] * (len(shuffled) - n_mix))

    print(f"\n  External mẫu đưa vào training: {len(mix_paths)} "
          f"({args.mix_per_class} mỗi lớp)")
    print(f"  External mẫu giữ làm test: {len(remaining_paths)}")

    # ---------------------------------------------------------------- build splits
    # Internal split: 60/20/20
    int_tr, int_te, int_tr_l, int_te_l = train_test_split(
        int_paths, int_labels, test_size=0.2, stratify=int_labels, random_state=args.seed
    )
    int_tr, int_val, int_tr_l, int_val_l = train_test_split(
        int_tr, int_tr_l, test_size=0.2, stratify=int_tr_l, random_state=args.seed
    )

    # Training set = internal train + mixed external
    train_paths  = int_tr + mix_paths
    train_labels = int_tr_l + mix_labels

    # Shuffle combined train
    combined = list(zip(train_paths, train_labels))
    rng.shuffle(combined)
    train_paths, train_labels = zip(*combined)
    train_paths, train_labels = list(train_paths), list(train_labels)

    print(f"\nData splits:")
    print(f"  Train : {len(train_paths)} "
          f"(internal {len(int_tr)} + external mix {len(mix_paths)})")
    print(f"  Val   : {len(int_val)} (internal)")
    print(f"  Test  : {len(int_te)} (internal)")
    print(f"  Ext   : {len(remaining_paths)} (external holdout)")

    # ---------------------------------------------------------------- datasets
    T = TARGET_LEN
    spec_tmp = _audio_to_features(tf.zeros([T]))
    spec_shape = tuple(spec_tmp.shape)
    print(f"\nSpec shape: {spec_shape}")

    train_ds = make_dataset(train_paths, train_labels, augment=True,
                            batch_size=args.batch_size, seed=args.seed)
    val_ds   = make_dataset(int_val, int_val_l, augment=False,
                            batch_size=args.batch_size, seed=args.seed)
    test_ds  = make_dataset(int_te, int_te_l, augment=False,
                            batch_size=args.batch_size, seed=args.seed)
    ext_ds   = make_dataset(remaining_paths, remaining_labels, augment=False,
                            batch_size=args.batch_size, seed=args.seed)

    # ---------------------------------------------------------------- train models
    all_results = {}

    for model_name, builder in MODEL_BUILDERS.items():
        print(f"\n{'='*60}")
        print(f"Training: {model_name}")
        print(f"{'='*60}")

        tf.random.set_seed(args.seed)
        model = builder(spec_shape)
        print(f"  Params: {model.count_params():,}")

        callbacks = [
            tf.keras.callbacks.EarlyStopping(
                monitor="val_loss", patience=4, restore_best_weights=True
            )
        ]
        model.fit(
            train_ds, validation_data=val_ds,
            epochs=args.epochs,
            callbacks=callbacks,
            verbose=1,
        )

        # Evaluate
        print(f"\n  Evaluating on internal test...")
        probs_te, y_te = predict_probs(model, test_ds)
        int_metrics = evaluate_probs(probs_te, y_te)

        print(f"  Evaluating on external holdout...")
        probs_ex, y_ex = predict_probs(model, ext_ds)
        ext_metrics = evaluate_probs(probs_ex, y_ex)

        # TFLite export
        tflite_path = args.output_dir / f"{model_name}.tflite"
        try:
            converter = tf.lite.TFLiteConverter.from_keras_model(model)
            tflite_bytes = converter.convert()
            tflite_path.write_bytes(tflite_bytes)
            tflite_kb = len(tflite_bytes) / 1024
        except Exception as e:
            tflite_kb = -1
            print(f"  [WARN] TFLite export failed: {e}")

        all_results[model_name] = {
            "params":      model.count_params(),
            "tflite_kb":   round(tflite_kb, 1),
            "mix_per_class": args.mix_per_class,
            "internal_test": int_metrics,
            "external_holdout": ext_metrics,
        }

        print(f"\n  Internal  → Acc={int_metrics['accuracy']*100:.2f}%  "
              f"F1={int_metrics['f1']*100:.2f}%  AUC={int_metrics['auc']:.4f}")
        print(f"  External  → Acc={ext_metrics['accuracy']*100:.2f}%  "
              f"F1={ext_metrics['f1']*100:.2f}%  AUC={ext_metrics['auc']:.4f}  "
              f"EER={ext_metrics['eer']*100:.2f}%")
        print(f"  TFLite    → {tflite_kb:.1f} KB")

    # ---------------------------------------------------------------- save results
    out_json = args.output_dir / "mixed_retrain_results.json"
    meta = {
        "mix_per_class":       args.mix_per_class,
        "total_train":         len(train_paths),
        "internal_train":      len(int_tr),
        "external_mixed_in":   len(mix_paths),
        "external_holdout":    len(remaining_paths),
        "val_size":            len(int_val),
        "internal_test_size":  len(int_te),
        "epochs":              args.epochs,
        "seed":                args.seed,
        "models":              all_results,
    }
    out_json.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved: {out_json}")

    # ---------------------------------------------------------------- summary markdown
    md = ["# Kết quả Retrain với Dữ liệu External Trộn vào Training\n",
          f"**Cấu hình:** {args.mix_per_class} mẫu external mỗi lớp được thêm vào training set.\n",
          f"- Train tổng: {len(train_paths)} (internal {len(int_tr)} + external mix {len(mix_paths)})\n",
          f"- External holdout (đánh giá): {len(remaining_paths)} mẫu\n",
          "\n## So sánh Trước và Sau\n",
          "| Model | External Acc (Trước) | External Acc (Sau) | Cải thiện | External AUC (Sau) | EER (Sau) |",
          "|---|---:|---:|---:|---:|---:|",
    ]
    # Kết quả trước (từ REPORT.md đã có)
    before = {
        "cross_scale_attention_lite": 0.5125,
        "aasist_lite":                0.4980,
        "cbam_resnet_lite":           0.4990,
    }
    for name, res in all_results.items():
        ext_acc_after = res["external_holdout"]["accuracy"]
        ext_acc_before = before.get(name, 0.0)
        delta = ext_acc_after - ext_acc_before
        delta_str = f"{delta*100:+.2f}%"
        md.append(
            f"| {name} | {ext_acc_before*100:.2f}% | {ext_acc_after*100:.2f}% | "
            f"**{delta_str}** | {res['external_holdout']['auc']:.4f} | "
            f"{res['external_holdout']['eer']*100:.2f}% |"
        )

    md.append("\n## Chi tiết từng Model\n")
    for name, res in all_results.items():
        md.append(f"### {name}\n")
        it = res["internal_test"]
        ex = res["external_holdout"]
        md.append(f"- Params: {res['params']:,}  |  TFLite: {res['tflite_kb']} KB")
        md.append(f"- Internal test  → Acc={it['accuracy']*100:.2f}%  "
                  f"Precision={it['precision']*100:.2f}%  "
                  f"Recall={it['recall']*100:.2f}%  F1={it['f1']*100:.2f}%")
        md.append(f"- External holdout → Acc={ex['accuracy']*100:.2f}%  "
                  f"Precision={ex['precision']*100:.2f}%  "
                  f"Recall={ex['recall']*100:.2f}%  F1={ex['f1']*100:.2f}%  "
                  f"AUC={ex['auc']:.4f}  EER={ex['eer']*100:.2f}%")
        md.append(f"- Confusion (external): TP={ex['tp']} FP={ex['fp']} "
                  f"FN={ex['fn']} TN={ex['tn']}\n")

    out_md = args.output_dir / "mixed_retrain_summary.md"
    out_md.write_text("\n".join(md), encoding="utf-8")
    print(f"Saved: {out_md}")
    print("\n=== Done ===")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
train_spoof_model_v2.py — 21-feature DNN trainer
=================================================
Mở rộng từ train_spoof_model.py:
  - 8 đặc trưng gốc (giữ nguyên thứ tự)
  - 13 MFCC (mean over frames)     → indices 8–20
  - RIR augmentation (phòng nhỏ/vừa/lớn) để giảm domain shift
  - External data mixing (400 mẫu/lớp mặc định)

Feature order khớp chính xác AudioFeatureExtractor.kt:
  0  RMS | 1  MeanAbs | 2  ZCR | 3  Peak | 4  CrestFactor
  5  ClippingRatio | 6  DynamicRange | 7  ActiveDuration
  8–20  MFCC[0..12]

Chạy:
  python ml/train_spoof_model_v2.py
  python ml/train_spoof_model_v2.py \\
    --dataset-root data/dataset_samples \\
    --external-root data/external_vietnamese_test \\
    --mix-per-class 400 \\
    --output-dir ml/artifacts/v2 \\
    --epochs 40 --seed 42
"""
from __future__ import annotations

import argparse
import json
import math
import random
import wave
from pathlib import Path
from typing import List, Tuple

import numpy as np
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score, roc_curve
from sklearn.model_selection import train_test_split
import tensorflow as tf

# ──────────────────────────────────────────────────────────────────────────────
# Constants (must match AudioFeatureExtractor.kt exactly)
# ──────────────────────────────────────────────────────────────────────────────
FEATURE_SIZE     = 21
PRE_EMPHASIS     = 0.97
FRAME_LENGTH     = 512      # ~32 ms @ 16 kHz
HOP_LENGTH       = 160      # ~10 ms @ 16 kHz
NUM_MEL_FILTERS  = 26
NUM_MFCC         = 13
MEL_LOW_HZ       = 80.0
MEL_HIGH_HZ      = 7600.0
TARGET_SR        = 16000

FEATURE_NAMES = [
    "rms", "mean_abs", "zcr", "peak", "crest_factor",
    "clipping_ratio", "dynamic_range", "active_duration_sec",
    *[f"mfcc_{i}" for i in range(NUM_MFCC)],
]


# ──────────────────────────────────────────────────────────────────────────────
# Audio I/O
# ──────────────────────────────────────────────────────────────────────────────
def load_wav_mono(path: Path) -> Tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wf:
        ch = wf.getnchannels(); sw = wf.getsampwidth(); sr = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
    if sw != 2:
        raise ValueError(f"Unsupported sample width {sw}: {path}")
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
    if ch > 1:
        audio = audio.reshape(-1, ch).mean(axis=1)
    return audio / float(np.iinfo(np.int16).max), sr


def resample_linear(sig: np.ndarray, src: int, tgt: int) -> np.ndarray:
    if src == tgt or sig.size == 0:
        return sig
    n = max(1, int(round(sig.size / src * tgt)))
    return np.interp(np.linspace(0, sig.size - 1, n),
                     np.linspace(0, sig.size - 1, sig.size), sig).astype(np.float32)


# ──────────────────────────────────────────────────────────────────────────────
# Room Impulse Response (RIR) simulation — simple image method
# ──────────────────────────────────────────────────────────────────────────────
def _simulate_rir(room_dim: Tuple[float, float, float],
                  src_pos: Tuple[float, float, float],
                  mic_pos: Tuple[float, float, float],
                  sr: int, rt60: float, n_reflections: int = 200) -> np.ndarray:
    """Simplified image-source model RIR. Good enough for augmentation."""
    c = 343.0
    rir_len = int(sr * rt60 * 2)
    rir = np.zeros(rir_len, dtype=np.float32)

    def dist(a, b):
        return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))

    # Direct path
    d = dist(src_pos, mic_pos)
    t = int(d / c * sr)
    if t < rir_len:
        rir[t] += 1.0 / max(d, 0.01)

    rng = random.Random(42)
    decay = 6.908 / (rt60 * sr)   # per-sample decay (dB)

    for _ in range(n_reflections):
        # Random reflection point on a wall
        axis  = rng.randint(0, 2)
        wall  = rng.choice([0.0, room_dim[axis]])
        image = list(src_pos)
        image[axis] = 2 * wall - src_pos[axis]
        d_img = dist(tuple(image), mic_pos)
        t_img = int(d_img / c * sr)
        if t_img < rir_len:
            gain = np.exp(-decay * t_img) / max(d_img, 0.01)
            rir[t_img] += float(gain)

    return rir / (np.max(np.abs(rir)) + 1e-8)


def apply_rir(signal: np.ndarray, sr: int, room_type: str = "medium") -> np.ndarray:
    """Convolve signal with a random RIR matching the room type."""
    configs = {
        "small":  {"room_dim": (4.0, 3.0, 2.5), "rt60": 0.15, "n_ref": 80},
        "medium": {"room_dim": (7.0, 5.0, 3.0), "rt60": 0.30, "n_ref": 150},
        "large":  {"room_dim": (12.0, 9.0, 4.0), "rt60": 0.55, "n_ref": 200},
    }
    cfg = configs.get(room_type, configs["medium"])
    Lx, Ly, Lz = cfg["room_dim"]
    rng = random.Random()
    src = (rng.uniform(0.5, Lx - 0.5), rng.uniform(0.5, Ly - 0.5), rng.uniform(1.0, 1.8))
    mic = (rng.uniform(0.5, Lx - 0.5), rng.uniform(0.5, Ly - 0.5), rng.uniform(0.9, 1.7))
    rir = _simulate_rir(cfg["room_dim"], src, mic, sr, cfg["rt60"], cfg["n_ref"])
    reverbed = np.convolve(signal, rir)[:len(signal)]
    peak = np.max(np.abs(reverbed))
    return (reverbed / peak * np.max(np.abs(signal))).astype(np.float32) if peak > 1e-6 else signal


def augment(signal: np.ndarray, sr: int, rng: random.Random) -> np.ndarray:
    """Training-time augmentation pipeline."""
    # 1. Random gain ±6 dB
    gain_db = rng.uniform(-6.0, 6.0)
    signal = signal * (10 ** (gain_db / 20.0))

    # 2. Time shift ±10 %
    shift = int(rng.uniform(-0.10, 0.10) * len(signal))
    signal = np.roll(signal, shift)

    # 3. Gaussian noise (SNR 12–30 dB) — 75 % of the time
    if rng.random() < 0.75:
        rms   = float(np.sqrt(np.mean(signal ** 2) + 1e-8))
        snr   = rng.uniform(12.0, 30.0)
        noise = rng.gauss(0, 1)
        signal = signal + np.random.normal(0, rms / (10 ** (snr / 20.0)), len(signal)).astype(np.float32)

    # 4. RIR simulation (room reverb) — 50 % of the time, bonafide only
    if rng.random() < 0.50:
        room = rng.choice(["small", "medium", "large"])
        signal = apply_rir(signal, sr, room)

    return np.clip(signal, -1.0, 1.0).astype(np.float32)


# ──────────────────────────────────────────────────────────────────────────────
# Feature extraction — mirrors AudioFeatureExtractor.kt exactly
# ──────────────────────────────────────────────────────────────────────────────
def _hz_to_mel(hz):  return 2595.0 * np.log10(1.0 + hz / 700.0)
def _mel_to_hz(mel): return 700.0 * (10.0 ** (mel / 2595.0) - 1.0)


def _build_mel_filterbank(sr: int) -> np.ndarray:
    fft_size = 1 << math.ceil(math.log2(FRAME_LENGTH))
    n_bins   = fft_size // 2 + 1
    mel_low  = _hz_to_mel(MEL_LOW_HZ)
    mel_high = _hz_to_mel(min(MEL_HIGH_HZ, sr / 2))
    mel_pts  = np.array([_mel_to_hz(mel_low + i * (mel_high - mel_low) / (NUM_MEL_FILTERS + 1))
                         for i in range(NUM_MEL_FILTERS + 2)])
    bin_pts  = np.floor((fft_size + 1) * mel_pts / sr).astype(int)
    filterbank = np.zeros((NUM_MEL_FILTERS, n_bins))
    for f in range(NUM_MEL_FILTERS):
        for k in range(n_bins):
            if k < bin_pts[f]:
                filterbank[f, k] = 0.0
            elif k <= bin_pts[f + 1]:
                filterbank[f, k] = (k - bin_pts[f]) / (bin_pts[f + 1] - bin_pts[f] + 1e-10)
            elif k <= bin_pts[f + 2]:
                filterbank[f, k] = (bin_pts[f + 2] - k) / (bin_pts[f + 2] - bin_pts[f + 1] + 1e-10)
    return filterbank


_MEL_CACHE: dict = {}


def _get_mel_filterbank(sr: int) -> np.ndarray:
    if sr not in _MEL_CACHE:
        _MEL_CACHE[sr] = _build_mel_filterbank(sr)
    return _MEL_CACHE[sr]


def compute_mfcc_mean(signal: np.ndarray, sr: int) -> np.ndarray:
    if len(signal) < FRAME_LENGTH:
        return np.zeros(NUM_MFCC, dtype=np.float32)

    # Pre-emphasis
    emph = np.concatenate([[signal[0]], signal[1:] - PRE_EMPHASIS * signal[:-1]])

    fft_size = 1 << math.ceil(math.log2(FRAME_LENGTH))
    hamming  = 0.54 - 0.46 * np.cos(2 * np.pi * np.arange(FRAME_LENGTH) / (FRAME_LENGTH - 1))
    mel_fb   = _get_mel_filterbank(sr)
    n_bins   = fft_size // 2 + 1

    mfcc_sum = np.zeros(NUM_MFCC)
    n_frames = 0
    start    = 0
    while start + FRAME_LENGTH <= len(emph):
        frame   = emph[start:start + FRAME_LENGTH] * hamming
        padded  = np.zeros(fft_size)
        padded[:FRAME_LENGTH] = frame
        power   = np.abs(np.fft.rfft(padded)) ** 2   # length = fft_size//2+1
        if len(power) > n_bins:
            power = power[:n_bins]
        elif len(power) < n_bins:
            power = np.pad(power, (0, n_bins - len(power)))

        log_mel = np.log(mel_fb @ power + 1e-10)
        # DCT-II
        for m in range(NUM_MFCC):
            mfcc_sum[m] += np.sum(log_mel * np.cos(
                np.pi * m * (np.arange(NUM_MEL_FILTERS) + 0.5) / NUM_MEL_FILTERS))
        n_frames += 1
        start    += HOP_LENGTH

    return (mfcc_sum / max(n_frames, 1)).astype(np.float32)


def extract_features(signal: np.ndarray, sr: int) -> np.ndarray:
    """21 features matching AudioFeatureExtractor.kt."""
    if signal.size == 0:
        return np.zeros(FEATURE_SIZE, dtype=np.float32)

    rms   = float(np.sqrt(np.mean(signal ** 2)))
    mabs  = float(np.mean(np.abs(signal)))
    signs = np.signbit(signal)
    zcr   = float(np.mean(signs[1:] != signs[:-1])) if signal.size > 1 else 0.0
    peak  = float(np.max(np.abs(signal)))
    crest = float(np.clip(peak / rms, 0, 10)) if rms > 1e-6 else 0.0
    clip  = float(np.mean(np.abs(signal) > 0.98))
    dyn   = float(max(np.max(signal) - np.min(signal), 0))
    dur   = float(signal.size / sr)
    mfcc  = compute_mfcc_mean(signal, sr)

    return np.array([rms, mabs, zcr, peak, crest, clip, dyn, dur, *mfcc], dtype=np.float32)


# ──────────────────────────────────────────────────────────────────────────────
# Dataset helpers
# ──────────────────────────────────────────────────────────────────────────────
def collect_files(root: Path, seed: int, limit: int = 0) -> Tuple[List[str], List[int]]:
    rng = random.Random(seed)
    paths, labels = [], []
    for lname, lbl in (("bonafide", 0), ("spoof", 1)):
        files = sorted(str(p) for p in (root / lname).rglob("*.wav") if (root / lname).exists())
        if limit > 0:
            rng.shuffle(files)
            files = files[:limit]
        paths.extend(files); labels.extend([lbl] * len(files))
    return paths, labels


def build_matrix(paths: List[str], labels: List[int],
                 do_augment: bool, seed: int) -> Tuple[np.ndarray, np.ndarray]:
    rng   = random.Random(seed)
    feats, ys = [], []
    failed = 0
    for path, lbl in zip(paths, labels):
        try:
            sig, sr = load_wav_mono(Path(path))
            sig = resample_linear(sig, sr, TARGET_SR)
            if do_augment:
                sig = augment(sig, TARGET_SR, rng)
            feats.append(extract_features(sig, TARGET_SR))
            ys.append(lbl)
        except Exception:
            failed += 1
    if failed:
        print(f"  [WARN] {failed} files failed to load")
    return np.stack(feats).astype(np.float32), np.array(ys, dtype=np.float32)


# ──────────────────────────────────────────────────────────────────────────────
# Model
# ──────────────────────────────────────────────────────────────────────────────
def build_model(input_dim: int) -> tf.keras.Model:
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(input_dim,)),
        tf.keras.layers.Dense(128, activation="relu"),
        tf.keras.layers.Dropout(0.3),
        tf.keras.layers.Dense(64, activation="relu"),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(32, activation="relu"),
        tf.keras.layers.Dense(1),
    ])
    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-3),
        loss=tf.keras.losses.BinaryCrossentropy(from_logits=True),
        metrics=[tf.keras.metrics.BinaryAccuracy(name="accuracy")],
    )
    return model


def standardize(train_x, other):
    mean = train_x.mean(axis=0, keepdims=True)
    std  = np.where(train_x.std(axis=0, keepdims=True) < 1e-6, 1.0,
                    train_x.std(axis=0, keepdims=True))
    return (train_x - mean) / std, (other - mean) / std, np.concatenate([mean, std])


def evaluate(model, x, y, threshold=0.50):
    from scipy.special import expit
    logits = model.predict(x, verbose=0).reshape(-1)
    probs  = expit(logits.astype(np.float64)).astype(np.float32)
    pred   = (probs >= threshold).astype(np.int32)
    truth  = y.astype(np.int32)
    try:
        auc = float(roc_auc_score(truth, probs))
        fpr, tpr, _ = roc_curve(truth, probs)
        fnr = 1 - tpr
        eer = float((fpr + fnr)[np.argmin(np.abs(fpr - fnr))]) / 2
    except Exception:
        auc = eer = 0.0
    return {
        "accuracy":  float(accuracy_score(truth, pred)),
        "precision": float(precision_score(truth, pred, zero_division=0)),
        "recall":    float(recall_score(truth, pred, zero_division=0)),
        "f1":        float(f1_score(truth, pred, zero_division=0)),
        "auc":       auc, "eer": eer,
        "tp": int(np.sum((pred==1)&(truth==1))),
        "fp": int(np.sum((pred==1)&(truth==0))),
        "fn": int(np.sum((pred==0)&(truth==1))),
        "tn": int(np.sum((pred==0)&(truth==0))),
        "count": int(len(y)),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root",  default="data/dataset_samples",         type=Path)
    parser.add_argument("--external-root", default="data/external_vietnamese_test", type=Path)
    parser.add_argument("--output-dir",    default="ml/artifacts/v2",               type=Path)
    parser.add_argument("--mix-per-class", default=400, type=int)
    parser.add_argument("--epochs",        default=40,  type=int)
    parser.add_argument("--batch-size",    default=32,  type=int)
    parser.add_argument("--seed",          default=42,  type=int)
    parser.add_argument("--from-cache",    action="store_true",
                        help="Load pre-extracted features from ml/artifacts/v2/features_*.npz")
    args = parser.parse_args()

    np.random.seed(args.seed)
    tf.random.set_seed(args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # ── Load feature matrix (from cache or extract fresh) ───────────────
    cache_int = args.output_dir / "features_internal.npz"
    cache_ext = args.output_dir / "features_external.npz"

    if args.from_cache and cache_int.exists():
        print("Loading features from cache...")
        d_int = np.load(cache_int, allow_pickle=True)
        X_all, y_all = d_int["X"].astype(np.float32), d_int["y"].astype(np.float32)
        print(f"  Internal cache: {X_all.shape}")
    else:
        print("Extracting internal features (single-threaded)...")
        int_paths, int_labels = collect_files(args.dataset_root, args.seed)
        print(f"  {len(int_paths)} files")
        X_all, y_all = build_matrix(int_paths, int_labels, do_augment=False, seed=args.seed)
        print(f"  Done: {X_all.shape}")
        args.output_dir.mkdir(parents=True, exist_ok=True)
        np.savez(cache_int, X=X_all, y=y_all)

    # ── Mix external into train ──────────────────────────────────────────
    X_ext_mix = np.zeros((0, FEATURE_SIZE), dtype=np.float32)
    y_ext_mix = np.zeros(0, dtype=np.float32)
    X_ext_holdout = np.zeros((0, FEATURE_SIZE), dtype=np.float32)
    y_ext_holdout = np.zeros(0, dtype=np.float32)

    if args.external_root.exists():
        if args.from_cache and cache_ext.exists():
            print("Loading external cache...")
            d_ext = np.load(cache_ext, allow_pickle=True)
            X_ext_all, y_ext_all = d_ext["X"].astype(np.float32), d_ext["y"].astype(np.float32)
        else:
            print(f"Extracting external features ({args.mix_per_class*2} samples)...")
            ext_paths, ext_labels = collect_files(args.external_root, args.seed)
            X_ext_all, y_ext_all = build_matrix(ext_paths, ext_labels, do_augment=False, seed=args.seed)
            np.savez(cache_ext, X=X_ext_all, y=y_ext_all)

        rng = np.random.default_rng(args.seed)
        mix_idx, hold_idx = [], []
        for lbl in [0, 1]:
            idx = np.where(y_ext_all == lbl)[0]
            rng.shuffle(idx)
            n = min(args.mix_per_class, len(idx))
            mix_idx.extend(idx[:n].tolist())
            hold_idx.extend(idx[n:].tolist())
        X_ext_mix, y_ext_mix = X_ext_all[mix_idx], y_ext_all[mix_idx]
        X_ext_holdout, y_ext_holdout = X_ext_all[hold_idx], y_ext_all[hold_idx]
        print(f"  External mix-in: {len(X_ext_mix)} | holdout: {len(X_ext_holdout)}")

    # ── Train/val/test split (internal) ──────────────────────────────────
    tr_idx, te_idx = train_test_split(np.arange(len(y_all)), test_size=0.2,
                                      stratify=y_all, random_state=args.seed)
    tr_idx, va_idx = train_test_split(tr_idx, test_size=0.2,
                                      stratify=y_all[tr_idx], random_state=args.seed)

    X_tr = np.concatenate([X_all[tr_idx], X_ext_mix])
    y_tr = np.concatenate([y_all[tr_idx], y_ext_mix])
    X_va, y_va = X_all[va_idx], y_all[va_idx]
    X_te, y_te = X_all[te_idx], y_all[te_idx]
    X_ext_n_data, y_ext_n_data = X_ext_holdout, y_ext_holdout

    # Shuffle train
    perm = np.random.RandomState(args.seed).permutation(len(y_tr))
    X_tr, y_tr = X_tr[perm], y_tr[perm]

    print(f"\nSplits: train={len(y_tr)} | val={len(y_va)} | test={len(y_te)} | ext_holdout={len(y_ext_n_data)}")
    print(f"Feature shape: {X_tr.shape}")

    X_tr_n, X_va_n, stats = standardize(X_tr, X_va)
    _, X_te_n, _           = standardize(X_tr, X_te)
    if len(y_ext_n_data):
        _, X_ext_n, _ = standardize(X_tr, X_ext_n_data)
    else:
        X_ext_n = X_ext_n_data

    # ── Train ───────────────────────────────────────────────────────────
    print(f"\nTraining DNN-21 (input_dim={FEATURE_SIZE})...")
    model = build_model(FEATURE_SIZE)
    model.summary()
    model.fit(
        X_tr_n, y_tr,
        validation_data=(X_va_n, y_va),
        epochs=args.epochs, batch_size=args.batch_size, verbose=1,
        callbacks=[tf.keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=8, restore_best_weights=True)],
    )

    # ── Evaluate ─────────────────────────────────────────────────────────
    val_metrics  = evaluate(model, X_va_n, y_va)
    test_metrics = evaluate(model, X_te_n, y_te)
    ext_metrics  = evaluate(model, X_ext_n, y_ext_n_data) if len(y_ext_n_data) else {}

    print(f"\nValidation : Acc={val_metrics['accuracy']*100:.2f}%  F1={val_metrics['f1']*100:.2f}%")
    print(f"Test (int) : Acc={test_metrics['accuracy']*100:.2f}%  F1={test_metrics['f1']*100:.2f}%  AUC={test_metrics['auc']:.4f}")
    if ext_metrics:
        print(f"External   : Acc={ext_metrics['accuracy']*100:.2f}%  F1={ext_metrics['f1']*100:.2f}%  "
              f"AUC={ext_metrics['auc']:.4f}  EER={ext_metrics['eer']*100:.2f}%")

    # ── Export ───────────────────────────────────────────────────────────
    model_path  = args.output_dir / "voice_spoof_detector_v2.keras"
    tflite_path = args.output_dir / "voice_spoof_detector_v2.tflite"
    stats_path  = args.output_dir / "feature_stats_v2.npy"
    report_path = args.output_dir / "report_v2.json"

    model.save(model_path)
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    tflite_model = converter.convert()
    tflite_path.write_bytes(tflite_model)
    np.save(stats_path, stats)

    report = {
        "feature_version":  2,
        "feature_size":     FEATURE_SIZE,
        "feature_order":    FEATURE_NAMES,
        "mix_per_class":    args.mix_per_class,
        "tflite_kb":        round(len(tflite_model) / 1024, 1),
        "params":           model.count_params(),
        "val":              val_metrics,
        "test":             test_metrics,
        "external":         ext_metrics,
        "dataset": {
            "total_train":      len(y_tr),
            "internal_test":    len(y_te),
            "external_holdout": len(y_ext_n_data),
        },
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))

    print(f"\n=== Done ===")
    print(f"  TFLite v2 : {tflite_path}  ({report['tflite_kb']} KB)")
    print(f"  Report    : {report_path}")
    print(f"\nDeploy: cp {tflite_path} app/src/main/assets/models/voice_spoof_detector.tflite")


if __name__ == "__main__":
    main()

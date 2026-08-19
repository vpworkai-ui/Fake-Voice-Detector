#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import wave
from datetime import datetime
from pathlib import Path
from typing import Callable

import numpy as np
import tensorflow as tf
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split


AUTOTUNE = tf.data.AUTOTUNE


def collect_dataset(dataset_root: Path, limit_per_class: int = 0, seed: int = 42) -> tuple[list[str], list[int]]:
    rng = random.Random(seed)
    paths: list[str] = []
    labels: list[int] = []
    for label_name, label in (("bonafide", 0), ("spoof", 1)):
        files = sorted((dataset_root / label_name).rglob("*.wav"))
        if limit_per_class > 0:
            rng.shuffle(files)
            files = files[:limit_per_class]
        paths.extend(str(p) for p in files)
        labels.extend([label] * len(files))
    if not paths:
        raise RuntimeError(f"No wav files found under {dataset_root}")
    return paths, labels


def resolve_split_size(count: int, ratio: float, name: str) -> int | float:
    if count > 0:
        return count
    if not 0.0 < ratio < 1.0:
        raise ValueError(f"{name} must be between 0 and 1 when count is not provided, got {ratio}")
    return ratio


def split_dataset(
    paths: list[str],
    labels: list[int],
    seed: int,
    test_size: float,
    val_size: float,
    test_count: int = 0,
    val_count: int = 0,
) -> dict[str, tuple[list[str], list[int]]]:
    resolved_test_size = resolve_split_size(test_count, test_size, "test_size")
    train_p, test_p, train_y, test_y = train_test_split(
        paths,
        labels,
        test_size=resolved_test_size,
        random_state=seed,
        stratify=labels,
    )
    resolved_val_size = resolve_split_size(val_count, val_size, "val_size")
    train_p, val_p, train_y, val_y = train_test_split(
        train_p,
        train_y,
        test_size=resolved_val_size,
        random_state=seed,
        stratify=train_y,
    )
    return {
        "train": (train_p, train_y),
        "val": (val_p, val_y),
        "test": (test_p, test_y),
    }


def load_wave(path: tf.Tensor, sample_rate: int, max_duration_sec: float) -> tf.Tensor:
    audio = tf.py_function(
        func=lambda p: load_wave_numpy(p, sample_rate),
        inp=[path],
        Tout=tf.float32,
    )
    audio.set_shape([None])
    target_len = int(sample_rate * max_duration_sec)
    audio = audio[:target_len]
    pad_len = tf.maximum(0, target_len - tf.shape(audio)[0])
    audio = tf.pad(audio, [[0, pad_len]])
    return audio


def augment_audio(audio: tf.Tensor, sample_rate: int, max_duration_sec: float) -> tf.Tensor:
    """Lightweight train-time augmentation to reduce source/device overfitting."""
    target_len = int(sample_rate * max_duration_sec)

    gain_db = tf.random.uniform([], -6.0, 6.0)
    audio = audio * tf.pow(10.0, gain_db / 20.0)

    max_shift = tf.cast(tf.round(0.10 * tf.cast(target_len, tf.float32)), tf.int32)
    shift = tf.random.uniform([], -max_shift, max_shift + 1, dtype=tf.int32)
    audio = tf.roll(audio, shift=shift, axis=0)

    rms = tf.sqrt(tf.reduce_mean(tf.square(audio)) + 1e-8)
    snr_db = tf.random.uniform([], 12.0, 30.0)
    noise_rms = rms / tf.pow(10.0, snr_db / 20.0)
    noise = tf.random.normal(tf.shape(audio), stddev=noise_rms)
    use_noise = tf.random.uniform([]) < 0.75
    audio = tf.cond(use_noise, lambda: audio + noise, lambda: audio)

    return tf.clip_by_value(audio, -1.0, 1.0)


def load_wave_numpy(path: tf.Tensor, target_sample_rate: int) -> np.ndarray:
    raw_path = path.numpy()
    if isinstance(raw_path, bytes):
        raw_path = raw_path.decode("utf-8")
    with wave.open(str(raw_path), "rb") as wf:
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
    if sample_width != 2:
        raise ValueError(f"Unsupported WAV sample width {sample_width}: {raw_path}")
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    audio = audio / float(np.iinfo(np.int16).max)
    if sample_rate != target_sample_rate and audio.size > 0:
        duration = audio.size / float(sample_rate)
        target_size = max(1, int(round(duration * target_sample_rate)))
        src_idx = np.linspace(0, audio.size - 1, num=audio.size, dtype=np.float32)
        target_idx = np.linspace(0, audio.size - 1, num=target_size, dtype=np.float32)
        audio = np.interp(target_idx, src_idx, audio).astype(np.float32)
    return audio.astype(np.float32)


def per_sample_standardize(x: tf.Tensor) -> tf.Tensor:
    mean = tf.reduce_mean(x)
    std = tf.math.reduce_std(x)
    return (x - mean) / tf.maximum(std, 1e-5)


def acoustic_features(audio: tf.Tensor, sample_rate: int) -> tf.Tensor:
    """8 acoustic features — statistical, source-agnostic, fast on Android CPU.
    Feature order matches AudioFeatureExtractor.kt exactly.
    Note: MFCC was tested but caused domain shift overfitting (AUC 0.36 external).
    These 8 statistical features are more robust across recording conditions.
    """
    abs_audio = tf.abs(audio)
    rms = tf.sqrt(tf.reduce_mean(tf.square(audio)) + 1e-8)
    mean_abs = tf.reduce_mean(abs_audio)

    signs = audio >= 0.0
    zcr = tf.reduce_mean(tf.cast(tf.not_equal(signs[1:], signs[:-1]), tf.float32))

    peak = tf.reduce_max(abs_audio)
    crest = tf.clip_by_value(peak / tf.maximum(rms, 1e-6), 0.0, 10.0)
    clipping_ratio = tf.reduce_mean(tf.cast(abs_audio > 0.98, tf.float32))
    dynamic_range = tf.reduce_max(audio) - tf.reduce_min(audio)

    active = tf.cast(abs_audio > 1e-4, tf.float32)
    duration_sec = tf.reduce_sum(active) / float(sample_rate)

    features = tf.stack(
        [rms, mean_abs, zcr, peak, crest, clipping_ratio, dynamic_range, duration_sec]
    )
    return tf.ensure_shape(features, [8])


def log_spectrogram(audio: tf.Tensor, frame_length: int, frame_step: int, out_hw: tuple[int, int]) -> tf.Tensor:
    spec = tf.signal.stft(
        audio,
        frame_length=frame_length,
        frame_step=frame_step,
        fft_length=frame_length,
        window_fn=tf.signal.hann_window,
    )
    mag = tf.math.log(tf.abs(spec) + 1e-6)
    mag = per_sample_standardize(mag)
    mag = tf.expand_dims(mag, axis=-1)
    return tf.image.resize(mag, out_hw, method="bilinear")


def make_raw_dataset(
    paths: list[str],
    labels: list[int],
    batch_size: int,
    sample_rate: int,
    max_duration_sec: float,
    training: bool,
    augment: bool = False,
    use_acoustic_features: bool = False,
) -> tf.data.Dataset:
    ds = tf.data.Dataset.from_tensor_slices((paths, np.asarray(labels, dtype=np.float32)))

    def mapper(path: tf.Tensor, label: tf.Tensor) -> tuple[tf.Tensor, tf.Tensor]:
        audio = load_wave(path, sample_rate, max_duration_sec)
        if training and augment:
            audio = augment_audio(audio, sample_rate, max_duration_sec)
        features = acoustic_features(audio, sample_rate)
        model_audio = per_sample_standardize(audio)
        model_input = tf.expand_dims(model_audio, axis=-1)
        if use_acoustic_features:
            return {"audio_input": model_input, "feature_input": features}, label
        return model_input, label

    if training:
        ds = ds.shuffle(min(len(paths), 8192), reshuffle_each_iteration=True)
    return ds.map(mapper, num_parallel_calls=AUTOTUNE).batch(batch_size).prefetch(AUTOTUNE)


def make_cross_scale_dataset(
    paths: list[str],
    labels: list[int],
    batch_size: int,
    sample_rate: int,
    max_duration_sec: float,
    training: bool,
    augment: bool = False,
    use_acoustic_features: bool = False,
) -> tf.data.Dataset:
    ds = tf.data.Dataset.from_tensor_slices((paths, np.asarray(labels, dtype=np.float32)))

    def mapper(path: tf.Tensor, label: tf.Tensor) -> tuple[tf.Tensor, tf.Tensor]:
        audio = load_wave(path, sample_rate, max_duration_sec)
        if training and augment:
            audio = augment_audio(audio, sample_rate, max_duration_sec)
        features = acoustic_features(audio, sample_rate)
        s1 = log_spectrogram(audio, int(sample_rate * 0.025), int(sample_rate * 0.010), (128, 64))
        s2 = log_spectrogram(audio, int(sample_rate * 0.050), int(sample_rate * 0.020), (128, 64))
        s3 = log_spectrogram(audio, int(sample_rate * 0.100), int(sample_rate * 0.040), (128, 64))
        model_input = tf.concat([s1, s2, s3], axis=-1)
        if use_acoustic_features:
            return {"audio_input": model_input, "feature_input": features}, label
        return model_input, label

    if training:
        ds = ds.shuffle(min(len(paths), 8192), reshuffle_each_iteration=True)
    return ds.map(mapper, num_parallel_calls=AUTOTUNE).batch(batch_size).prefetch(AUTOTUNE)


def conv_block_2d(x: tf.Tensor, filters: int, stride: int = 1) -> tf.Tensor:
    x = tf.keras.layers.Conv2D(filters, 3, strides=stride, padding="same", use_bias=False)(x)
    x = tf.keras.layers.BatchNormalization()(x)
    return tf.keras.layers.Activation("swish")(x)


def channel_attention_2d(x: tf.Tensor, ratio: int = 8) -> tf.Tensor:
    channels = int(x.shape[-1])
    hidden = max(channels // ratio, 4)
    avg = tf.keras.layers.GlobalAveragePooling2D()(x)
    mx = tf.keras.layers.GlobalMaxPooling2D()(x)
    dense1 = tf.keras.layers.Dense(hidden, activation="relu")
    dense2 = tf.keras.layers.Dense(channels, activation="sigmoid")
    weights = tf.keras.layers.Add()([dense2(dense1(avg)), dense2(dense1(mx))])
    weights = tf.keras.layers.Reshape((1, 1, channels))(weights)
    return tf.keras.layers.Multiply()([x, weights])


def add_acoustic_branch(x: tf.Tensor, feature_input: tf.Tensor) -> tf.Tensor:
    f = tf.keras.layers.BatchNormalization(name="feature_norm")(feature_input)
    f = tf.keras.layers.Dense(16, activation="swish", name="feature_dense")(f)
    f = tf.keras.layers.Dropout(0.10, name="feature_dropout")(f)
    return tf.keras.layers.Concatenate(name="audio_feature_fusion")([x, f])


def build_cross_scale_attention(input_shape: tuple[int, int, int], use_acoustic_features: bool = False) -> tf.keras.Model:
    inputs = tf.keras.Input(shape=input_shape, name="audio_input")
    x = conv_block_2d(inputs, 32)
    x = conv_block_2d(x, 56, stride=2)
    x = channel_attention_2d(x)
    x = conv_block_2d(x, 80, stride=2)
    x = channel_attention_2d(x)
    x = conv_block_2d(x, 104, stride=2)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    if use_acoustic_features:
        feature_input = tf.keras.Input(shape=(8,), name="feature_input")
        x = add_acoustic_branch(x, feature_input)
    x = tf.keras.layers.Dense(128, activation="swish")(x)
    x = tf.keras.layers.Dropout(0.25)(x)
    outputs = tf.keras.layers.Dense(1, activation="sigmoid")(x)
    model_inputs = [inputs, feature_input] if use_acoustic_features else inputs
    suffix = "_acoustic" if use_acoustic_features else ""
    return tf.keras.Model(model_inputs, outputs, name=f"cross_scale_attention_lite{suffix}")


def sepconv_block_1d(x: tf.Tensor, filters: int, stride: int = 1) -> tf.Tensor:
    residual = x
    x = tf.keras.layers.SeparableConv1D(filters, 9, strides=stride, padding="same", use_bias=False)(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Activation("swish")(x)
    x = tf.keras.layers.SeparableConv1D(filters, 9, padding="same", use_bias=False)(x)
    x = tf.keras.layers.BatchNormalization()(x)
    if int(residual.shape[-1]) != filters or stride != 1:
        residual = tf.keras.layers.Conv1D(filters, 1, strides=stride, padding="same", use_bias=False)(residual)
        residual = tf.keras.layers.BatchNormalization()(residual)
    x = tf.keras.layers.Add()([x, residual])
    return tf.keras.layers.Activation("swish")(x)


def build_aasist_lite(input_len: int, use_acoustic_features: bool = False) -> tf.keras.Model:
    inputs = tf.keras.Input(shape=(input_len, 1), name="audio_input")
    x = tf.keras.layers.Conv1D(32, 11, strides=4, padding="same", use_bias=False)(inputs)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Activation("swish")(x)
    x = sepconv_block_1d(x, 48, stride=2)
    x = sepconv_block_1d(x, 64, stride=2)
    x = sepconv_block_1d(x, 88, stride=2)
    attn = tf.keras.layers.MultiHeadAttention(num_heads=2, key_dim=24, dropout=0.1)(x, x)
    x = tf.keras.layers.Add()([x, attn])
    x = tf.keras.layers.LayerNormalization()(x)
    avg = tf.keras.layers.GlobalAveragePooling1D()(x)
    mx = tf.keras.layers.GlobalMaxPooling1D()(x)
    x = tf.keras.layers.Concatenate()([avg, mx])
    if use_acoustic_features:
        feature_input = tf.keras.Input(shape=(8,), name="feature_input")
        x = add_acoustic_branch(x, feature_input)
    x = tf.keras.layers.Dense(96, activation="swish")(x)
    x = tf.keras.layers.Dropout(0.25)(x)
    outputs = tf.keras.layers.Dense(1, activation="sigmoid")(x)
    model_inputs = [inputs, feature_input] if use_acoustic_features else inputs
    suffix = "_acoustic" if use_acoustic_features else ""
    return tf.keras.Model(model_inputs, outputs, name=f"aasist_lite_inspired{suffix}")


def cbam_1d(x: tf.Tensor, ratio: int = 8) -> tf.Tensor:
    channels = int(x.shape[-1])
    hidden = max(channels // ratio, 4)
    avg = tf.keras.layers.GlobalAveragePooling1D()(x)
    mx = tf.keras.layers.GlobalMaxPooling1D()(x)
    dense1 = tf.keras.layers.Dense(hidden, activation="relu")
    dense2 = tf.keras.layers.Dense(channels, activation="sigmoid")
    channel_weights = tf.keras.layers.Add()([dense2(dense1(avg)), dense2(dense1(mx))])
    channel_weights = tf.keras.layers.Reshape((1, channels))(channel_weights)
    x = tf.keras.layers.Multiply()([x, channel_weights])

    avg_spatial = tf.keras.layers.Lambda(lambda t: tf.reduce_mean(t, axis=-1, keepdims=True))(x)
    max_spatial = tf.keras.layers.Lambda(lambda t: tf.reduce_max(t, axis=-1, keepdims=True))(x)
    spatial = tf.keras.layers.Concatenate(axis=-1)([avg_spatial, max_spatial])
    spatial = tf.keras.layers.Conv1D(1, 7, padding="same", activation="sigmoid")(spatial)
    return tf.keras.layers.Multiply()([x, spatial])


def resnet_cbam_block(x: tf.Tensor, filters: int, stride: int = 1) -> tf.Tensor:
    residual = x
    x = tf.keras.layers.Conv1D(filters, 7, strides=stride, padding="same", use_bias=False)(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Activation("swish")(x)
    x = tf.keras.layers.Conv1D(filters, 7, padding="same", use_bias=False)(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = cbam_1d(x)
    if int(residual.shape[-1]) != filters or stride != 1:
        residual = tf.keras.layers.Conv1D(filters, 1, strides=stride, padding="same", use_bias=False)(residual)
        residual = tf.keras.layers.BatchNormalization()(residual)
    x = tf.keras.layers.Add()([x, residual])
    return tf.keras.layers.Activation("swish")(x)


def build_cbam_resnet(input_len: int, use_acoustic_features: bool = False) -> tf.keras.Model:
    inputs = tf.keras.Input(shape=(input_len, 1), name="audio_input")
    x = tf.keras.layers.Conv1D(32, 15, strides=4, padding="same", use_bias=False)(inputs)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Activation("swish")(x)
    x = resnet_cbam_block(x, 48, stride=2)
    x = resnet_cbam_block(x, 64, stride=2)
    x = resnet_cbam_block(x, 80, stride=2)
    x = resnet_cbam_block(x, 112, stride=2)
    x = tf.keras.layers.GlobalAveragePooling1D()(x)
    if use_acoustic_features:
        feature_input = tf.keras.Input(shape=(8,), name="feature_input")
        x = add_acoustic_branch(x, feature_input)
    x = tf.keras.layers.Dense(96, activation="swish")(x)
    x = tf.keras.layers.Dropout(0.25)(x)
    outputs = tf.keras.layers.Dense(1, activation="sigmoid")(x)
    model_inputs = [inputs, feature_input] if use_acoustic_features else inputs
    suffix = "_acoustic" if use_acoustic_features else ""
    return tf.keras.Model(model_inputs, outputs, name=f"cbam_resnet_lite{suffix}")


def compile_model(model: tf.keras.Model, learning_rate: float) -> None:
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate),
        loss=tf.keras.losses.BinaryCrossentropy(),
        metrics=[
            tf.keras.metrics.BinaryAccuracy(name="accuracy"),
            tf.keras.metrics.AUC(name="auc"),
        ],
    )


def compute_eer(y_true: np.ndarray, y_score: np.ndarray) -> float:
    fpr, tpr, _ = roc_curve(y_true, y_score)
    fnr = 1.0 - tpr
    idx = int(np.nanargmin(np.abs(fnr - fpr)))
    return float((fpr[idx] + fnr[idx]) / 2.0)


def evaluate(model: tf.keras.Model, ds: tf.data.Dataset) -> dict[str, float]:
    y_true_batches: list[np.ndarray] = []
    y_score_batches: list[np.ndarray] = []
    for x_batch, y_batch in ds:
        y_score = model.predict(x_batch, verbose=0).reshape(-1)
        y_true_batches.append(y_batch.numpy().reshape(-1))
        y_score_batches.append(y_score)
    y_true = np.concatenate(y_true_batches).astype(np.int32)
    y_score = np.concatenate(y_score_batches)
    y_pred = (y_score >= 0.5).astype(np.int32)
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "auc": float(roc_auc_score(y_true, y_score)),
        "eer": compute_eer(y_true, y_score),
    }


def write_split_manifests(split: dict[str, tuple[list[str], list[int]]], output_dir: Path) -> None:
    manifest_dir = output_dir / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    for name, (paths, labels) in split.items():
        rows = ["path,label"]
        rows.extend(f"{p},{'spoof' if y == 1 else 'bonafide'}" for p, y in zip(paths, labels))
        (manifest_dir / f"{name}.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")


def export_tflite(model: tf.keras.Model, model_dir: Path) -> tuple[str | None, int | None]:
    tflite_path = model_dir / "model_dynamic_quant.tflite"
    try:
        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        tflite = converter.convert()
        tflite_path.write_bytes(tflite)
        return str(tflite_path), tflite_path.stat().st_size
    except Exception as exc:
        (model_dir / "tflite_error.txt").write_text(str(exc), encoding="utf-8")
        return None, None


def train_one(
    name: str,
    model_builder: Callable[[], tf.keras.Model],
    ds_builder: Callable[[list[str], list[int], bool], tf.data.Dataset],
    split: dict[str, tuple[list[str], list[int]]],
    output_dir: Path,
    epochs: int,
    learning_rate: float,
) -> dict:
    model_dir = output_dir / name
    model_dir.mkdir(parents=True, exist_ok=True)
    model = model_builder()
    compile_model(model, learning_rate)

    train_ds = ds_builder(*split["train"], True)
    val_ds = ds_builder(*split["val"], False)
    test_ds = ds_builder(*split["test"], False)

    callbacks = [
        tf.keras.callbacks.EarlyStopping(monitor="val_auc", mode="max", patience=3, restore_best_weights=True),
        tf.keras.callbacks.ModelCheckpoint(
            filepath=str(model_dir / "best.keras"),
            monitor="val_auc",
            mode="max",
            save_best_only=True,
        ),
    ]
    history = model.fit(train_ds, validation_data=val_ds, epochs=epochs, callbacks=callbacks, verbose=1)
    test_metrics = evaluate(model, test_ds)
    val_metrics = evaluate(model, val_ds)

    tflite_path, tflite_size = export_tflite(model, model_dir)

    result = {
        "model": name,
        "keras_model_name": model.name,
        "params": int(model.count_params()),
        "epochs_requested": epochs,
        "epochs_ran": len(history.history.get("loss", [])),
        "val": val_metrics,
        "test": test_metrics,
        "tflite_dynamic_quant_path": tflite_path,
        "tflite_dynamic_quant_size_bytes": tflite_size,
        "history": {k: [float(v) for v in vals] for k, vals in history.history.items()},
    }
    (model_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def train_one_all_data(
    name: str,
    model_builder: Callable[[], tf.keras.Model],
    ds_builder: Callable[[list[str], list[int], bool], tf.data.Dataset],
    paths: list[str],
    labels: list[int],
    output_dir: Path,
    epochs: int,
    learning_rate: float,
) -> dict:
    model_dir = output_dir / name
    model_dir.mkdir(parents=True, exist_ok=True)
    model = model_builder()
    compile_model(model, learning_rate)

    train_ds = ds_builder(paths, labels, True)
    eval_ds = ds_builder(paths, labels, False)
    callbacks = [
        tf.keras.callbacks.ModelCheckpoint(
            filepath=str(model_dir / "best.keras"),
            monitor="loss",
            mode="min",
            save_best_only=True,
        ),
    ]
    history = model.fit(train_ds, epochs=epochs, callbacks=callbacks, verbose=1)
    train_metrics = evaluate(model, eval_ds)
    tflite_path, tflite_size = export_tflite(model, model_dir)

    result = {
        "model": name,
        "keras_model_name": model.name,
        "params": int(model.count_params()),
        "epochs_requested": epochs,
        "epochs_ran": len(history.history.get("loss", [])),
        "train_all_count": len(paths),
        "train": train_metrics,
        "val": None,
        "test": None,
        "tflite_dynamic_quant_path": tflite_path,
        "tflite_dynamic_quant_size_bytes": tflite_size,
        "history": {k: [float(v) for v in vals] for k, vals in history.history.items()},
        "note": "Trained on all available files. Metrics are training-set metrics only; use external files for real evaluation.",
    }
    (model_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Android-oriented audio deepfake model candidates.")
    parser.add_argument("--dataset-root", type=Path, default=Path("data/dataset_samples"))
    parser.add_argument("--output-dir", type=Path, default=Path("ml/artifacts/android_model_benchmark"))
    parser.add_argument("--models", default="cross_scale_attention_lite,aasist_lite,cbam_resnet_lite")
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--sample-rate", type=int, default=16000)
    parser.add_argument("--max-duration-sec", type=float, default=4.0)
    parser.add_argument("--limit-per-class", type=int, default=0)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-all", action="store_true", help="Train on every collected file without val/test split.")
    parser.add_argument("--test-size", type=float, default=0.2, help="Fraction for test split when --test-count is not set.")
    parser.add_argument("--val-size", type=float, default=0.2, help="Fraction of remaining data for validation when --val-count is not set.")
    parser.add_argument("--test-count", type=int, default=0, help="Exact number of files for stratified test split.")
    parser.add_argument("--val-count", type=int, default=0, help="Exact number of files for stratified validation split from non-test data.")
    parser.add_argument(
        "--augment",
        action="store_true",
        help="Apply train-time gain, shift, and noise augmentation to improve cross-source robustness.",
    )
    parser.add_argument(
        "--acoustic-features",
        action="store_true",
        help="Fuse the 8 thesis acoustic features with each deep model before classification.",
    )
    parser.add_argument(
        "--external-data-root", type=Path, default=None,
        help="Path to external Vietnamese test dataset to mix into training.",
    )
    parser.add_argument(
        "--external-mix-per-class", type=int, default=400,
        help="Number of external samples per class to mix into training set.",
    )
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    tf.random.set_seed(args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    paths, labels = collect_dataset(args.dataset_root, args.limit_per_class, args.seed)

    # Mix external data into training paths/labels
    if args.external_data_root and args.external_data_root.exists():
        ext_paths, ext_labels = collect_dataset(args.external_data_root, 0, args.seed)
        rng_ext = random.Random(args.seed)
        by_class: dict = {0: [], 1: []}
        for p, l in zip(ext_paths, ext_labels):
            by_class[l].append(p)
        ext_mix_paths, ext_mix_labels = [], []
        for lbl, files in by_class.items():
            shuffled = files[:]
            rng_ext.shuffle(shuffled)
            n = min(args.external_mix_per_class, len(shuffled))
            ext_mix_paths.extend(shuffled[:n])
            ext_mix_labels.extend([lbl] * n)
        paths = paths + ext_mix_paths
        labels = labels + ext_mix_labels
        combined = list(zip(paths, labels))
        rng_ext.shuffle(combined)
        paths, labels = zip(*combined)
        paths, labels = list(paths), list(labels)
        print(f"[external mix] Added {len(ext_mix_paths)} samples ({args.external_mix_per_class}/class) from {args.external_data_root}")
        print(f"[external mix] Total dataset: {len(paths)} (internal + external)")
    split = (
        {"train_all": (paths, labels)}
        if args.train_all
        else split_dataset(
            paths,
            labels,
            args.seed,
            args.test_size,
            args.val_size,
            args.test_count,
            args.val_count,
        )
    )
    write_split_manifests(split, args.output_dir)

    input_len = int(args.sample_rate * args.max_duration_sec)

    def raw_ds_builder(paths_: list[str], labels_: list[int], training: bool) -> tf.data.Dataset:
        return make_raw_dataset(
            paths_,
            labels_,
            args.batch_size,
            args.sample_rate,
            args.max_duration_sec,
            training,
            augment=args.augment,
            use_acoustic_features=args.acoustic_features,
        )

    def cross_ds_builder(paths_: list[str], labels_: list[int], training: bool) -> tf.data.Dataset:
        return make_cross_scale_dataset(
            paths_,
            labels_,
            args.batch_size,
            args.sample_rate,
            args.max_duration_sec,
            training,
            augment=args.augment,
            use_acoustic_features=args.acoustic_features,
        )

    registry: dict[str, tuple[Callable[[], tf.keras.Model], Callable[[list[str], list[int], bool], tf.data.Dataset]]] = {
        "cross_scale_attention_lite": (
            lambda: build_cross_scale_attention((128, 64, 3), args.acoustic_features),
            cross_ds_builder,
        ),
        "aasist_lite": (lambda: build_aasist_lite(input_len, args.acoustic_features), raw_ds_builder),
        "cbam_resnet_lite": (lambda: build_cbam_resnet(input_len, args.acoustic_features), raw_ds_builder),
    }

    selected = [m.strip() for m in args.models.split(",") if m.strip()]
    summary = {
        "created_at": datetime.utcnow().isoformat() + "Z",
        "dataset_root": str(args.dataset_root),
        "sample_count": len(paths),
        "class_count": {
            "bonafide": int(np.sum(np.asarray(labels) == 0)),
            "spoof": int(np.sum(np.asarray(labels) == 1)),
        },
        "split_count": {k: len(v[0]) for k, v in split.items()},
        "split_config": {
            "test_size": args.test_size,
            "val_size": args.val_size,
            "test_count": args.test_count,
            "val_count": args.val_count,
        },
        "train_all": args.train_all,
        "sample_rate": args.sample_rate,
        "max_duration_sec": args.max_duration_sec,
        "limit_per_class": args.limit_per_class,
        "augment": args.augment,
        "acoustic_features": args.acoustic_features,
        "acoustic_feature_order": [
            "rms",
            "mean_abs",
            "zcr",
            "peak",
            "crest_factor",
            "clipping_ratio",
            "dynamic_range",
            "active_duration_sec",
        ],
        "results": [],
        "note": "These are local TensorFlow/Keras Android-oriented lite implementations inspired by the selected papers, not official reproduction code.",
    }
    summary_path = args.output_dir / "summary.json"
    if summary_path.exists():
        previous_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        previous_results = previous_summary.get("results", [])
        selected_set = set(selected)
        summary["results"] = [row for row in previous_results if row.get("model") not in selected_set]

    for model_name in selected:
        if model_name not in registry:
            raise ValueError(f"Unknown model {model_name}. Available: {sorted(registry)}")
        builder, ds_builder = registry[model_name]
        if args.train_all:
            result = train_one_all_data(
                model_name,
                builder,
                ds_builder,
                paths,
                labels,
                args.output_dir,
                args.epochs,
                args.learning_rate,
            )
        else:
            result = train_one(
                model_name,
                builder,
                ds_builder,
                split,
                args.output_dir,
                args.epochs,
                args.learning_rate,
            )
        summary["results"].append(result)
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

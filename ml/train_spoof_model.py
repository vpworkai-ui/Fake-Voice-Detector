#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import numpy as np
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
import tensorflow as tf


@dataclass
class Sample:
    path: Path
    label: int  # 0 bonafide, 1 spoof


def load_wav_mono(path: Path) -> Tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wf:
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())

    if sample_width != 2:
        raise ValueError(f"Unsupported sample width in {path}: {sample_width}")

    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)

    audio = audio / float(np.iinfo(np.int16).max)
    return audio, sample_rate


def resample_linear(signal: np.ndarray, src_rate: int, tgt_rate: int) -> np.ndarray:
    if src_rate == tgt_rate:
        return signal
    if signal.size == 0:
        return signal

    duration = signal.size / float(src_rate)
    tgt_size = max(1, int(round(duration * tgt_rate)))
    src_idx = np.linspace(0, signal.size - 1, num=signal.size, dtype=np.float32)
    tgt_idx = np.linspace(0, signal.size - 1, num=tgt_size, dtype=np.float32)
    return np.interp(tgt_idx, src_idx, signal).astype(np.float32)


def extract_features(signal: np.ndarray, sample_rate: int) -> np.ndarray:
    if signal.size == 0:
        return np.zeros((8,), dtype=np.float32)

    rms = float(np.sqrt(np.mean(np.square(signal))))
    mean_abs = float(np.mean(np.abs(signal)))

    signs = np.signbit(signal)
    zcr = float(np.mean(signs[1:] != signs[:-1])) if signal.size > 1 else 0.0

    peak = float(np.max(np.abs(signal)))
    crest = float(peak / rms) if rms > 1e-6 else 0.0
    clipping_ratio = float(np.mean(np.abs(signal) > 0.98))
    dynamic_range = float(np.max(signal) - np.min(signal))
    duration_sec = float(signal.size / sample_rate)

    return np.array(
        [
            rms,
            mean_abs,
            zcr,
            peak,
            min(max(crest, 0.0), 10.0),
            clipping_ratio,
            max(dynamic_range, 0.0),
            duration_sec,
        ],
        dtype=np.float32,
    )


def collect_samples(dataset_root: Path) -> List[Sample]:
    samples: List[Sample] = []
    for label_name, label in (("bonafide", 0), ("spoof", 1)):
        label_dir = dataset_root / label_name
        if not label_dir.exists():
            continue
        for path in sorted(label_dir.rglob("*.wav")):
            samples.append(Sample(path=path, label=label))
    return samples


def build_matrix(samples: List[Sample], target_sr: int) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    feats = []
    labels = []
    failed = []

    for s in samples:
        try:
            sig, sr = load_wav_mono(s.path)
            sig = resample_linear(sig, sr, target_sr)
            feats.append(extract_features(sig, target_sr))
            labels.append(s.label)
        except Exception:
            failed.append(str(s.path))

    if not feats:
        raise RuntimeError("No valid wav samples found to train.")

    return np.stack(feats).astype(np.float32), np.array(labels, dtype=np.float32), failed


def standardize(train_x: np.ndarray, other: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = np.mean(train_x, axis=0, keepdims=True)
    std = np.std(train_x, axis=0, keepdims=True)
    std = np.where(std < 1e-6, 1.0, std)
    return (train_x - mean) / std, (other - mean) / std, np.concatenate([mean, std], axis=0)


def create_model(input_dim: int) -> tf.keras.Model:
    model = tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=(input_dim,)),
            tf.keras.layers.Dense(64, activation="relu"),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(32, activation="relu"),
            tf.keras.layers.Dense(1),
        ]
    )
    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-3),
        loss=tf.keras.losses.BinaryCrossentropy(from_logits=True),
        metrics=[tf.keras.metrics.BinaryAccuracy(name="accuracy")],
    )
    return model


def evaluate(model: tf.keras.Model, x: np.ndarray, y: np.ndarray) -> dict:
    logits = model.predict(x, verbose=0).reshape(-1)
    probs = 1.0 / (1.0 + np.exp(-logits))
    pred = (probs >= 0.5).astype(np.int32)
    truth = y.astype(np.int32)

    return {
        "accuracy": float(accuracy_score(truth, pred)),
        "precision": float(precision_score(truth, pred, zero_division=0)),
        "recall": float(recall_score(truth, pred, zero_division=0)),
        "f1": float(f1_score(truth, pred, zero_division=0)),
        "count": int(y.shape[0]),
    }


def export_tflite(model: tf.keras.Model, output_path: Path) -> None:
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    tflite_model = converter.convert()
    output_path.write_bytes(tflite_model)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train spoof detector from bonafide/spoof wav dataset")
    parser.add_argument("--dataset-root", default="data/dataset_samples", type=Path)
    parser.add_argument("--output-dir", default="ml/artifacts", type=Path)
    parser.add_argument("--target-sr", default=16000, type=int)
    parser.add_argument("--epochs", default=30, type=int)
    parser.add_argument("--batch-size", default=16, type=int)
    parser.add_argument("--seed", default=42, type=int)
    args = parser.parse_args()

    np.random.seed(args.seed)
    tf.random.set_seed(args.seed)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    samples = collect_samples(args.dataset_root)
    if not samples:
        raise RuntimeError(f"No samples found at: {args.dataset_root}")

    x, y, failed = build_matrix(samples, args.target_sr)

    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, stratify=y, random_state=args.seed
    )
    x_train, x_val, y_train, y_val = train_test_split(
        x_train, y_train, test_size=0.2, stratify=y_train, random_state=args.seed
    )

    x_train_n, x_val_n, stats = standardize(x_train, x_val)
    _, x_test_n, _ = standardize(x_train, x_test)

    model = create_model(input_dim=x_train.shape[1])
    callbacks = [
        tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=6, restore_best_weights=True)
    ]

    model.fit(
        x_train_n,
        y_train,
        validation_data=(x_val_n, y_val),
        epochs=args.epochs,
        batch_size=args.batch_size,
        verbose=1,
        callbacks=callbacks,
    )

    metrics = {
        "val": evaluate(model, x_val_n, y_val),
        "test": evaluate(model, x_test_n, y_test),
        "dataset": {
            "total": int(len(samples)),
            "bonafide": int(np.sum(y == 0)),
            "spoof": int(np.sum(y == 1)),
            "failed_files": failed,
        },
        "feature_order": [
            "rms",
            "meanAbs",
            "zcr",
            "peak",
            "crestFactor",
            "clippingRatio",
            "dynamicRange",
            "durationSec",
        ],
    }

    model_path = args.output_dir / "voice_spoof_detector.keras"
    tflite_path = args.output_dir / "voice_spoof_detector.tflite"
    stats_path = args.output_dir / "feature_stats.npy"
    report_path = args.output_dir / "report.json"

    model.save(model_path)
    export_tflite(model, tflite_path)
    np.save(stats_path, stats)
    report_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print("=== Training done ===")
    print(f"Saved model: {model_path}")
    print(f"Saved tflite: {tflite_path}")
    print(f"Saved report: {report_path}")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()

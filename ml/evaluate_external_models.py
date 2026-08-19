#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import random
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import tensorflow as tf
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from benchmark_android_models import (
    build_aasist_lite,
    build_cbam_resnet,
    build_cross_scale_attention,
    compute_eer,
    make_cross_scale_dataset,
    make_raw_dataset,
)


MODEL_INPUT_KIND = {
    "cross_scale_attention_lite": "cross",
    "aasist_lite": "raw",
    "cbam_resnet_lite": "raw",
}


def collect_external(root: Path, limit_per_class: int, seed: int) -> tuple[list[str], list[int]]:
    rng = random.Random(seed)
    rows: list[tuple[str, int]] = []
    label_dirs = [("bonafide", 0), ("real", 0), ("spoof", 1), ("fake", 1)]
    for folder, label in label_dirs:
        folder_path = root / folder
        if not folder_path.exists():
            continue
        files = sorted(folder_path.rglob("*.wav"))
        if limit_per_class:
            rng.shuffle(files)
            files = files[:limit_per_class]
        rows.extend((str(path), label) for path in files)
    if not rows:
        raise RuntimeError(f"No WAV files found under {root}/bonafide|real and {root}/spoof|fake")
    rng.shuffle(rows)
    paths, labels = zip(*rows)
    return list(paths), list(labels)


def threshold_metrics(y_true: np.ndarray, y_score: np.ndarray, threshold: float) -> dict[str, float | int]:
    y_pred = (y_score >= threshold).astype(np.int32)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }


def threshold_sweep_metrics(
    y_true: np.ndarray, y_score: np.ndarray, thresholds: list[float]
) -> list[dict[str, float | int]]:
    return [threshold_metrics(y_true, y_score, threshold) for threshold in thresholds]


def best_threshold_metrics(y_true: np.ndarray, y_score: np.ndarray) -> dict[str, dict[str, float | int]]:
    candidates = np.unique(np.concatenate(([0.0, 0.5, 1.0], y_score)))
    by_accuracy = max(
        (threshold_metrics(y_true, y_score, float(t)) for t in candidates),
        key=lambda row: (row["accuracy"], row["f1"]),
    )
    by_f1 = max(
        (threshold_metrics(y_true, y_score, float(t)) for t in candidates),
        key=lambda row: (row["f1"], row["accuracy"]),
    )
    return {
        "fixed_0_5": threshold_metrics(y_true, y_score, 0.5),
        "best_accuracy": by_accuracy,
        "best_f1": by_f1,
    }


def evaluate_with_counts(
    model: tf.keras.Model,
    ds: tf.data.Dataset,
    thresholds: list[float],
) -> tuple[
    dict[str, float | int | dict[str, float | int] | list[dict[str, float | int]]],
    np.ndarray,
    np.ndarray,
]:
    y_true_batches: list[np.ndarray] = []
    y_score_batches: list[np.ndarray] = []
    for x_batch, y_batch in ds:
        y_score = model.predict(x_batch, verbose=0).reshape(-1)
        y_true_batches.append(y_batch.numpy().reshape(-1))
        y_score_batches.append(y_score)

    y_true = np.concatenate(y_true_batches).astype(np.int32)
    y_score = np.concatenate(y_score_batches)
    metrics = threshold_metrics(y_true, y_score, 0.5)
    metrics.update(
        {
            "auc": float(roc_auc_score(y_true, y_score)),
            "eer": compute_eer(y_true, y_score),
            "threshold_analysis": best_threshold_metrics(y_true, y_score),
            "threshold_sweep": threshold_sweep_metrics(y_true, y_score, thresholds),
        }
    )
    return metrics, y_true, y_score


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate trained models on external labeled audio data.")
    parser.add_argument("--models-dir", type=Path, default=Path("ml/artifacts/android_model_benchmark_teacher_split"))
    parser.add_argument("--external-root", type=Path, default=Path("data/external_vietnamese_test"))
    parser.add_argument("--output-dir", type=Path, default=Path("ml/artifacts/external_evaluation_vietnamese"))
    parser.add_argument("--models", default="cross_scale_attention_lite,aasist_lite,cbam_resnet_lite")
    parser.add_argument("--limit-per-class", type=int, default=1000)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--sample-rate", type=int, default=16000)
    parser.add_argument("--max-duration-sec", type=float, default=4.0)
    parser.add_argument(
        "--thresholds",
        default="0.5,0.1,0.01,0.001,0.0005,0.0002,0.0001,0.00001,0.000001",
        help="Comma-separated fixed thresholds to compare on the external dataset.",
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    tf.random.set_seed(args.seed)
    np.random.seed(args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    training_summary_path = args.models_dir / "summary.json"
    training_summary = json.loads(training_summary_path.read_text(encoding="utf-8"))
    use_acoustic_features = bool(training_summary.get("acoustic_features", False))
    paths, labels = collect_external(args.external_root, args.limit_per_class, args.seed)

    manifest_path = args.output_dir / "external_manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["path", "label"])
        for path, label in zip(paths, labels):
            writer.writerow([path, "spoof" if label == 1 else "bonafide"])

    previous_by_model = {row["model"]: row for row in training_summary["results"]}
    thresholds = [float(value.strip()) for value in args.thresholds.split(",") if value.strip()]
    input_len = int(args.sample_rate * args.max_duration_sec)
    model_builders = {
        "cross_scale_attention_lite": lambda: build_cross_scale_attention((128, 64, 3), use_acoustic_features),
        "aasist_lite": lambda: build_aasist_lite(input_len, use_acoustic_features),
        "cbam_resnet_lite": lambda: build_cbam_resnet(input_len, use_acoustic_features),
    }
    results: list[dict] = []
    prediction_by_model: dict[str, np.ndarray] = {}
    selected_models = [m.strip() for m in args.models.split(",") if m.strip()]
    for model_name in selected_models:
        if model_name not in MODEL_INPUT_KIND:
            raise ValueError(f"Unknown model {model_name}. Available: {sorted(MODEL_INPUT_KIND)}")
        model_path = args.models_dir / model_name / "best.keras"
        if not model_path.exists():
            raise FileNotFoundError(f"Missing trained model weights: {model_path}")
        model = model_builders[model_name]()
        model.load_weights(model_path)
        if MODEL_INPUT_KIND[model_name] == "cross":
            ds = make_cross_scale_dataset(
                paths,
                labels,
                args.batch_size,
                args.sample_rate,
                args.max_duration_sec,
                False,
                use_acoustic_features=use_acoustic_features,
            )
        else:
            ds = make_raw_dataset(
                paths,
                labels,
                args.batch_size,
                args.sample_rate,
                args.max_duration_sec,
                False,
                use_acoustic_features=use_acoustic_features,
            )

        external_metrics, y_true, y_score = evaluate_with_counts(model, ds, thresholds)
        prediction_by_model[model_name] = y_score
        previous = previous_by_model[model_name]
        results.append(
            {
                "model": model_name,
                "params": previous["params"],
                "internal_test": previous["test"],
                "external_test": external_metrics,
                "accuracy_drop_points": float(
                    (previous["test"]["accuracy"] - external_metrics["accuracy"]) * 100.0
                ),
                "tflite_dynamic_quant_size_bytes": previous["tflite_dynamic_quant_size_bytes"],
            }
        )

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "models_dir": str(args.models_dir),
        "training_summary": str(training_summary_path),
        "external_root": str(args.external_root),
        "external_manifest": str(manifest_path),
        "external_count": len(paths),
        "external_class_count": {
            "bonafide": int(np.sum(np.asarray(labels) == 0)),
            "spoof": int(np.sum(np.asarray(labels) == 1)),
        },
        "selected_models": selected_models,
        "sample_rate": args.sample_rate,
        "max_duration_sec": args.max_duration_sec,
        "limit_per_class": args.limit_per_class,
        "thresholds": thresholds,
        "acoustic_features": use_acoustic_features,
        "results": results,
        "note": "Internal test is from the original VIVOS + mc_thu_hue split. External test uses a separate labeled dataset under --external-root and is not used for training.",
    }
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    predictions_path = args.output_dir / "external_predictions_threshold_0_5.csv"
    with predictions_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        header = ["path", "true_label"]
        for model_name in selected_models:
            header.extend(
                [
                    f"{model_name}_score",
                    f"{model_name}_pred_label_at_0_5",
                    f"{model_name}_correct_at_0_5",
                ]
            )
        writer.writerow(header)
        labels_array = np.asarray(labels, dtype=np.int32)
        for idx, (path, label) in enumerate(zip(paths, labels_array)):
            row = [path, "spoof" if label == 1 else "bonafide"]
            for model_name in selected_models:
                score = float(prediction_by_model[model_name][idx])
                pred = int(score >= 0.5)
                row.extend([score, "spoof" if pred == 1 else "bonafide", int(pred == label)])
            writer.writerow(row)

    with (args.output_dir / "comparison.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "model",
                "params",
                "internal_accuracy",
                "external_accuracy",
                "best_accuracy",
                "best_accuracy_threshold",
                "accuracy_drop_points",
                "external_auc",
                "external_eer",
                "tn",
                "fp",
                "fn",
                "tp",
            ]
        )
        for row in results:
            ext = row["external_test"]
            writer.writerow(
                [
                    row["model"],
                    row["params"],
                    row["internal_test"]["accuracy"],
                    ext["accuracy"],
                    ext["threshold_analysis"]["best_accuracy"]["accuracy"],
                    ext["threshold_analysis"]["best_accuracy"]["threshold"],
                    row["accuracy_drop_points"],
                    ext["auc"],
                    ext["eer"],
                    ext["tn"],
                    ext["fp"],
                    ext["fn"],
                    ext["tp"],
                ]
            )

    with (args.output_dir / "threshold_sweep.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["model", "threshold", "accuracy", "precision", "recall", "f1", "tn", "fp", "fn", "tp"])
        for row in results:
            for metrics in row["external_test"]["threshold_sweep"]:
                writer.writerow(
                    [
                        row["model"],
                        metrics["threshold"],
                        metrics["accuracy"],
                        metrics["precision"],
                        metrics["recall"],
                        metrics["f1"],
                        metrics["tn"],
                        metrics["fp"],
                        metrics["fn"],
                        metrics["tp"],
                    ]
                )

    lines = [
        "# External Model Evaluation",
        "",
        f"- External dataset: `{args.external_root}`",
        f"- External samples: {len(paths):,} ({summary['external_class_count']['bonafide']:,} bonafide, {summary['external_class_count']['spoof']:,} spoof)",
        f"- Internal reference: `{training_summary_path}`",
        f"- Per-file prediction audit: `{predictions_path}`",
        "",
        f"- Acoustic feature branch: `{use_acoustic_features}`",
        "",
        "| Model | Params | Internal test acc | External acc @0.5 | Best external acc | Best threshold | AUC | EER | FP | FN |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in results:
        ext = row["external_test"]
        best_acc = ext["threshold_analysis"]["best_accuracy"]
        lines.append(
            "| "
            + " | ".join(
                [
                    row["model"],
                    f"{row['params']:,}",
                    pct(row["internal_test"]["accuracy"]),
                    pct(ext["accuracy"]),
                    pct(best_acc["accuracy"]),
                    f"{best_acc['threshold']:.6f}",
                    f"{ext['auc']:.6f}",
                    pct(ext["eer"]),
                    str(ext["fp"]),
                    str(ext["fn"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Fixed Threshold Sweep",
            "",
            "| Model | Threshold | Accuracy | Precision | Recall | F1 | TN | FP | FN | TP |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in results:
        for metrics in row["external_test"]["threshold_sweep"]:
            lines.append(
                "| "
                + " | ".join(
                    [
                        row["model"],
                        f"{metrics['threshold']:.6f}",
                        pct(metrics["accuracy"]),
                        pct(metrics["precision"]),
                        pct(metrics["recall"]),
                        pct(metrics["f1"]),
                        str(metrics["tn"]),
                        str(metrics["fp"]),
                        str(metrics["fn"]),
                        str(metrics["tp"]),
                    ]
                )
                + " |"
            )
    (args.output_dir / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

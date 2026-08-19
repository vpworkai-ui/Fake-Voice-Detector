#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REMOTE_BASE = "/sdcard/Android/media/com.vpsaker.fake_voice_detector/benchmark"


def run(cmd: list[str], check: bool = True, capture: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
        check=check,
    )


def adb(*args: str, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess[str]:
    return run(["adb", *args], check=check, capture=capture)

def build_and_install() -> None:
    print("[1/5] Building debug APK")
    run(["./gradlew", ":app:assembleDebug"], check=True, capture=False)
    print("[2/5] Installing debug APK")
    adb("install", "-r", str(ROOT / "app/build/outputs/apk/debug/app-debug.apk"), check=True, capture=False)


def read_manifest(path: Path) -> list[tuple[str, int]]:
    rows = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        rel, label = line.split("\t", 1)
        rows.append((rel, 1 if label.strip().lower() == "spoof" else 0))
    return rows


def stage_batch(dataset_root: Path, batch_rows: list[tuple[str, int]], batch_dir: Path, manifest_path: Path) -> None:
    if batch_dir.exists():
        shutil.rmtree(batch_dir)
    batch_dir.mkdir(parents=True, exist_ok=True)
    manifest_lines: list[str] = []
    for rel, label in batch_rows:
        src = dataset_root / rel
        dst = batch_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(src, dst)
        except OSError:
            shutil.copy2(src, dst)
        manifest_lines.append(f"{rel}\t{'spoof' if label == 1 else 'bonafide'}")
    manifest_path.write_text("\n".join(manifest_lines) + "\n")


def wait_for_remote_file(path: str, timeout_sec: int) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        result = adb("shell", f"test -f '{path}' && echo OK || true")
        if "OK" in result.stdout:
            return True
        time.sleep(2)
    return False


def push_and_run_batch(batch_dir: Path, manifest_path: Path, models: str, threshold: float, progress_every: int, timeout_sec: int) -> dict:
    batch_token = f"batch_{time.time_ns()}"
    remote_dataset_root = f"{REMOTE_BASE}/{batch_token}/dataset"
    remote_manifest = f"{REMOTE_BASE}/{batch_token}/manifest.tsv"
    remote_output = f"{REMOTE_BASE}/{batch_token}/android_runtime_benchmark_batch.json"

    adb("shell", "mkdir", "-p", remote_dataset_root, capture=False)
    adb("push", str(batch_dir) + "/.", remote_dataset_root, capture=False)
    adb("push", str(manifest_path), remote_manifest, capture=False)
    adb("logcat", "-c", capture=False)
    adb(
        "shell",
        "am",
        "start",
        "-W",
        "-n",
        "com.vpsaker.fake_voice_detector/.debug.RuntimeBenchmarkActivity",
        "--es",
        "datasetRoot",
        remote_dataset_root,
        "--es",
        "manifestPath",
        remote_manifest,
        "--es",
        "outputPath",
        remote_output,
        "--es",
        "threshold",
        str(threshold),
        "--es",
        "progressEvery",
        str(progress_every),
        "--es",
        "models",
        models,
        capture=False,
    )
    if not wait_for_remote_file(remote_output, timeout_sec):
        logs = adb("logcat", "-d").stdout
        raise RuntimeError(f"Batch benchmark timed out.\nRecent logcat:\n{logs[-8000:]}")
    pulled = adb("shell", f"cat '{remote_output}'").stdout
    return json.loads(pulled)


def safe_div(n: float, d: float) -> float:
    return 0.0 if d == 0 else n / d


def compute_metrics(rows: list[tuple[float, int]], threshold: float) -> dict:
    tp = fp = fn = tn = 0
    for score, label in rows:
        pred = 1 if score >= threshold else 0
        if pred == 1 and label == 1:
            tp += 1
        elif pred == 1 and label == 0:
            fp += 1
        elif pred == 0 and label == 1:
            fn += 1
        else:
            tn += 1
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    far = safe_div(fp, fp + tn)
    frr = safe_div(fn, fn + tp)
    accuracy = safe_div(tp + tn, len(rows))

    sorted_rows = sorted(rows, key=lambda item: item[0], reverse=True)
    positives = sum(1 for _, label in sorted_rows if label == 1)
    negatives = sum(1 for _, label in sorted_rows if label == 0)
    tp_running = fp_running = 0
    prev_fpr = prev_tpr = auc = 0.0
    best_gap = float("inf")
    best_eer = 1.0
    i = 0
    while i < len(sorted_rows):
        score = sorted_rows[i][0]
        while i < len(sorted_rows) and sorted_rows[i][0] == score:
            if sorted_rows[i][1] == 1:
                tp_running += 1
            else:
                fp_running += 1
            i += 1
        tpr = safe_div(tp_running, positives)
        fpr = safe_div(fp_running, negatives)
        auc += (fpr - prev_fpr) * (tpr + prev_tpr) / 2.0
        prev_fpr, prev_tpr = fpr, tpr
        fnr = 1.0 - tpr
        gap = abs(fpr - fnr)
        if gap < best_gap:
            best_gap = gap
            best_eer = (fpr + fnr) / 2.0

    return {
        "sampleCount": len(rows),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "far": far,
        "frr": frr,
        "auc": max(0.0, min(1.0, auc)),
        "eer": max(0.0, min(1.0, best_eer)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", default=str(ROOT / "data/external_vietnamese_test"))
    parser.add_argument("--manifest", default=str(ROOT / "ml/artifacts/android_runtime_benchmark/benchmark_manifest.tsv"))
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--models", default="cross_scale_attention_lite,aasist_lite,cbam_resnet_lite")
    parser.add_argument("--threshold", type=float, default=0.25)
    parser.add_argument("--progress-every", type=int, default=50)
    parser.add_argument("--timeout-sec", type=int, default=900)
    parser.add_argument("--output", default=str(ROOT / "ml/artifacts/android_runtime_benchmark/android_runtime_benchmark.json"))
    args = parser.parse_args()

    dataset_root = Path(args.dataset_root)
    manifest_path = Path(args.manifest)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    build_and_install()
    all_rows = read_manifest(manifest_path)
    model_scores: dict[str, list[tuple[float, int]]] = {}
    model_meta: dict[str, dict] = {}

    with tempfile.TemporaryDirectory(prefix="fvd_batch_") as tmp:
        tmpdir = Path(tmp)
        for batch_index, start in enumerate(range(0, len(all_rows), args.batch_size), start=1):
            batch_rows = all_rows[start:start + args.batch_size]
            batch_dir = tmpdir / "dataset"
            batch_manifest = tmpdir / "manifest.tsv"
            stage_batch(dataset_root, batch_rows, batch_dir, batch_manifest)
            print(f"[3/5] Batch {batch_index}: {len(batch_rows)} files")
            batch_json = push_and_run_batch(batch_dir, batch_manifest, args.models, args.threshold, args.progress_every, args.timeout_sec)
            for model_key, payload in batch_json["models"].items():
                model_scores.setdefault(model_key, [])
                model_meta.setdefault(model_key, {
                    "displayName": payload["displayName"],
                    "assetPath": payload["assetPath"],
                    "md5": payload["md5"],
                })
                for score_row in payload.get("scores", []):
                    model_scores[model_key].append((float(score_row["score"]), int(score_row["label"])))

    final = {
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "threshold": args.threshold,
        "sampleCount": len(all_rows),
        "models": {},
    }
    for model_key, rows in model_scores.items():
        final["models"][model_key] = {
            **model_meta[model_key],
            **compute_metrics(rows, args.threshold),
        }

    output_path.write_text(json.dumps(final, indent=2))
    print(f"[4/5] Saved merged benchmark JSON: {output_path}")
    print(json.dumps(final, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

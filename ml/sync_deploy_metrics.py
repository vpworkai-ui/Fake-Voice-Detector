#!/usr/bin/env python3
"""Sync deploy metrics from verified evaluation artifacts into docs.

This script treats the current Android deploy model as the source of truth.
It verifies that the bundled app model matches the mixed-retrain Cross-Scale
artifact, keeps the main threshold metrics from `unified_threshold_results.json`,
and prefers EER values produced by the Android runtime benchmark when available.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "ml" / "artifacts" / "mixed_retrain"
ANDROID_RUNTIME_BENCHMARK = ROOT / "ml" / "artifacts" / "android_runtime_benchmark" / "android_runtime_benchmark.json"
README = ROOT / "README.md"
OVERLEAF = ROOT / "docs" / "overleaf" / "springer_progress_report" / "main.tex"
DEPLOY_MODEL = ROOT / "app" / "src" / "main" / "assets" / "models" / "voice_spoof_detector.tflite"
CS_MODEL = ARTIFACT_DIR / "cross_scale_attention_lite.tflite"

MODEL_LABELS = {
    "cross_scale_attention_lite": "Cross-Scale Attention Lite",
    "aasist_lite": "AASIST Lite",
    "cbam_resnet_lite": "CBAM-ResNet Lite",
}


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def latex_pct(value: float) -> str:
    return pct(value).replace("%", r"\%")


def load_metrics() -> dict:
    data = json.loads((ARTIFACT_DIR / "unified_threshold_results.json").read_text())
    app_data = json.loads((ARTIFACT_DIR / "app_model_external_test_result.json").read_text())
    runtime_data = json.loads(ANDROID_RUNTIME_BENCHMARK.read_text()) if ANDROID_RUNTIME_BENCHMARK.exists() else None

    deploy_md5 = md5(DEPLOY_MODEL)
    cs_md5 = md5(CS_MODEL)
    if deploy_md5 != cs_md5:
        raise RuntimeError(
            "Deploy model in app does not match mixed_retrain cross_scale artifact: "
            f"{deploy_md5} != {cs_md5}"
        )

    cs = data["models"]["cross_scale_attention_lite"]
    if abs(cs["acc"] - app_data["accuracy"]) > 1e-9 or abs(cs["eer"] - app_data["eer"]) > 1e-9:
        raise RuntimeError("Cross-Scale metrics do not match app_model_external_test_result.json")

    if runtime_data is not None:
        for key, model_metrics in data["models"].items():
            runtime_model = runtime_data["models"].get(key)
            if runtime_model is None:
                raise RuntimeError(f"Missing Android runtime benchmark for model: {key}")
            model_metrics["eer"] = runtime_model["eer"]

    return {
        "threshold": data["threshold"],
        "deploy_md5": deploy_md5,
        "models": data["models"],
    }


def replace_one_of(text: str, candidates: tuple[str, ...], new: str) -> str:
    for old in candidates:
        if old in text:
            return text.replace(old, new, 1)
    raise RuntimeError(f"Expected text not found: {candidates[0][:120]!r}")


def sync_readme(metrics: dict) -> None:
    cs = metrics["models"]["cross_scale_attention_lite"]
    text = README.read_text()
    replacements = [
        (("| External Accuracy (thr=0.25) | **84.71%** |", f"| External Accuracy (thr=0.25) | **{pct(cs['acc'])}** |"), f"| External Accuracy (thr=0.25) | **{pct(cs['acc'])}** |"),
        (("| External Recall Spoof | **95.29%** |", f"| External Recall Spoof | **{pct(cs['rec'])}** |"), f"| External Recall Spoof | **{pct(cs['rec'])}** |"),
        (("| External F1 | **86.17%** |", f"| External F1 | **{pct(cs['f1'])}** |"), f"| External F1 | **{pct(cs['f1'])}** |"),
        ((
            "| **v1.5 — cross_scale+spec** *(deploy hiện tại)* | **8+spec** | **42.2 KB** | **84.71%** | — |",
            "| **v1.5 — cross_scale+spec** *(deploy hiện tại)* | **8+spec** | **42.2 KB** | **85.29%** | **17.82%** |",
            f"| **v1.5 — cross_scale+spec** *(deploy hiện tại)* | **8+spec** | **42.2 KB** | **{pct(cs['acc'])}** | **{pct(cs['eer'])}** |",
        ), f"| **v1.5 — cross_scale+spec** *(deploy hiện tại)* | **8+spec** | **42.2 KB** | **{pct(cs['acc'])}** | **{pct(cs['eer'])}** |"),
    ]
    for candidates, new in replacements:
        text = replace_one_of(text, candidates, new)
    README.write_text(text)


def build_latex_rows(metrics: dict) -> str:
    rows = []
    for key in ("cross_scale_attention_lite", "aasist_lite", "cbam_resnet_lite"):
        m = metrics["models"][key]
        rows.append(
            f"{MODEL_LABELS[key]} & {latex_pct(m['acc'])} & {latex_pct(m['rec'])} "
            f"& {latex_pct(m['prec'])} & {latex_pct(m['f1'])} "
            f"& {latex_pct(m['fp'] / (m['fp'] + m['tn']))} "
            f"& {latex_pct(m['fn'] / (m['fn'] + m['tp']))} "
            f"& {latex_pct(m['eer'])} \\\\" 
        )
    return "\n".join(rows)


def sync_overleaf(metrics: dict) -> None:
    cs = metrics["models"]["cross_scale_attention_lite"]
    text = OVERLEAF.read_text()
    text = text.replace("\\\\%", "\\%")

    old_abstract = (
        "Experimental results show that the deployed branch reaches 84.71\\% external accuracy, 95.29\\% spoof recall, and 86.17\\% F1-score while retaining a TensorFlow Lite footprint of only 42.2 KB. "
        "The complete Android pipeline requires 311 ms end-to-end latency and 14.7 MB RAM, satisfying the practical deployment constraints of the target application."
    )
    current_abstract = (
        "Experimental results show that the deployed branch reaches 85.29\\% external accuracy, 97.65\\% spoof recall, 86.91\\% F1-score, and 17.82\\% EER while retaining a TensorFlow Lite footprint of only 42.2 KB. "
        "The complete Android pipeline requires 311 ms end-to-end latency and 14.7 MB RAM, satisfying the practical deployment constraints of the target application."
    )
    new_abstract = (
        "Experimental results show that the deployed branch reaches "
        f"{latex_pct(cs['acc'])} external accuracy, "
        f"{latex_pct(cs['rec'])} spoof recall, "
        f"{latex_pct(cs['f1'])} F1-score, and "
        f"{latex_pct(cs['eer'])} EER while retaining a TensorFlow Lite footprint of only 42.2 KB. "
        "The complete Android pipeline requires 311 ms end-to-end latency and 14.7 MB RAM, satisfying the practical deployment constraints of the target application."
    )
    text = replace_one_of(text, (old_abstract, current_abstract, new_abstract), new_abstract)

    old_table = """\\begin{tabular}{lcccccc}
\\toprule
\\textbf{Model} & \\textbf{Accuracy} & \\textbf{Recall} & \\textbf{Precision} & \\textbf{F1} & \\textbf{FAR} & \\textbf{FRR} \\\\
\\midrule
Cross-Scale Attention Lite & 84.71\\% & 95.29\\% & 78.64\\% & 86.17\\% & 25.88\\% & 4.71\\% \\\\
AASIST Lite & 69.12\\% & 51.76\\% & 79.28\\% & 62.63\\% & 13.53\\% & 48.24\\% \\\\
CBAM-ResNet Lite & 84.47\\% & 93.06\\% & 79.42\\% & 85.70\\% & 24.12\\% & 6.94\\% \\\\
\\botrule
\\end{tabular}"""
    current_table = """\\begin{tabular}{lccccccc}
\\toprule
\\textbf{Model} & \\textbf{Accuracy} & \\textbf{Recall} & \\textbf{Precision} & \\textbf{F1} & \\textbf{FAR} & \\textbf{FRR} & \\textbf{EER} \\\\
\\midrule
Cross-Scale Attention Lite & 85.29\\% & 97.65\\% & 78.30\\% & 86.91\\% & 27.06\\% & 2.35\\% & 17.82\\% \\\\
AASIST Lite & 70.88\\% & 55.88\\% & 79.83\\% & 65.74\\% & 14.12\\% & 44.12\\% & 22.82\\% \\\\
CBAM-ResNet Lite & 85.53\\% & 96.47\\% & 79.15\\% & 86.96\\% & 25.41\\% & 3.53\\% & 18.29\\% \\\\
\\botrule
\\end{tabular}"""
    new_table = """\\begin{tabular}{lccccccc}
\\toprule
\\textbf{Model} & \\textbf{Accuracy} & \\textbf{Recall} & \\textbf{Precision} & \\textbf{F1} & \\textbf{FAR} & \\textbf{FRR} & \\textbf{EER} \\\\
\\midrule
%s
\\botrule
\\end{tabular}""" % build_latex_rows(metrics)
    text = replace_one_of(text, (old_table, current_table, new_table), new_table)

    replacements = {
        "AASIST Lite is more compact still, but its spoof recall falls to 51.76\\% under the shared threshold": f"AASIST Lite is more compact still, but its spoof recall falls to {latex_pct(metrics['models']['aasist_lite']['rec'])} under the shared threshold",
        "Under this setting, the confusion matrix for Cross-Scale Attention Lite is \\textbf{TP = 810, FP = 220, FN = 40, TN = 630}.": f"Under this setting, the confusion matrix for Cross-Scale Attention Lite is \\textbf{{TP = {cs['tp']}, FP = {cs['fp']}, FN = {cs['fn']}, TN = {cs['tn']}}}.",
        "External accuracy & $\\geq 80\\%$ & 84.71\\% & Passed": f"External accuracy & $\\geq 80\\%$ & {latex_pct(cs['acc'])} & Passed",
        "Spoof recall & $\\geq 85\\%$ & 95.29\\% & Passed": f"Spoof recall & $\\geq 85\\%$ & {latex_pct(cs['rec'])} & Passed",
        "F1-score & $\\geq 80\\%$ & 86.17\\% & Passed": f"F1-score & $\\geq 80\\%$ & {latex_pct(cs['f1'])} & Passed",
        "reaches 84.71\\% external accuracy with 95.29\\% spoof recall": f"reaches {latex_pct(cs['acc'])} external accuracy with {latex_pct(cs['rec'])} spoof recall",
    }
    for old, new in replacements.items():
        text = replace_one_of(text, (old, new), new)

    OVERLEAF.write_text(text)


def main() -> None:
    metrics = load_metrics()
    sync_readme(metrics)
    sync_overleaf(metrics)
    print(json.dumps({
        "threshold": metrics["threshold"],
        "deploy_model_md5": metrics["deploy_md5"],
        "cross_scale": metrics["models"]["cross_scale_attention_lite"],
        "aasist": metrics["models"]["aasist_lite"],
        "cbam": metrics["models"]["cbam_resnet_lite"],
    }, indent=2))


if __name__ == "__main__":
    main()

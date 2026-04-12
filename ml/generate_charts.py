#!/usr/bin/env python3
"""
Sinh biểu đồ luận văn từ model đã huấn luyện.

Outputs (ml/charts/):
  training_curves.png      — Loss & Accuracy theo epoch
  confusion_matrix.png     — Ma trận nhầm lẫn (test set)
  roc_curve.png            — ROC Curve + AUC + EER
  pr_curve.png             — Precision-Recall Curve
  feature_distributions.png — Phân phối 8 đặc trưng: Bonafide vs Spoof
  metrics_summary.png      — Bảng chỉ số tổng hợp

Usage:
  cd <project_root>
  python ml/generate_charts.py
"""
from __future__ import annotations

import json
import wave
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import (
    confusion_matrix,
    roc_curve, auc,
    precision_recall_curve, average_precision_score,
)
from sklearn.model_selection import train_test_split
import tensorflow as tf

# ── Cấu hình ──────────────────────────────────────────────────────────────────
DATASET_ROOT = Path("data/dataset_samples")
ARTIFACTS    = Path("ml/artifacts")
CHARTS_DIR   = Path("ml/charts")
SEED         = 42
TARGET_SR    = 16_000
EPOCHS       = 60
BATCH_SIZE   = 16

FEATURE_NAMES = [
    "RMS", "Mean Abs", "ZCR", "Peak",
    "Crest Factor", "Clipping Ratio", "Dynamic Range", "Duration (s)",
]

# Bảng màu đồng nhất với app
C_BON   = "#1DB954"   # green — bonafide
C_SPF   = "#E53935"   # red   — spoof
C_TEAL  = "#0B8FAC"
C_PRP   = "#7B61FF"
C_ORG   = "#F57C00"
C_BG    = "#F4F8FA"
C_DARK  = "#0D2137"
C_MID   = "#4A6572"

plt.rcParams.update({
    "font.family":       "DejaVu Sans",
    "figure.facecolor":  C_BG,
    "axes.facecolor":    C_BG,
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "axes.edgecolor":    "#C5D5DE",
    "grid.color":        "#C5D5DE",
    "grid.linestyle":    "--",
    "grid.alpha":        0.5,
    "xtick.color":       C_MID,
    "ytick.color":       C_MID,
    "text.color":        C_DARK,
})


# ── Tiện ích âm thanh ─────────────────────────────────────────────────────────
def load_wav(path: Path):
    with wave.open(str(path), "rb") as wf:
        ch  = wf.getnchannels()
        raw = wf.readframes(wf.getnframes())
        sr  = wf.getframerate()
    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        audio = audio.reshape(-1, ch).mean(axis=1)
    return audio, sr


def extract_features(sig: np.ndarray, sr: int) -> np.ndarray:
    if sig.size == 0:
        return np.zeros(8, dtype=np.float32)
    rms   = float(np.sqrt(np.mean(np.square(sig))))
    mabs  = float(np.mean(np.abs(sig)))
    signs = np.signbit(sig)
    zcr   = float(np.mean(signs[1:] != signs[:-1])) if sig.size > 1 else 0.0
    peak  = float(np.max(np.abs(sig)))
    crest = float(peak / rms) if rms > 1e-6 else 0.0
    clip  = float(np.mean(np.abs(sig) > 0.98))
    dr    = float(np.max(sig) - np.min(sig))
    dur   = float(sig.size / sr)
    return np.array([rms, mabs, zcr, peak, min(crest, 10.0), clip, max(dr, 0.0), dur], dtype=np.float32)


def load_dataset():
    feats, labels = [], []
    for lname, lid in [("bonafide", 0), ("spoof", 1)]:
        d = DATASET_ROOT / lname
        if not d.exists():
            continue
        for p in sorted(d.rglob("*.wav")):
            try:
                sig, sr = load_wav(p)
                feats.append(extract_features(sig, sr))
                labels.append(lid)
            except Exception:
                pass
    return np.stack(feats).astype(np.float32), np.array(labels, dtype=np.float32)


def standardize(x_tr, x_other):
    mu  = x_tr.mean(0, keepdims=True)
    std = x_tr.std(0,  keepdims=True)
    std = np.where(std < 1e-6, 1.0, std)
    return (x_tr - mu) / std, (x_other - mu) / std


def build_model(dim: int) -> tf.keras.Model:
    m = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(dim,)),
        tf.keras.layers.Dense(64, activation="relu"),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(32, activation="relu"),
        tf.keras.layers.Dense(1),
    ])
    m.compile(
        optimizer=tf.keras.optimizers.Adam(1e-3),
        loss=tf.keras.losses.BinaryCrossentropy(from_logits=True),
        metrics=[tf.keras.metrics.BinaryAccuracy(name="accuracy")],
    )
    return m


# ── Biểu đồ 1: Training curves ───────────────────────────────────────────────
def plot_training_curves(history: dict, out: Path) -> None:
    ep   = range(1, len(history["loss"]) + 1)
    best = int(np.argmin(history["val_loss"])) + 1

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle("Quá trình Huấn luyện Mô hình", fontsize=15, fontweight="bold", color=C_DARK, y=1.02)

    # — Loss —
    ax1.plot(ep, history["loss"],     color=C_TEAL, lw=2.2, label="Train Loss")
    ax1.plot(ep, history["val_loss"], color=C_SPF,  lw=2.2, ls="--", label="Validation Loss")
    ax1.axvline(best, color="#AAAAAA", ls=":", lw=1.4)
    ax1.text(best + 0.4, max(history["loss"]) * 0.97,
             f"Best epoch\n= {best}", fontsize=9, color="#888888")
    ax1.set_title("Binary Cross-Entropy Loss", fontweight="bold", fontsize=12)
    ax1.set_xlabel("Epoch"); ax1.set_ylabel("Loss")
    ax1.legend(frameon=True, framealpha=0.85, fontsize=10)
    ax1.grid(True)

    # — Accuracy —
    ax2.plot(ep, [v * 100 for v in history["accuracy"]],
             color=C_BON, lw=2.2, label="Train Accuracy")
    ax2.plot(ep, [v * 100 for v in history["val_accuracy"]],
             color=C_TEAL, lw=2.2, ls="--", label="Validation Accuracy")
    ax2.axhline(98, color="#AAAAAA", ls=":", lw=1, alpha=0.7)
    ax2.set_title("Accuracy (%)", fontweight="bold", fontsize=12)
    ax2.set_xlabel("Epoch"); ax2.set_ylabel("Accuracy (%)")
    ax2.set_ylim(60, 101)
    ax2.legend(frameon=True, framealpha=0.85, fontsize=10)
    ax2.grid(True)

    plt.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"✓  {out.name}")


# ── Biểu đồ 2: Confusion Matrix ──────────────────────────────────────────────
def plot_confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, out: Path) -> None:
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()
    total = tn + fp + fn + tp
    acc   = (tp + tn) / total
    far   = fp / (fp + tn) if (fp + tn) > 0 else 0.0   # False Accept Rate
    frr   = fn / (fn + tp) if (fn + tp) > 0 else 0.0   # False Reject Rate

    fig, ax = plt.subplots(figsize=(8, 7))
    fig.suptitle(
        f"Confusion Matrix — Tập Kiểm tra ({total:,} mẫu)\n"
        f"Accuracy: {acc:.2%}   FAR: {far:.2%}   FRR: {frr:.2%}",
        fontsize=13, fontweight="bold", color=C_DARK
    )

    # Cell data: [row=actual, col=predicted]
    cells = [
        # (row, col, count, label, bg_hex, text_color)
        (0, 0, tn, "True Negative (TN)\nBonafide → Bonafide ✓", "#D5F5E3", C_DARK),
        (0, 1, fp, "False Positive (FP)\nBonafide → Spoof ✗",   "#FFEBEE", C_SPF),
        (1, 0, fn, "False Negative (FN)\nSpoof → Bonafide ✗",   "#FFEBEE", C_SPF),
        (1, 1, tp, "True Positive (TP)\nSpoof → Spoof ✓",       "#D5F5E3", C_DARK),
    ]
    for row, col, count, label, bg, tc in cells:
        rect = plt.Rectangle([col, 1 - row], 1, 1,
                              facecolor=bg, edgecolor="white", linewidth=3)
        ax.add_patch(rect)
        ax.text(col + 0.5, 1.5 - row + 0.15, str(count),
                ha="center", va="center", fontsize=28, fontweight="black", color=tc)
        pct = count / total * 100
        ax.text(col + 0.5, 1.5 - row - 0.15, f"({pct:.1f}%)\n{label}",
                ha="center", va="center", fontsize=9, color=C_MID)

    ax.set_xlim(0, 2); ax.set_ylim(0, 2)
    ax.set_xticks([0.5, 1.5])
    ax.set_xticklabels(["Dự đoán: BONAFIDE", "Dự đoán: SPOOF"],
                       fontsize=11, fontweight="bold")
    ax.set_yticks([0.5, 1.5])
    ax.set_yticklabels(["Thực tế: SPOOF", "Thực tế: BONAFIDE"],
                       fontsize=11, fontweight="bold")
    ax.tick_params(length=0)

    plt.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"✓  {out.name}")


# ── Biểu đồ 3: ROC Curve ─────────────────────────────────────────────────────
def plot_roc_curve(y_true: np.ndarray, y_prob: np.ndarray, out: Path) -> None:
    fpr, tpr, _ = roc_curve(y_true, y_prob)
    roc_auc     = auc(fpr, tpr)
    fnr         = 1 - tpr
    eer_idx     = np.argmin(np.abs(fnr - fpr))
    eer         = (fpr[eer_idx] + fnr[eer_idx]) / 2

    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    ax.plot(fpr, tpr, color=C_TEAL, lw=2.5, label=f"ROC  (AUC = {roc_auc:.4f})")
    ax.fill_between(fpr, tpr, alpha=0.08, color=C_TEAL)
    ax.plot([0, 1], [0, 1], "k--", lw=1.2, alpha=0.4, label="Random Classifier")
    ax.scatter([fpr[eer_idx]], [tpr[eer_idx]],
               color=C_SPF, s=90, zorder=5, label=f"EER point  ({eer:.2%})")
    ax.annotate(f"EER = {eer:.2%}", xy=(fpr[eer_idx], tpr[eer_idx]),
                xytext=(fpr[eer_idx] + 0.07, tpr[eer_idx] - 0.07),
                fontsize=9, color=C_SPF,
                arrowprops=dict(arrowstyle="->", color=C_SPF))
    ax.set_xlabel("False Positive Rate (FAR)",  fontsize=11)
    ax.set_ylabel("True Positive Rate (1 − FRR)", fontsize=11)
    ax.set_title(f"ROC Curve\nAUC = {roc_auc:.4f}   |   EER = {eer:.2%}",
                 fontsize=13, fontweight="bold")
    ax.legend(frameon=True, framealpha=0.9, fontsize=10)
    ax.grid(True)
    ax.set_xlim(-0.01, 1.01); ax.set_ylim(-0.01, 1.02)

    plt.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"✓  {out.name}")


# ── Biểu đồ 4: Precision-Recall Curve ───────────────────────────────────────
def plot_pr_curve(y_true: np.ndarray, y_prob: np.ndarray, out: Path) -> None:
    prec, rec, _ = precision_recall_curve(y_true, y_prob)
    ap           = average_precision_score(y_true, y_prob)
    baseline     = float(y_true.mean())

    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    ax.plot(rec, prec, color=C_BON, lw=2.5, label=f"PR Curve  (AP = {ap:.4f})")
    ax.fill_between(rec, prec, alpha=0.08, color=C_BON)
    ax.axhline(baseline, ls="--", color="#AAAAAA", lw=1.2,
               label=f"Baseline Precision = {baseline:.2f}")
    ax.set_xlabel("Recall (Độ nhạy)",  fontsize=11)
    ax.set_ylabel("Precision (Độ chính xác)", fontsize=11)
    ax.set_title(f"Precision-Recall Curve\nAverage Precision = {ap:.4f}",
                 fontsize=13, fontweight="bold")
    ax.legend(frameon=True, framealpha=0.9, fontsize=10)
    ax.grid(True)
    ax.set_xlim(-0.01, 1.01); ax.set_ylim(-0.01, 1.02)

    plt.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"✓  {out.name}")


# ── Biểu đồ 5: Feature Distributions ────────────────────────────────────────
def plot_feature_distributions(X: np.ndarray, y: np.ndarray, out: Path) -> None:
    fig, axes = plt.subplots(2, 4, figsize=(16, 9))
    fig.suptitle(
        "Phân phối 8 Đặc trưng Âm thanh: Bonafide vs Spoof",
        fontsize=15, fontweight="bold", color=C_DARK, y=1.01
    )

    bon_data = X[y == 0]
    spf_data = X[y == 1]

    for i, (ax, name) in enumerate(zip(axes.flatten(), FEATURE_NAMES)):
        b = bon_data[:, i]
        s = spf_data[:, i]
        lo = np.percentile(np.concatenate([b, s]), 1)
        hi = np.percentile(np.concatenate([b, s]), 99)
        bins = np.linspace(lo, hi, 45)

        ax.hist(b, bins=bins, color=C_BON, alpha=0.65, density=True, label="Bonafide")
        ax.hist(s, bins=bins, color=C_SPF, alpha=0.65, density=True, label="Spoof")

        # Mean lines
        ax.axvline(b.mean(), color=C_BON, lw=1.5, ls="--", alpha=0.9)
        ax.axvline(s.mean(), color=C_SPF, lw=1.5, ls="--", alpha=0.9)

        ax.set_title(name, fontweight="bold", fontsize=11, color=C_DARK)
        ax.set_xlabel("Giá trị", fontsize=9, color=C_MID)
        ax.set_ylabel("Mật độ", fontsize=9, color=C_MID)
        ax.legend(fontsize=8, frameon=False)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"✓  {out.name}")


# ── Biểu đồ 6: Metrics Summary ───────────────────────────────────────────────
def plot_metrics_summary(report: dict, out: Path) -> None:
    tm = report["test"]
    vm = report["val"]
    ds = report["dataset"]

    names  = ["Accuracy", "Precision", "Recall", "F1 Score"]
    t_vals = [tm["accuracy"], tm["precision"], tm["recall"], tm["f1"]]
    v_vals = [vm["accuracy"], vm["precision"], vm["recall"], vm["f1"]]
    colors = [C_TEAL, C_BON, C_PRP, C_ORG]

    x   = np.arange(len(names))
    w   = 0.35
    fig, ax = plt.subplots(figsize=(10, 6))

    b1 = ax.bar(x - w/2, [v * 100 for v in t_vals], w,
                label="Test set", color=colors, edgecolor="white", lw=1.5)
    b2 = ax.bar(x + w/2, [v * 100 for v in v_vals], w,
                label="Val set", color=colors, alpha=0.55, edgecolor="white", lw=1.5,
                hatch="//")

    for bar, val in zip(b1, t_vals):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.15,
                f"{val:.2%}", ha="center", va="bottom",
                fontsize=11, fontweight="bold", color=C_DARK)

    for bar, val in zip(b2, v_vals):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.15,
                f"{val:.2%}", ha="center", va="bottom",
                fontsize=10, color=C_MID)

    ax.set_xticks(x)
    ax.set_xticklabels(names, fontsize=12, fontweight="bold")
    ax.set_ylim(85, 103)
    ax.set_ylabel("Giá trị (%)", fontsize=11)
    ax.set_title("Chỉ số Hiệu năng Mô hình (Test set vs Val set)",
                 fontsize=14, fontweight="bold", color=C_DARK)
    ax.legend(fontsize=10, frameon=True)
    ax.grid(True, axis="y", alpha=0.3)
    ax.axhline(100, ls="--", color="#CCCCCC", lw=1)

    fig.text(0.5, -0.04,
             f"Dataset: {ds['total']:,} mẫu  ·  "
             f"Bonafide (VIVOS): {ds['bonafide']:,}  ·  "
             f"Spoof (mc_thu_hue): {ds['spoof']:,}  ·  "
             f"Test: {tm['count']:,} mẫu  ·  Val: {vm['count']:,} mẫu",
             ha="center", fontsize=10, color=C_MID)

    plt.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"✓  {out.name}")


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    np.random.seed(SEED)
    tf.random.set_seed(SEED)

    # 1. Load features
    print("─" * 55)
    print("Đang tải dataset và trích xuất đặc trưng...")
    X, y = load_dataset()
    print(f"  Tổng: {len(X):,} mẫu  "
          f"(bonafide={int((y==0).sum()):,}, spoof={int((y==1).sum()):,})")

    # 2. Split (cùng seed với lúc train)
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=SEED)
    X_tr, X_va, y_tr, y_va = train_test_split(
        X_tr, y_tr, test_size=0.2, stratify=y_tr, random_state=SEED)
    X_tr_n, X_va_n = standardize(X_tr, X_va)
    _, X_te_n      = standardize(X_tr, X_te)

    print(f"  Train={len(X_tr):,}  Val={len(X_va):,}  Test={len(X_te):,}")
    print("─" * 55)

    # 3. Feature distribution (raw data, trước normalize)
    print("\n[1/6] Phân phối đặc trưng...")
    plot_feature_distributions(X, y, CHARTS_DIR / "feature_distributions.png")

    # 4. Metrics summary từ report.json
    rpt_path = ARTIFACTS / "report.json"
    if rpt_path.exists():
        print("\n[2/6] Bảng chỉ số tổng hợp...")
        report = json.loads(rpt_path.read_text())
        plot_metrics_summary(report, CHARTS_DIR / "metrics_summary.png")

    # 5. Train fresh model để lấy history curves
    print(f"\n[3/6] Huấn luyện để lấy training curves ({EPOCHS} epochs)...")
    model = build_model(X_tr.shape[1])
    hist = model.fit(
        X_tr_n, y_tr,
        validation_data=(X_va_n, y_va),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        verbose=1,
        callbacks=[
            tf.keras.callbacks.EarlyStopping(
                monitor="val_loss", patience=8, restore_best_weights=True
            )
        ],
    )
    plot_training_curves(hist.history, CHARTS_DIR / "training_curves.png")

    # 6. Dùng model đã train tốt nhất (keras saved)
    saved_model_path = ARTIFACTS / "voice_spoof_detector.keras"
    if saved_model_path.exists():
        print("\nSử dụng model đã lưu để đánh giá...")
        eval_model = tf.keras.models.load_model(str(saved_model_path))
    else:
        eval_model = model

    # Predictions
    logits = eval_model.predict(X_te_n, verbose=0).reshape(-1)
    probs  = 1.0 / (1.0 + np.exp(-logits))
    preds  = (probs >= 0.5).astype(int)
    y_int  = y_te.astype(int)

    print("\n[4/6] Confusion Matrix...")
    plot_confusion_matrix(y_int, preds, CHARTS_DIR / "confusion_matrix.png")

    print("\n[5/6] ROC Curve...")
    plot_roc_curve(y_int, probs, CHARTS_DIR / "roc_curve.png")

    print("\n[6/6] Precision-Recall Curve...")
    plot_pr_curve(y_int, probs, CHARTS_DIR / "pr_curve.png")

    # Summary
    print("\n" + "=" * 55)
    print(f"✅ Tất cả biểu đồ đã lưu tại: {CHARTS_DIR.resolve()}")
    print("─" * 55)
    total_kb = 0
    for f in sorted(CHARTS_DIR.glob("*.png")):
        kb = f.stat().st_size // 1024
        total_kb += kb
        print(f"  📊  {f.name:<35} {kb:>4} KB")
    print(f"  Tổng: {total_kb} KB")
    print("=" * 55)


if __name__ == "__main__":
    main()

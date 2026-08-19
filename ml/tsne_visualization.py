#!/usr/bin/env python3
"""
t-SNE Visualization — Data Record
===================================
Mục đích (theo yêu cầu GVHD):
  Dùng t-SNE để visualize phân phối 8 đặc trưng âm thanh của dữ liệu ghi âm,
  giúp quan sát trực quan xem bonafide và spoof có tách nhau không, và
  dữ liệu nội bộ (training) vs dữ liệu ngoài nguồn (external) có cùng
  phân phối không.

Biểu đồ sinh ra:
  1. tsne_label.png      — màu theo nhãn (bonafide / spoof)
  2. tsne_source.png     — màu theo nguồn (internal / external)
  3. tsne_combined.png   — kết hợp: hình theo nguồn, màu theo nhãn
  4. tsne_feature_density.png — phân phối từng đặc trưng: bonafide vs spoof

Chạy:
  python ml/tsne_visualization.py
  python ml/tsne_visualization.py \\
    --internal-root data/dataset_samples \\
    --external-root data/external_vietnamese_test \\
    --output-dir ml/artifacts/tsne \\
    --limit-internal 2000 --limit-external 1000 --seed 42
"""
from __future__ import annotations

import argparse
import wave
from pathlib import Path
from typing import List, Optional

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler

# ---------------------------------------------------------------------------
# Feature definitions
# ---------------------------------------------------------------------------
FEATURE_NAMES = [
    "RMS", "MeanAbs", "ZCR", "Peak",
    "CrestFactor", "ClippingRatio", "DynamicRange", "ActiveDuration",
]

FEATURE_VI = [
    "RMS\n(Năng lượng)", "MeanAbs\n(Biên độ TB)", "ZCR\n(Tỷ lệ đổi dấu)", "Peak\n(Biên độ đỉnh)",
    "CrestFactor\n(Peak/RMS)", "ClippingRatio\n(Tỷ lệ bão hòa)", "DynamicRange\n(Dải biến thiên)",
    "ActiveDuration\n(Thời lượng)",
]


# ---------------------------------------------------------------------------
# Audio I/O
# ---------------------------------------------------------------------------
def load_wav_mono(path: Path):
    with wave.open(str(path), "rb") as wf:
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
    if sample_width != 2:
        raise ValueError(f"Unsupported: {path}")
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    return audio / float(np.iinfo(np.int16).max), sample_rate


def resample_linear(signal: np.ndarray, src_rate: int, tgt_rate: int) -> np.ndarray:
    if src_rate == tgt_rate or signal.size == 0:
        return signal
    tgt_size = max(1, int(round(signal.size / src_rate * tgt_rate)))
    src_idx = np.linspace(0, signal.size - 1, signal.size, dtype=np.float32)
    tgt_idx = np.linspace(0, signal.size - 1, tgt_size, dtype=np.float32)
    return np.interp(tgt_idx, src_idx, signal).astype(np.float32)


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------
def extract_features(signal: np.ndarray, sample_rate: int) -> np.ndarray:
    if signal.size == 0:
        return np.zeros(8, dtype=np.float32)
    rms = float(np.sqrt(np.mean(np.square(signal))))
    mean_abs = float(np.mean(np.abs(signal)))
    signs = np.signbit(signal)
    zcr = float(np.mean(signs[1:] != signs[:-1])) if signal.size > 1 else 0.0
    peak = float(np.max(np.abs(signal)))
    crest = float(peak / rms) if rms > 1e-6 else 0.0
    clipping_ratio = float(np.mean(np.abs(signal) > 0.98))
    dynamic_range = float(np.max(signal) - np.min(signal))
    duration_sec = float(signal.size / sample_rate)
    return np.array([
        rms, mean_abs, zcr, peak,
        min(max(crest, 0.0), 10.0),
        clipping_ratio, max(dynamic_range, 0.0), duration_sec,
    ], dtype=np.float32)


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------
def load_dataset(root: Path, limit: int, seed: int, target_sr: int = 16000):
    """Returns (features, labels, paths).  labels: 0=bonafide, 1=spoof."""
    rng = np.random.default_rng(seed)
    feats, labels = [], []
    for label_name, label in (("bonafide", 0), ("spoof", 1)):
        label_dir = root / label_name
        if not label_dir.exists():
            print(f"  [WARN] Directory not found: {label_dir}")
            continue
        files = sorted(label_dir.rglob("*.wav"))
        if limit > 0 and len(files) > limit:
            idx = rng.choice(len(files), size=limit, replace=False)
            files = [files[i] for i in sorted(idx)]
        for path in files:
            try:
                sig, sr = load_wav_mono(path)
                sig = resample_linear(sig, sr, target_sr)
                feats.append(extract_features(sig, target_sr))
                labels.append(label)
            except Exception:
                pass
    if not feats:
        return None, None
    return np.stack(feats).astype(np.float32), np.array(labels, dtype=np.int32)


# ---------------------------------------------------------------------------
# t-SNE
# ---------------------------------------------------------------------------
def run_tsne(X: np.ndarray, seed: int, perplexity: float = 30.0) -> np.ndarray:
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    n = X_scaled.shape[0]
    perp = min(perplexity, n // 5)  # perplexity < n/5
    tsne = TSNE(n_components=2, perplexity=perp, random_state=seed,
                max_iter=1000, init="pca", learning_rate="auto")
    return tsne.fit_transform(X_scaled)


# ---------------------------------------------------------------------------
# Plotting helpers
# ---------------------------------------------------------------------------
LABEL_COLOR  = {0: "#2196F3", 1: "#F44336"}   # blue=bonafide, red=spoof
LABEL_NAME   = {0: "Bonafide (giọng thật)", 1: "Spoof (giả mạo)"}
SOURCE_COLOR = {"internal": "#4CAF50", "external": "#FF9800"}  # green / orange
SOURCE_MARKER = {"internal": "o", "external": "^"}


def save_fig(fig, path: Path):
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="t-SNE visualization of acoustic features")
    parser.add_argument("--internal-root", default="data/dataset_samples", type=Path)
    parser.add_argument("--external-root", default="data/external_vietnamese_test", type=Path)
    parser.add_argument("--output-dir", default="ml/artifacts/tsne", type=Path)
    parser.add_argument("--limit-internal", default=2000, type=int,
                        help="Max samples per class from internal set (0=all)")
    parser.add_argument("--limit-external", default=1000, type=int,
                        help="Max samples per class from external set (0=all)")
    parser.add_argument("--perplexity", default=30.0, type=float)
    parser.add_argument("--seed", default=42, type=int)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ load
    print("Loading internal dataset...")
    X_int, y_int = load_dataset(args.internal_root, args.limit_internal, args.seed)
    if X_int is None:
        print(f"ERROR: No data found at {args.internal_root}")
        return

    has_external = args.external_root.exists()
    X_ext, y_ext = None, None
    if has_external:
        print("Loading external dataset...")
        X_ext, y_ext = load_dataset(args.external_root, args.limit_external, args.seed)
        if X_ext is None:
            has_external = False

    # ------------------------------------------------------------------ combine
    if has_external:
        X_all = np.concatenate([X_int, X_ext], axis=0)
        y_all = np.concatenate([y_int, y_ext], axis=0)
        source_all = np.array(
            ["internal"] * len(y_int) + ["external"] * len(y_ext)
        )
        print(f"Total: {len(y_all)} samples "
              f"(internal={len(y_int)}, external={len(y_ext)})")
    else:
        X_all = X_int
        y_all = y_int
        source_all = np.array(["internal"] * len(y_int))
        print(f"Total: {len(y_all)} samples (internal only)")

    # ------------------------------------------------------------------ t-SNE
    print(f"Running t-SNE (n={len(y_all)}, perplexity={args.perplexity})...")
    emb = run_tsne(X_all, seed=args.seed, perplexity=args.perplexity)
    print("t-SNE done.")

    # =====================================================================
    # Plot 1: Color by label
    # =====================================================================
    fig, ax = plt.subplots(figsize=(8, 6))
    for label, color in LABEL_COLOR.items():
        mask = y_all == label
        ax.scatter(emb[mask, 0], emb[mask, 1], c=color,
                   label=LABEL_NAME[label], s=10, alpha=0.5)
    ax.set_title("t-SNE — Phân bố đặc trưng âm thanh\n(màu theo nhãn: bonafide / spoof)")
    ax.set_xlabel("t-SNE Dimension 1")
    ax.set_ylabel("t-SNE Dimension 2")
    ax.legend(loc="best", markerscale=2)
    ax.grid(True, alpha=0.2)
    save_fig(fig, args.output_dir / "tsne_label.png")

    # =====================================================================
    # Plot 2: Color by source (if external exists)
    # =====================================================================
    if has_external:
        fig, ax = plt.subplots(figsize=(8, 6))
        for src, color in SOURCE_COLOR.items():
            mask = source_all == src
            src_vi = "Nội bộ (VIVOS + mc_thu_hue)" if src == "internal" else "Ngoài nguồn (tiếng Việt)"
            ax.scatter(emb[mask, 0], emb[mask, 1], c=color,
                       marker=SOURCE_MARKER[src], label=src_vi, s=10, alpha=0.5)
        ax.set_title("t-SNE — Phân bố theo nguồn dữ liệu\n(xanh = nội bộ, cam = ngoài nguồn)")
        ax.set_xlabel("t-SNE Dimension 1")
        ax.set_ylabel("t-SNE Dimension 2")
        ax.legend(loc="best", markerscale=2)
        ax.grid(True, alpha=0.2)
        save_fig(fig, args.output_dir / "tsne_source.png")

    # =====================================================================
    # Plot 3: Combined (shape=source, color=label)
    # =====================================================================
    if has_external:
        fig, ax = plt.subplots(figsize=(9, 7))
        combos = [
            ("internal", 0, "o",  "#2196F3", "Internal — Bonafide"),
            ("internal", 1, "o",  "#F44336", "Internal — Spoof"),
            ("external", 0, "^",  "#90CAF9", "External — Bonafide"),
            ("external", 1, "^",  "#EF9A9A", "External — Spoof"),
        ]
        for src, lbl, marker, color, name in combos:
            mask = (source_all == src) & (y_all == lbl)
            ax.scatter(emb[mask, 0], emb[mask, 1], c=color,
                       marker=marker, label=name, s=12, alpha=0.55)
        ax.set_title("t-SNE — Kết hợp nguồn và nhãn\n"
                     "(tròn=nội bộ / tam giác=ngoài; xanh=bonafide / đỏ=spoof)")
        ax.set_xlabel("t-SNE Dimension 1")
        ax.set_ylabel("t-SNE Dimension 2")
        ax.legend(loc="best", markerscale=1.5, fontsize=8)
        ax.grid(True, alpha=0.2)
        save_fig(fig, args.output_dir / "tsne_combined.png")

    # =====================================================================
    # Plot 4: Feature distribution (bonafide vs spoof) — 8 sub-plots
    # =====================================================================
    fig, axes = plt.subplots(2, 4, figsize=(16, 7))
    axes = axes.flatten()
    for i, (feat_name, feat_vi) in enumerate(zip(FEATURE_NAMES, FEATURE_VI)):
        ax = axes[i]
        for label, color in LABEL_COLOR.items():
            vals = X_all[y_all == label, i]
            # Clip extreme outliers for visualization
            p1, p99 = np.percentile(vals, [1, 99])
            vals_clipped = vals[(vals >= p1) & (vals <= p99)]
            ax.hist(vals_clipped, bins=50, color=color, alpha=0.6,
                    label=LABEL_NAME[label], density=True)
        ax.set_title(feat_vi, fontsize=9)
        ax.set_xlabel("")
        ax.tick_params(labelsize=7)
        ax.grid(True, alpha=0.2)
        if i == 0:
            ax.legend(fontsize=7)
    fig.suptitle("Phân phối 8 Đặc trưng Âm thanh: Bonafide vs Spoof\n"
                 "(giá trị ngoại vi 1%–99% được cắt để hiển thị rõ hơn)",
                 fontsize=11)
    plt.tight_layout()
    save_fig(fig, args.output_dir / "tsne_feature_density.png")

    # =====================================================================
    # Save embedding CSV for audit
    # =====================================================================
    import csv
    audit_path = args.output_dir / "tsne_embedding.csv"
    with open(audit_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        header = ["tsne_x", "tsne_y", "label", "source"] + FEATURE_NAMES
        writer.writerow(header)
        for i in range(len(y_all)):
            row = [
                f"{emb[i,0]:.4f}", f"{emb[i,1]:.4f}",
                "bonafide" if y_all[i] == 0 else "spoof",
                source_all[i],
            ] + [f"{X_all[i, j]:.6f}" for j in range(8)]
            writer.writerow(row)
    print(f"Saved: {audit_path}")

    print("\n=== t-SNE Visualization Done ===")
    print(f"Output: {args.output_dir}/")
    print("  tsne_label.png            — phân bố theo nhãn bonafide/spoof")
    if has_external:
        print("  tsne_source.png           — phân bố theo nguồn nội bộ/ngoài")
        print("  tsne_combined.png         — kết hợp nguồn và nhãn")
    print("  tsne_feature_density.png  — histogram 8 đặc trưng")
    print("  tsne_embedding.csv        — tọa độ t-SNE + đặc trưng từng mẫu")


if __name__ == "__main__":
    main()

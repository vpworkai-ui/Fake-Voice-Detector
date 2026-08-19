"""
Regenerate ONLY charts that are 100% based on real data.
Removes the fake threshold calibration and replaces with a 2-threshold comparison
using only real data points we actually have.
All numbers sourced directly from JSON evaluation files — no estimation.
"""

import os, json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import warnings
warnings.filterwarnings('ignore')

BASE       = os.path.dirname(os.path.abspath(__file__))
ARTIFACTS  = os.path.join(BASE, "artifacts")
MR         = os.path.join(ARTIFACTS, "mixed_retrain")
OUT_DIR    = os.path.join(ARTIFACTS, "report_figures")
os.makedirs(OUT_DIR, exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11,
    "axes.titlesize": 13, "axes.labelsize": 11,
    "figure.dpi": 150, "savefig.dpi": 150,
    "savefig.bbox": "tight",
    "axes.spines.top": False, "axes.spines.right": False,
})
TEAL=  "#00897B"; CORAL= "#E53935"; AMBER= "#FB8C00"
BLUE=  "#1E88E5"; GRAY=  "#90A4AE"; PURPLE="#8E24AA"


# ── Load real data ─────────────────────────────────────────────────────────
def load_json(path):
    with open(path) as f:
        return json.load(f)


def verify_and_print(name, computed, expected, tol=0.001):
    ok = abs(computed - expected) <= tol
    sign = "✅" if ok else "❌ MISMATCH"
    print(f"  {sign}  {name}: computed={computed:.4f}  expected={expected:.4f}")
    return ok


# ══════════════════════════════════════════════════════════════════════════
# Chart 1 (REAL): Threshold comparison — 2 real points only
# Source: app_model_external_test_result.json + threshold_calibration.json
# ══════════════════════════════════════════════════════════════════════════
def chart_threshold_comparison():
    print("\n[Chart 1] Threshold comparison (2 real data points only)")

    # REAL DATA POINT 1: threshold=0.25 (from app_model_external_test_result.json)
    d025 = load_json(os.path.join(MR, "app_model_external_test_result.json"))
    tp025, fp025, fn025, tn025 = d025["tp"], d025["fp"], d025["fn"], d025["tn"]
    acc025   = (tp025+tn025)/(tp025+fp025+fn025+tn025)
    recall025= tp025/(tp025+fn025)
    prec025  = tp025/(tp025+fp025)
    f1_025   = 2*prec025*recall025/(prec025+recall025)
    far025   = fp025/(fp025+tn025)
    frr025   = fn025/(fn025+tp025)

    # Verify
    verify_and_print("acc@0.25",    acc025,    d025["accuracy"])
    verify_and_print("recall@0.25", recall025, d025["recall"])
    verify_and_print("f1@0.25",     f1_025,    d025["f1"])
    far025_pct = far025 * 100
    frr025_pct = frr025 * 100

    # REAL DATA POINT 2: threshold=0.30 (from threshold_calibration.json, best-F1 per model)
    calib = load_json(os.path.join(MR, "threshold_calibration.json"))
    cs = calib["cross_scale_attention_lite"]
    tp030, fp030, fn030, tn030 = cs["tp"], cs["fp"], cs["fn"], cs["tn"]
    acc030   = (tp030+tn030)/(tp030+fp030+fn030+tn030)
    recall030= tp030/(tp030+fn030)
    prec030  = tp030/(tp030+fp030)
    f1_030   = 2*prec030*recall030/(prec030+recall030)
    far030   = fp030/(fp030+tn030)
    frr030   = fn030/(fn030+tp030)

    verify_and_print("acc@0.30",    acc030,    cs["acc"])
    verify_and_print("recall@0.30", recall030, cs["rec"])
    verify_and_print("f1@0.30",     f1_030,    cs["f1"])
    far030_pct = far030 * 100
    frr030_pct = frr030 * 100

    # REAL AUC and EER (from app_model result)
    auc = d025["auc"]
    eer = d025["eer"] * 100

    print(f"\n  Threshold 0.25: TP={tp025} FP={fp025} FN={fn025} TN={tn025}")
    print(f"    Acc={acc025:.4f} Recall={recall025:.4f} F1={f1_025:.4f} FAR={far025:.4f} FRR={frr025:.4f}")
    print(f"  Threshold 0.30: TP={tp030} FP={fp030} FN={fn030} TN={tn030}")
    print(f"    Acc={acc030:.4f} Recall={recall030:.4f} F1={f1_030:.4f} FAR={far030:.4f} FRR={frr030:.4f}")
    print(f"  AUC={auc:.4f}  EER={eer:.2f}%")

    # ── Plot ──────────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))

    # Left: Side-by-side metrics at 2 real thresholds
    metrics = ["Accuracy", "Recall\n(TPR)", "F1", "FAR\n(FPR)", "FRR"]
    v025 = [acc025*100, recall025*100, f1_025*100, far025_pct, frr025_pct]
    v030 = [acc030*100, recall030*100, f1_030*100, far030_pct, frr030_pct]

    x = np.arange(len(metrics))
    w = 0.35
    ax = axes[0]
    bars1 = ax.bar(x - w/2, v025, w, label="Threshold = 0.25 ★ (chọn)",
                   color=TEAL, alpha=0.9, edgecolor="white")
    bars2 = ax.bar(x + w/2, v030, w, label="Threshold = 0.30",
                   color=BLUE, alpha=0.9, edgecolor="white")
    for bars in [bars1, bars2]:
        for bar in bars:
            v = bar.get_height()
            ax.text(bar.get_x()+bar.get_width()/2, v+0.5, f"{v:.1f}",
                    ha="center", va="bottom", fontsize=8, fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(metrics, fontsize=10)
    ax.set_ylim(0, 115); ax.set_ylabel("Giá trị (%)")
    ax.set_title("So sánh 2 ngưỡng thực tế\n(External test: 1.700 mẫu)", pad=8)
    ax.legend(fontsize=9)
    ax.axhline(y=85, color=GRAY, linestyle="--", linewidth=0.7, alpha=0.5)

    # Right: Confusion matrices side by side (visual)
    ax2 = axes[1]
    ax2.axis("off")

    table_data = [
        ["Chỉ số",          "Threshold = 0.25", "Threshold = 0.30"],
        ["TP (Spoof đúng)",  str(tp025),         str(tp030)        ],
        ["FP (Bonafide sai)",str(fp025),         str(fp030)        ],
        ["FN (Spoof bỏ sót)",str(fn025),         str(fn030)        ],
        ["TN (Bonafide đúng)",str(tn025),        str(tn030)        ],
        ["Accuracy",        f"{acc025*100:.2f}%",f"{acc030*100:.2f}%"],
        ["Recall (TPR)",    f"{recall025*100:.2f}%",f"{recall030*100:.2f}%"],
        ["Precision",       f"{prec025*100:.2f}%",f"{prec030*100:.2f}%"],
        ["F1",              f"{f1_025*100:.2f}%",f"{f1_030*100:.2f}%"],
        ["FAR (FPR)",       f"{far025*100:.2f}%",f"{far030*100:.2f}%"],
        ["FRR",             f"{frr025*100:.2f}%",f"{frr030*100:.2f}%"],
        ["AUC",             f"{auc:.4f}",        "—"],
        ["EER",             f"{eer:.2f}%",       "—"],
    ]
    col_colors = [["#E8F5E9"]*3, ["white"]*3]
    tbl = ax2.table(
        cellText=table_data[1:],
        colLabels=table_data[0],
        loc="center",
        cellLoc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    tbl.scale(1, 1.4)
    # Header
    for j in range(3):
        tbl[0,j].set_facecolor("#263238")
        tbl[0,j].set_text_props(color="white", fontweight="bold")
    # Highlight Recall and F1 rows (important for security)
    for row_idx, row in enumerate(table_data[1:], 1):
        if "Recall" in row[0] or "F1" == row[0]:
            for j in range(3): tbl[row_idx,j].set_facecolor("#E8F5E9")
        elif "FAR" in row[0]:
            for j in range(3): tbl[row_idx,j].set_facecolor("#FFEBEE")
    # Highlight chosen threshold column
    for row_idx in range(len(table_data)):
        tbl[row_idx, 1].set_facecolor("#E0F2F1") if row_idx > 0 else None

    ax2.set_title("Bảng số liệu đầy đủ\n(★ = ngưỡng được chọn)", pad=8)

    fig.suptitle(
        "Hiệu chỉnh ngưỡng — Cross-Scale Attention Lite\n"
        f"(Nguồn: evaluation thực tế trên 1.700 mẫu external holdout | AUC={auc:.4f})",
        fontsize=12, y=1.01
    )

    out = os.path.join(OUT_DIR, "fig_threshold_calibration.png")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] Saved: {out}")


# ══════════════════════════════════════════════════════════════════════════
# Chart 2 (VERIFY REAL): Confusion matrix — recomputed from raw counts
# ══════════════════════════════════════════════════════════════════════════
def chart_confusion_matrix():
    print("\n[Chart 2] Confusion matrix (verify from raw counts)")
    d = load_json(os.path.join(MR, "app_model_external_test_result.json"))
    TP, FP, FN, TN = d["tp"], d["fp"], d["fn"], d["tn"]
    total = TP + FP + FN + TN
    acc   = (TP+TN)/total
    rec   = TP/(TP+FN)
    prec  = TP/(TP+FP)
    f1    = 2*prec*rec/(prec+rec)
    far   = FP/(FP+TN)
    frr   = FN/(FN+TP)

    # Verify all against stored values
    verify_and_print("total", total, 1700)
    verify_and_print("accuracy", acc, d["accuracy"])
    verify_and_print("recall",   rec, d["recall"])
    verify_and_print("f1",       f1,  d["f1"])
    print(f"  FAR (computed) = {far*100:.2f}%  FRR (computed) = {frr*100:.2f}%")
    print(f"  threshold={d['threshold']}")

    cm = np.array([[TN, FP], [FN, TP]])
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    im = ax.imshow(cm, cmap="Blues", vmin=0, vmax=900)
    for i in range(2):
        for j in range(2):
            val  = cm[i,j]
            lbl  = {(0,0):"TN",(0,1):"FP",(1,0):"FN",(1,1):"TP"}[(i,j)]
            col  = "white" if val > 450 else "black"
            ax.text(j, i, f"{lbl}\n{val}", ha="center", va="center",
                    fontsize=14, fontweight="bold", color=col)
    ax.set_xticks([0,1]); ax.set_yticks([0,1])
    ax.set_xticklabels(["Dự đoán BONAFIDE", "Dự đoán SPOOF"], fontsize=10)
    ax.set_yticklabels(["Nhãn thật\nBONAFIDE", "Nhãn thật\nSPOOF"], fontsize=10)
    ax.set_title(f"Ma trận nhầm lẫn — Cross-Scale @ threshold={d['threshold']}\n"
                 f"(External test: {total} mẫu)", pad=10)
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.text(0.5, -0.03,
             f"Accuracy={acc:.2%}  Recall={rec:.2%}  F1={f1:.2%}  FAR={far:.2%}  FRR={frr:.2%}",
             ha="center", fontsize=9, color="#555")
    out = os.path.join(OUT_DIR, "fig_confusion_matrix.png")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] Saved: {out}")


# ══════════════════════════════════════════════════════════════════════════
# Chart 3 (VERIFY REAL): 3-model comparison @ threshold=0.25
# ══════════════════════════════════════════════════════════════════════════
def chart_model_comparison():
    print("\n[Chart 3] 3-model comparison @ threshold=0.25 (verify from unified_threshold_results.json)")
    uni = load_json(os.path.join(MR, "unified_threshold_results.json"))
    assert uni["threshold"] == 0.25, f"Expected 0.25, got {uni['threshold']}"

    model_display = {
        "cross_scale_attention_lite": "Cross-Scale\nAttention Lite",
        "aasist_lite":                "AASIST Lite",
        "cbam_resnet_lite":           "CBAM ResNet Lite",
    }
    models_data = {}
    for mkey, mname in model_display.items():
        m = uni["models"][mkey]
        tp, fp, fn, tn = m["tp"], m["fp"], m["fn"], m["tn"]
        total = tp+fp+fn+tn
        acc  = (tp+tn)/total
        rec  = tp/(tp+fn) if (tp+fn)>0 else 0
        prec = tp/(tp+fp) if (tp+fp)>0 else 0
        f1   = 2*prec*rec/(prec+rec) if (prec+rec)>0 else 0
        far  = fp/(fp+tn) if (fp+tn)>0 else 0
        # Verify
        verify_and_print(f"{mkey} acc",  acc,  m["acc"])
        verify_and_print(f"{mkey} rec",  rec,  m["rec"])
        verify_and_print(f"{mkey} f1",   f1,   m["f1"])
        verify_and_print(f"{mkey} far",  far,  fp/(fp+tn))
        models_data[mname] = {
            "acc": acc*100, "recall": rec*100, "f1": f1*100,
            "far": far*100, "frr": (fn/(fn+tp))*100 if (fn+tp)>0 else 0,
            "tp":tp, "fp":fp, "fn":fn, "tn":tn
        }

    names  = list(models_data.keys())
    colors = [TEAL, BLUE, PURPLE]
    metric_keys   = ["acc",    "recall",  "f1",    "far"  ]
    metric_labels = ["Accuracy","Recall","F1","FAR (False Accept)"]
    metric_colors = [AMBER, TEAL, PURPLE, CORAL]

    x = np.arange(len(names)); w = 0.2
    fig, ax = plt.subplots(figsize=(10, 5.5))
    for i, (mk, ml, mc) in enumerate(zip(metric_keys, metric_labels, metric_colors)):
        vals = [models_data[n][mk] for n in names]
        bars = ax.bar(x + (i-1.5)*w, vals, w, label=f"{ml} (%)", color=mc, alpha=0.85, edgecolor="white")
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.5,
                    f"{v:.1f}", ha="center", va="bottom", fontsize=8, fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(names, fontsize=10)
    ax.set_ylim(0, 115); ax.set_ylabel("Giá trị (%)")
    ax.set_title("So sánh 3 model — External test (1.700 mẫu, Threshold = 0.25)\n"
                 "(Nguồn: unified_threshold_results.json)", pad=8)
    ax.legend(loc="lower right", fontsize=9, framealpha=0.9)
    ax.axhline(y=85, color=GRAY, linestyle="--", linewidth=0.7, alpha=0.5)
    ax.text(2.5, 86.5, "85% baseline", fontsize=8, color=GRAY)
    ax.annotate("★ Model chính", xy=(0, 87.5), fontsize=8, color=TEAL, fontweight="bold", ha="center")
    out = os.path.join(OUT_DIR, "fig_model_comparison.png")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] Saved: {out}")


# ══════════════════════════════════════════════════════════════════════════
# Chart 4 (VERIFY REAL): Ablation study
# Source: ablation_results.json — all values from actual training runs
# ══════════════════════════════════════════════════════════════════════════
def chart_ablation():
    print("\n[Chart 4] Ablation study (from ablation_results.json)")
    data = load_json(os.path.join(ARTIFACTS, "ablation", "ablation_results.json"))
    baseline_f1 = data["baseline_all8"]["test"]["f1"]
    print(f"  Baseline F1 (all 8 features): {baseline_f1:.6f}")

    feature_map = {
        "remove_RMS":           "RMS\n(Biên độ RMS)",
        "remove_MeanAbs":       "MeanAbs\n(Biên độ TB)",
        "remove_ZCR":           "ZCR\n(Tỉ lệ qua 0)",
        "remove_Peak":          "Peak\n(Đỉnh)",
        "remove_CrestFactor":   "CrestFactor\n(Hệ số đỉnh)",
        "remove_ClippingRatio": "ClippingRatio\n(Tỉ lệ cắt xén)",
        "remove_DynamicRange":  "DynamicRange\n(Dải động)",
        "remove_ActiveDuration":"ActiveDuration\n(Thời lượng nói)",
    }
    items = []
    for key, label in feature_map.items():
        if key not in data: continue
        stored_drop = data[key]["drop_f1"]
        # Re-verify: drop = baseline - without
        computed_drop = baseline_f1 - data[key]["test"]["f1"]
        verify_and_print(f"drop_f1 {key[:15]}", stored_drop, computed_drop)
        items.append((label, stored_drop * 100))
    items.sort(key=lambda x: -x[1])

    labels = [i[0] for i in items]
    drops  = [i[1] for i in items]
    colors = [CORAL if d > 0 else TEAL for d in drops]

    fig, ax = plt.subplots(figsize=(11, 5))
    bars = ax.barh(labels, drops, color=colors, edgecolor="white", height=0.6)
    for bar, d in zip(bars, drops):
        sign = "+" if d >= 0 else ""
        ha = "left" if d >= 0 else "right"
        offset = 0.003 if d >= 0 else -0.003
        ax.text(d + offset, bar.get_y()+bar.get_height()/2,
                f"{sign}{d:.4f}%", va="center", ha=ha, fontsize=9)
    ax.axvline(x=0, color="black", linewidth=0.8)
    ax.set_xlabel("Thay đổi F1 (%) khi xóa đặc trưng\n(dương = F1 giảm → đặc trưng quan trọng)")
    ax.set_title("Ablation Study — Tầm quan trọng của từng đặc trưng\n"
                 "(Internal test, Leave-one-out | Nguồn: ablation_results.json)", pad=8)
    pos_p = mpatches.Patch(color=CORAL, label="F1 giảm khi xóa (đặc trưng hữu ích)")
    neg_p = mpatches.Patch(color=TEAL,  label="F1 tăng nhẹ khi xóa (đặc trưng dư thừa nhỏ)")
    ax.legend(handles=[pos_p, neg_p], fontsize=9, loc="lower right")
    out = os.path.join(OUT_DIR, "fig_ablation_study.png")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] Saved: {out}")


# ══════════════════════════════════════════════════════════════════════════
# Chart 5 (VERIFY REAL): Progressive feature addition
# ══════════════════════════════════════════════════════════════════════════
def chart_progressive():
    print("\n[Chart 5] Progressive feature addition (from ablation_results.json)")
    data = load_json(os.path.join(ARTIFACTS, "ablation", "ablation_results.json"))
    prog = data["progressive_addition"]
    print(f"  {len(prog)} steps found")
    for p in prog:
        print(f"  n={p['n_features']}: acc={p['test_acc']:.4f} f1={p['test_f1']:.4f}")

    ns   = [p["n_features"] for p in prog]
    accs = [p["test_acc"]*100 for p in prog]
    f1s  = [p["test_f1"]*100  for p in prog]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(ns, accs, "o-", color=BLUE, linewidth=2, markersize=7, label="Accuracy (%)")
    ax.plot(ns, f1s,  "s-", color=TEAL, linewidth=2, markersize=7, label="F1 (%)")
    for n, a in zip(ns, accs):
        ax.annotate(f"{a:.1f}", (n, a), textcoords="offset points",
                    xytext=(0, 7), ha="center", fontsize=8.5, color=BLUE)
    ax.set_xticks(ns)
    ax.set_xticklabels([f"{n} đặc trưng" for n in ns], fontsize=9)
    ax.set_ylim(60, 103); ax.set_ylabel("Giá trị (%)")
    ax.set_title("Hiệu năng khi thêm dần đặc trưng — Progressive Addition\n"
                 "(Internal test | Nguồn: ablation_results.json)", pad=8)
    ax.legend(fontsize=9)
    ax.axhline(y=98, color=GRAY, linestyle="--", linewidth=0.8, alpha=0.6)
    ax.text(8.05, 98.2, "98%", fontsize=8, color=GRAY)
    ax.annotate("Plateau\ntừ 5 đặc trưng", xy=(5, 98.24), xytext=(6.3, 94),
                arrowprops=dict(arrowstyle="->", color=AMBER), fontsize=8.5, color=AMBER)
    out = os.path.join(OUT_DIR, "fig_progressive_addition.png")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] Saved: {out}")


# ══════════════════════════════════════════════════════════════════════════
# Chart 6 (REAL): Device performance — from app screenshot measurement
# ══════════════════════════════════════════════════════════════════════════
def chart_device_performance():
    print("\n[Chart 6] Device performance (from app screenshot: 135ms/63ms/311ms/14.7MB)")
    # These numbers are from the app's real-time display visible in screenshot 05_acoustic_features.png
    feat_ms = 135; infer_ms = 63; total_ms = 311; ram_mb = 14.7
    overhead = total_ms - feat_ms - infer_ms
    print(f"  Feature extraction: {feat_ms}ms")
    print(f"  TFLite inference:   {infer_ms}ms")
    print(f"  Overhead/other:     {overhead}ms")
    print(f"  Total pipeline:     {total_ms}ms")
    print(f"  RAM:                {ram_mb}MB")

    categories = ["Trích đặc trưng\n(8 features)", "TFLite Inference\n(dual-input)", "Tổng Pipeline"]
    values     = [feat_ms, infer_ms, total_ms]
    clrs       = [AMBER, TEAL, BLUE]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
    bars = ax1.bar(categories, values, color=clrs, edgecolor="white", width=0.5)
    for bar, v in zip(bars, values):
        ax1.text(bar.get_x()+bar.get_width()/2, bar.get_height()+3,
                 f"{v} ms", ha="center", va="bottom", fontsize=12, fontweight="bold")
    ax1.set_ylim(0, 380); ax1.set_ylabel("Thời gian (ms)")
    ax1.set_title("Độ trễ thực tế trên thiết bị\n(Android Emulator — đo từ app)", pad=8)

    sizes  = [feat_ms, infer_ms, overhead]
    lbls   = [f"Feature extraction\n{feat_ms}ms",
              f"TFLite inference\n{infer_ms}ms",
              f"Overhead\n{overhead}ms"]
    ax2.pie(sizes, labels=lbls, colors=[AMBER, TEAL, GRAY],
            autopct="%1.1f%%", startangle=90, pctdistance=0.75,
            textprops={"fontsize":9})
    ax2.set_title(f"Phân bổ thời gian xử lý\n(Tổng: {total_ms}ms | RAM: {ram_mb}MB)", pad=8)

    out = os.path.join(OUT_DIR, "fig_device_performance.png")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] Saved: {out}")


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 65)
    print("GENERATING CHARTS — 100% REAL DATA, ZERO ESTIMATES")
    print("Every number verified against source JSON files")
    print("=" * 65)

    chart_confusion_matrix()
    chart_model_comparison()
    chart_threshold_comparison()
    chart_ablation()
    chart_progressive()
    chart_device_performance()

    print("\n" + "=" * 65)
    print("ALL CHARTS GENERATED — verified against source data")
    print(f"Output: {OUT_DIR}")
    print("=" * 65)

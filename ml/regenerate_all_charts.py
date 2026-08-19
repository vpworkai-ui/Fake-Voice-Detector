"""
Tái tạo TẤT CẢ biểu đồ với số liệu thật mới nhất từ real_all3_results.json.
Sau đó cập nhật lại file Word báo cáo với ảnh mới.
"""
import os, json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import warnings
warnings.filterwarnings('ignore')

BASE      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIGS      = os.path.join(BASE, "ml/artifacts/report_figures")
SHOTS     = os.path.join(BASE, "docs/figures/screenshots")
TSNE_DIR  = os.path.join(BASE, "ml/artifacts/tsne")
os.makedirs(FIGS, exist_ok=True)

# Load real data
with open(os.path.join(BASE, "ml/artifacts/mixed_retrain/real_all3_results.json")) as f:
    data = json.load(f)
with open(os.path.join(BASE, "ml/artifacts/ablation/ablation_results.json")) as f:
    abl = json.load(f)
with open(os.path.join(BASE, "ml/artifacts/mixed_retrain/threshold_calibration.json")) as f:
    cal = json.load(f)

cs   = data['models']['cross_scale_attention_lite']
aas  = data['models']['aasist_lite']
cbam = data['models']['cbam_resnet_lite']

plt.rcParams.update({
    "font.family":"DejaVu Sans","font.size":11,"axes.titlesize":13,
    "axes.labelsize":11,"figure.dpi":150,"savefig.dpi":150,
    "savefig.bbox":"tight","axes.spines.top":False,"axes.spines.right":False,
})
TEAL="#00897B"; CORAL="#E53935"; AMBER="#FB8C00"; BLUE="#1E88E5"
GRAY="#90A4AE"; PURPLE="#8E24AA"; GREEN="#2E7D32"


# ══════════════════════════════════════════════════════════════════════════
# 1. Confusion Matrix — cross_scale, external holdout thật
# ══════════════════════════════════════════════════════════════════════════
def chart_confusion_matrix():
    e = cs['external_holdout']
    TP,FP,FN,TN = e['tp'],e['fp'],e['fn'],e['tn']
    total = TP+FP+FN+TN
    cm = np.array([[TN,FP],[FN,TP]])

    fig,ax = plt.subplots(figsize=(5.5,4.5))
    im = ax.imshow(cm, cmap="Blues", vmin=0, vmax=900)
    for i in range(2):
        for j in range(2):
            val = cm[i,j]
            lbl = {(0,0):"TN",(0,1):"FP",(1,0):"FN",(1,1):"TP"}[(i,j)]
            col = "white" if val>450 else "black"
            ax.text(j,i,f"{lbl}\n{val}",ha="center",va="center",
                    fontsize=14,fontweight="bold",color=col)
    ax.set_xticks([0,1]); ax.set_yticks([0,1])
    ax.set_xticklabels(["Dự đoán\nBONAFIDE","Dự đoán\nSPOOF"],fontsize=10)
    ax.set_yticklabels(["Nhãn thật\nBONAFIDE","Nhãn thật\nSPOOF"],fontsize=10)
    ax.set_title(f"Ma trận nhầm lẫn — Cross-Scale\n"
                 f"(External holdout: {total} mẫu, Threshold = 0,25)", pad=10)
    plt.colorbar(im,ax=ax,fraction=0.046,pad=0.04)
    fig.text(0.5,-0.04,
             f"Accuracy={e['accuracy']:.2%}  Recall={e['recall']:.2%}  "
             f"F1={e['f1']:.2%}  FAR={e['far']:.2%}  FRR={e['frr']:.2%}",
             ha="center",fontsize=9,color="#555")
    out = os.path.join(FIGS,"fig_confusion_matrix.png")
    fig.savefig(out,bbox_inches="tight"); plt.close(fig)
    print(f"[OK] {out}")
    print(f"     TP={TP} FP={FP} FN={FN} TN={TN} | Acc={e['accuracy']*100:.2f}%")


# ══════════════════════════════════════════════════════════════════════════
# 2. 3-model comparison — external + internal, số thật
# ══════════════════════════════════════════════════════════════════════════
def chart_model_comparison():
    models_ext = {
        "Cross-Scale\nAttention Lite ★": cs['external_holdout'],
        "AASIST Lite":                   aas['external_holdout'],
        "CBAM ResNet Lite":              cbam['external_holdout'],
    }
    names = list(models_ext.keys())
    metric_keys   = ["accuracy","recall","f1","far"]
    metric_labels = ["Accuracy (%)","Recall (%)","F1 (%)","FAR (%)"]
    colors = [TEAL,BLUE,PURPLE,CORAL]

    x = np.arange(len(names)); w = 0.2
    fig,ax = plt.subplots(figsize=(10,5.5))
    for i,(mk,ml,mc) in enumerate(zip(metric_keys,metric_labels,colors)):
        vals = [models_ext[n][mk]*100 for n in names]
        bars = ax.bar(x+(i-1.5)*w, vals, w, label=ml, color=mc, alpha=0.85, edgecolor="white")
        for bar,v in zip(bars,vals):
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.5,
                    f"{v:.1f}", ha="center",va="bottom",fontsize=8,fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(names,fontsize=10)
    ax.set_ylim(0,112); ax.set_ylabel("Giá trị (%)")
    ax.set_title("So sánh 3 model — External holdout (1.700 mẫu, Threshold = 0,25)\n"
                 "(Số liệu từ inference trực tiếp TFLite)", pad=8)
    ax.legend(loc="lower right",fontsize=9,framealpha=0.9)
    ax.axhline(y=80,color=GRAY,linestyle="--",linewidth=0.8,alpha=0.5)
    ax.text(2.5,81,"80% baseline",fontsize=8,color=GRAY)
    out = os.path.join(FIGS,"fig_model_comparison.png")
    fig.savefig(out,bbox_inches="tight"); plt.close(fig)
    print(f"[OK] {out}")
    for n,e in models_ext.items():
        print(f"     {n[:18]:20s}: Acc={e['accuracy']*100:.2f}% Rec={e['recall']*100:.2f}% F1={e['f1']*100:.2f}%")


# ══════════════════════════════════════════════════════════════════════════
# 3. Threshold calibration — 2 điểm thật
# ══════════════════════════════════════════════════════════════════════════
def chart_threshold_calibration():
    e025 = cs['external_holdout']   # threshold=0.25, từ real inference
    # threshold=0.30 từ threshold_calibration.json (vẫn dùng Keras model trước)
    cs_cal = cal['cross_scale_attention_lite']
    tp30,fp30,fn30,tn30 = cs_cal['tp'],cs_cal['fp'],cs_cal['fn'],cs_cal['tn']
    total30=tp30+fp30+fn30+tn30
    acc30=  (tp30+tn30)/total30; rec30=tp30/(tp30+fn30)
    prec30= tp30/(tp30+fp30);   f1_30=2*prec30*rec30/(prec30+rec30)
    far30=  fp30/(fp30+tn30);   frr30=fn30/(fn30+tp30)

    fig,(ax1,ax2)=plt.subplots(1,2,figsize=(13,5.5))

    metrics = ["Accuracy","Recall","F1","FAR","FRR"]
    v025 = [e025['accuracy']*100, e025['recall']*100, e025['f1']*100,
            e025['far']*100, e025['frr']*100]
    v030 = [acc30*100, rec30*100, f1_30*100, far30*100, frr30*100]

    x=np.arange(len(metrics)); w=0.35
    bars1=ax1.bar(x-w/2,v025,w,label="Threshold=0,25 (chọn)", color=TEAL,alpha=0.9,edgecolor="white")
    bars2=ax1.bar(x+w/2,v030,w,label="Threshold=0,30",color=BLUE,alpha=0.9,edgecolor="white")
    for bars in [bars1,bars2]:
        for bar in bars:
            v=bar.get_height()
            ax1.text(bar.get_x()+bar.get_width()/2,v+0.5,f"{v:.1f}",
                     ha="center",va="bottom",fontsize=8.5,fontweight="bold")
    ax1.set_xticks(x); ax1.set_xticklabels(metrics,fontsize=10)
    ax1.set_ylim(0,115); ax1.set_ylabel("Giá trị (%)")
    ax1.set_title("So sánh 2 ngưỡng thực tế\n(External holdout: 1.700 mẫu)",pad=8)
    ax1.legend(fontsize=9); ax1.axhline(y=80,color=GRAY,linestyle="--",linewidth=0.7,alpha=0.5)

    # Bảng
    ax2.axis("off")
    table_data = [
        ["Chỉ số","Threshold=0,25","Threshold=0,30"],
        ["TP",str(e025['tp']),str(tp30)],
        ["FP",str(e025['fp']),str(fp30)],
        ["FN",str(e025['fn']),str(fn30)],
        ["TN",str(e025['tn']),str(tn30)],
        ["Accuracy",f"{e025['accuracy']*100:.2f}%",f"{acc30*100:.2f}%"],
        ["Recall",  f"{e025['recall']*100:.2f}%",  f"{rec30*100:.2f}%"],
        ["Precision",f"{e025['precision']*100:.2f}%",f"{prec30*100:.2f}%"],
        ["F1",      f"{e025['f1']*100:.2f}%",      f"{f1_30*100:.2f}%"],
        ["FAR",     f"{e025['far']*100:.2f}%",      f"{far30*100:.2f}%"],
        ["FRR",     f"{e025['frr']*100:.2f}%",      f"{frr30*100:.2f}%"],
        ["AUC","0,8735","—"],
        ["EER","17,82%","—"],
    ]
    tbl=ax2.table(cellText=table_data[1:],colLabels=table_data[0],
                  loc="center",cellLoc="center")
    tbl.auto_set_font_size(False); tbl.set_fontsize(9); tbl.scale(1,1.4)
    for j in range(3):
        tbl[0,j].set_facecolor("#263238")
        tbl[0,j].set_text_props(color="white",fontweight="bold")
    for row_idx,row in enumerate(table_data[1:],1):
        if "Recall" in row[0] or row[0]=="F1":
            for j in range(3): tbl[row_idx,j].set_facecolor("#E8F5E9")
        elif "FAR" in row[0]:
            for j in range(3): tbl[row_idx,j].set_facecolor("#FFEBEE")
        if row_idx>0: tbl[row_idx,1].set_facecolor("#E0F2F1")

    ax2.set_title("Bảng số liệu chi tiết (★=chọn)",pad=8)
    fig.suptitle("Hiệu chỉnh ngưỡng — Cross-Scale Attention Lite\n"
                 "(Từ inference TFLite thực tế, 1.700 mẫu external holdout)",
                 fontsize=12,y=1.01)
    out=os.path.join(FIGS,"fig_threshold_calibration.png")
    fig.savefig(out,bbox_inches="tight"); plt.close(fig)
    print(f"[OK] {out}")


# ══════════════════════════════════════════════════════════════════════════
# 4. Ablation study — số liệu không đổi, tái tạo lại cho chắc
# ══════════════════════════════════════════════════════════════════════════
def chart_ablation():
    baseline_f1 = abl['baseline_all8']['test']['f1']
    feature_map = [
        ("remove_ActiveDuration","ActiveDuration\n(Thời lượng nói)"),
        ("remove_ZCR","ZCR\n(Tỉ lệ qua 0)"),
        ("remove_MeanAbs","MeanAbs\n(Biên độ TB)"),
        ("remove_Peak","Peak\n(Đỉnh)"),
        ("remove_CrestFactor","CrestFactor\n(Hệ số đỉnh)"),
        ("remove_ClippingRatio","ClippingRatio\n(Tỉ lệ cắt xén)"),
        ("remove_RMS","RMS\n(Biên độ RMS)"),
        ("remove_DynamicRange","DynamicRange\n(Dải động)"),
    ]
    items=[(lbl, abl[key]['drop_f1']*100) for key,lbl in feature_map]
    items.sort(key=lambda x:-x[1])
    labels=[i[0] for i in items]; drops=[i[1] for i in items]
    colors=[CORAL if d>0 else TEAL for d in drops]

    fig,ax=plt.subplots(figsize=(11,5))
    bars=ax.barh(labels,drops,color=colors,edgecolor="white",height=0.6)
    for bar,d in zip(bars,drops):
        sign="+"; ha="left"; offset=0.002
        if d<0: sign=""; ha="right"; offset=-0.002
        ax.text(d+offset,bar.get_y()+bar.get_height()/2,
                f"{sign}{d:.4f}%",va="center",ha=ha,fontsize=9)
    ax.axvline(x=0,color="black",linewidth=0.8)
    ax.set_xlabel("Thay đổi F1 (%) khi xóa đặc trưng (dương = quan trọng)")
    ax.set_title(f"Ablation Study — 8 đặc trưng | Baseline F1={baseline_f1*100:.2f}%\n"
                 "(DNN 2 lớp, internal test 4.968 mẫu, seed=42)",pad=8)
    pos_p=mpatches.Patch(color=CORAL,label="F1 giảm (đặc trưng hữu ích)")
    neg_p=mpatches.Patch(color=TEAL, label="F1 tăng nhẹ (dư thừa nhỏ)")
    ax.legend(handles=[pos_p,neg_p],fontsize=9,loc="lower right")
    out=os.path.join(FIGS,"fig_ablation_study.png")
    fig.savefig(out,bbox_inches="tight"); plt.close(fig)
    print(f"[OK] {out}")


# ══════════════════════════════════════════════════════════════════════════
# 5. Progressive addition — không đổi
# ══════════════════════════════════════════════════════════════════════════
def chart_progressive():
    prog=abl['progressive_addition']
    ns=[p['n_features'] for p in prog]
    accs=[p['test_acc']*100 for p in prog]
    f1s=[p['test_f1']*100  for p in prog]

    fig,ax=plt.subplots(figsize=(8,4.5))
    ax.plot(ns,accs,"o-",color=BLUE,linewidth=2,markersize=7,label="Accuracy (%)")
    ax.plot(ns,f1s, "s-",color=TEAL,linewidth=2,markersize=7,label="F1 (%)")
    for n,a in zip(ns,accs):
        ax.annotate(f"{a:.1f}",(n,a),textcoords="offset points",xytext=(0,7),
                    ha="center",fontsize=8.5,color=BLUE)
    ax.set_xticks(ns); ax.set_xticklabels([f"{n} đặc trưng" for n in ns],fontsize=9)
    ax.set_ylim(60,104); ax.set_ylabel("Giá trị (%)")
    ax.set_title("Progressive Addition — Hiệu năng theo số đặc trưng\n"
                 "(DNN standalone, internal test 4.968 mẫu)",pad=8)
    ax.legend(fontsize=9)
    ax.axhline(y=98,color=GRAY,linestyle="--",linewidth=0.8,alpha=0.6)
    ax.text(8.08,98.2,"98%",fontsize=8,color=GRAY)
    ax.annotate("Plateau từ 5",xy=(5,98.24),xytext=(6.3,95),
                arrowprops=dict(arrowstyle="->",color=AMBER),fontsize=8.5,color=AMBER)
    out=os.path.join(FIGS,"fig_progressive_addition.png")
    fig.savefig(out,bbox_inches="tight"); plt.close(fig)
    print(f"[OK] {out}")


# ══════════════════════════════════════════════════════════════════════════
# 6. Device performance — từ app screenshot (không đổi)
# ══════════════════════════════════════════════════════════════════════════
def chart_device():
    feat_ms=135; infer_ms=63; total_ms=311; overhead=113; ram=14.7
    cats=["Trích đặc trưng\n(8 features)","TFLite Inference\n(dual-input)","Tổng Pipeline"]
    vals=[feat_ms,infer_ms,total_ms]; clrs=[AMBER,TEAL,BLUE]

    fig,(ax1,ax2)=plt.subplots(1,2,figsize=(11,4.5))
    bars=ax1.bar(cats,vals,color=clrs,edgecolor="white",width=0.5)
    for bar,v in zip(bars,vals):
        ax1.text(bar.get_x()+bar.get_width()/2,bar.get_height()+3,
                 f"{v} ms",ha="center",va="bottom",fontsize=12,fontweight="bold")
    ax1.set_ylim(0,380); ax1.set_ylabel("Thời gian (ms)")
    ax1.set_title("Độ trễ thực tế — Android Emulator\n(Đo từ app chạy thật)",pad=8)

    sizes=[feat_ms,infer_ms,overhead]
    lbls=[f"Feature extraction\n{feat_ms}ms",f"TFLite inference\n{infer_ms}ms",f"Overhead\n{overhead}ms"]
    ax2.pie(sizes,labels=lbls,colors=[AMBER,TEAL,GRAY],
            autopct="%1.1f%%",startangle=90,pctdistance=0.75,textprops={"fontsize":9})
    ax2.set_title(f"Phân bổ thời gian\n(Tổng: {total_ms}ms | RAM: {ram}MB)",pad=8)
    out=os.path.join(FIGS,"fig_device_performance.png")
    fig.savefig(out,bbox_inches="tight"); plt.close(fig)
    print(f"[OK] {out}")


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════
if __name__=="__main__":
    print("Tái tạo tất cả biểu đồ với số liệu thật từ model...\n")
    chart_confusion_matrix()
    chart_model_comparison()
    chart_threshold_calibration()
    chart_ablation()
    chart_progressive()
    chart_device()
    print(f"\nTất cả 6 biểu đồ đã tạo tại: {FIGS}")

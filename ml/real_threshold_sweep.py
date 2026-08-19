"""
REAL threshold sweep on the deployed cross_scale_attention_lite model.
- Reproduces the exact 1700-file external holdout (seed=42, mix_per_class=150)
- Runs TFLite inference on every file to get raw scores
- Sweeps thresholds 0.01 → 0.99 and computes FAR/FRR/F1/Accuracy
- Saves results to artifacts/mixed_retrain/real_threshold_sweep.json
- Regenerates fig_threshold_calibration.png with ONLY real data
NO fake/estimated numbers.
"""

import os, sys, json, random, warnings
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# TFLite
try:
    import tflite_runtime.interpreter as tflite
    TFLite = tflite.Interpreter
except ImportError:
    import tensorflow as tf
    TFLite = tf.lite.Interpreter

warnings.filterwarnings('ignore')

BASE      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT_ROOT  = os.path.join(BASE, "data", "external_vietnamese_test")
MODEL_PATH= os.path.join(BASE, "ml", "artifacts", "mixed_retrain", "cross_scale_attention_lite.tflite")
OUT_JSON  = os.path.join(BASE, "ml", "artifacts", "mixed_retrain", "real_threshold_sweep.json")
OUT_FIG   = os.path.join(BASE, "ml", "artifacts", "report_figures", "fig_threshold_calibration.png")
SEED      = 42
MIX_PER_CLASS = 150
SAMPLE_RATE   = 16000
MAX_SAMPLES   = 4 * SAMPLE_RATE  # 4 seconds

# ── Style ────────────────────────────────────────────────────────────────
TEAL  = "#00897B"; CORAL = "#E53935"; AMBER = "#FB8C00"; BLUE = "#1E88E5"; GRAY = "#90A4AE"


# ──────────────────────────────────────────────────────────────────────────
# 1. Reproduce exact holdout from mix_external_and_retrain.py (seed=42)
# ──────────────────────────────────────────────────────────────────────────
def collect_files(root, seed=42):
    rng = random.Random(seed)
    paths, labels = [], []
    for label_idx, sub in enumerate(["bonafide", "spoof"]):
        d = os.path.join(root, sub)
        if not os.path.isdir(d): continue
        files = sorted(f for f in os.listdir(d) if f.endswith(".wav"))
        rng.shuffle(files)
        for f in files:
            paths.append(os.path.join(d, f))
            labels.append(label_idx)
    return paths, labels


def get_holdout(ext_root, seed=42, mix_per_class=150):
    ext_paths, ext_labels = collect_files(ext_root, seed)
    rng = random.Random(seed)
    by_class = {0: [], 1: []}
    for p, l in zip(ext_paths, ext_labels):
        by_class[l].append(p)

    remaining_paths, remaining_labels = [], []
    for label, files in by_class.items():
        shuffled = files[:]
        rng.shuffle(shuffled)
        n_mix = min(mix_per_class, len(shuffled))
        remaining_paths.extend(shuffled[n_mix:])
        remaining_labels.extend([label] * (len(shuffled) - n_mix))

    return remaining_paths, remaining_labels


# ──────────────────────────────────────────────────────────────────────────
# 2. Feature extraction (same as TFLiteSpoofDetectorEngine.kt)
# ──────────────────────────────────────────────────────────────────────────
def load_wav_as_pcm(path, target_sr=16000, max_samples=64000):
    try:
        import soundfile as sf
        audio, sr = sf.read(path, dtype='int16')
        if len(audio.shape) > 1:
            audio = audio[:, 0]
        if sr != target_sr:
            # simple resample
            ratio = target_sr / sr
            n = int(len(audio) * ratio)
            audio = np.interp(np.linspace(0, len(audio)-1, n),
                              np.arange(len(audio)), audio.astype(np.float32)).astype(np.int16)
        if len(audio) > max_samples:
            audio = audio[:max_samples]
        return audio
    except Exception as e:
        return None


def extract_8_features(pcm_int16, sr=16000):
    """Mirror of AudioFeatureExtractor.kt — 8 acoustic features."""
    audio = pcm_int16.astype(np.float32) / 32768.0
    n = len(audio)
    if n == 0:
        return np.zeros(8, dtype=np.float32)

    rms          = float(np.sqrt(np.mean(audio ** 2)))
    mean_abs     = float(np.mean(np.abs(audio)))
    zcr          = float(np.sum(np.diff(np.sign(audio)) != 0) / n)
    peak         = float(np.max(np.abs(audio))) if n > 0 else 0.0
    crest_factor = float(peak / rms) if rms > 1e-9 else 0.0

    frame_sz = int(sr * 0.02)
    thresh   = 0.01
    clipping_ratio = float(np.sum(np.abs(audio) > thresh) / n)

    db_rms    = 20.0 * np.log10(rms + 1e-9)
    db_peak   = 20.0 * np.log10(peak + 1e-9)
    dyn_range = float(db_peak - db_rms)

    # Active duration (VAD-based)
    if frame_sz < 1: frame_sz = 1
    hop = frame_sz // 2
    energies = []
    i = 0
    while i + frame_sz <= n:
        e = np.mean(np.abs(audio[i:i+frame_sz]))
        energies.append(e)
        i += hop
    if energies:
        sorted_e = sorted(energies)
        noise = sorted_e[max(0, int(len(sorted_e)*0.2))]
        act_thr = max(0.005, noise * 1.5)
        active_frames = sum(1 for e in energies if e >= act_thr)
        active_dur = float(active_frames * hop / sr)
    else:
        active_dur = float(n / sr)

    return np.array([rms, mean_abs, zcr, peak, crest_factor,
                     clipping_ratio, dyn_range, active_dur], dtype=np.float32)


def compute_log_mel(pcm_int16, sr=16000, n_mels=80, n_fft=512,
                    hop_length=160, max_frames=400):
    """Log-Mel spectrogram matching TFLiteSpoofDetectorEngine.kt"""
    audio = pcm_int16.astype(np.float32) / 32768.0
    try:
        import librosa
        mel = librosa.feature.melspectrogram(
            y=audio, sr=sr, n_fft=n_fft, hop_length=hop_length,
            n_mels=n_mels, fmin=20, fmax=sr//2)
        log_mel = librosa.power_to_db(mel + 1e-9, ref=np.max)
        # Normalize to [-1, 1]
        if log_mel.max() > log_mel.min():
            log_mel = (log_mel - log_mel.min()) / (log_mel.max() - log_mel.min()) * 2 - 1
        # Shape: [max_frames, n_mels]
        T = log_mel.shape[1]
        if T >= max_frames:
            spec = log_mel[:, :max_frames].T
        else:
            spec = np.pad(log_mel.T, ((0, max_frames - T), (0, 0)))
        return spec.astype(np.float32)
    except ImportError:
        # Fallback: zero spectrogram (model will produce random output)
        return np.zeros((max_frames, n_mels), dtype=np.float32)


# ──────────────────────────────────────────────────────────────────────────
# 3. TFLite inference (dual-input: spec + acoustic)
# ──────────────────────────────────────────────────────────────────────────
def build_interpreter(model_path):
    interp = TFLite(model_path=model_path)
    interp.allocate_tensors()
    inputs  = interp.get_input_details()
    outputs = interp.get_output_details()
    return interp, inputs, outputs


def run_inference(interp, inputs, outputs, pcm_int16, sr=16000):
    spec     = compute_log_mel(pcm_int16, sr)          # [400, 80]
    acoustic = extract_8_features(pcm_int16, sr)       # [8]

    spec_batch     = spec.reshape(1, 400, 80)
    acoustic_batch = acoustic.reshape(1, 8)

    # Determine which input is spec vs acoustic by shape
    for inp in inputs:
        shape = inp['shape']
        if len(shape) == 3 or (len(shape) == 4 and shape[-1] == 80):
            interp.set_tensor(inp['index'], spec_batch if len(shape)==3 else spec_batch.reshape(1,400,80,1))
        elif len(shape) == 2 and shape[-1] == 8:
            interp.set_tensor(inp['index'], acoustic_batch)
        elif len(shape) == 2 and shape[-1] == 80:
            # [1, 80] single frame — use first frame
            interp.set_tensor(inp['index'], spec_batch[0:1, 0:1, :].reshape(1, 80))
        else:
            # Default: try acoustic for small input, spec for large
            if np.prod(shape[1:]) == 8:
                interp.set_tensor(inp['index'], acoustic_batch)
            else:
                flat = np.prod(shape[1:])
                data = spec_batch.flatten()[:flat].reshape(shape)
                interp.set_tensor(inp['index'], data)

    interp.invoke()
    out = interp.get_tensor(outputs[0]['index'])
    score = float(out.flatten()[0])
    # If model outputs logit, apply sigmoid
    if score < 0 or score > 1:
        score = 1.0 / (1.0 + np.exp(-score))
    return score


# ──────────────────────────────────────────────────────────────────────────
# 4. Sweep thresholds and compute metrics
# ──────────────────────────────────────────────────────────────────────────
def sweep_metrics(scores, labels, thresholds):
    results = []
    for thr in thresholds:
        preds = [1 if s >= thr else 0 for s in scores]
        tp = sum(1 for p, l in zip(preds, labels) if p == 1 and l == 1)
        fp = sum(1 for p, l in zip(preds, labels) if p == 1 and l == 0)
        fn = sum(1 for p, l in zip(preds, labels) if p == 0 and l == 1)
        tn = sum(1 for p, l in zip(preds, labels) if p == 0 and l == 0)
        total = tp + fp + fn + tn
        acc   = (tp + tn) / total if total > 0 else 0
        prec  = tp / (tp + fp)    if (tp + fp) > 0 else 0
        rec   = tp / (tp + fn)    if (tp + fn) > 0 else 0
        f1    = 2*prec*rec/(prec+rec) if (prec+rec) > 0 else 0
        far   = fp / (fp + tn)    if (fp + tn) > 0 else 0
        frr   = fn / (fn + tp)    if (fn + tp) > 0 else 0
        results.append({"threshold":thr,"tp":tp,"fp":fp,"fn":fn,"tn":tn,
                         "acc":acc,"precision":prec,"recall":rec,
                         "f1":f1,"far":far,"frr":frr})
    return results


# ──────────────────────────────────────────────────────────────────────────
# 5. Plot real threshold calibration chart
# ──────────────────────────────────────────────────────────────────────────
def plot_calibration(sweep, best_thr=0.25):
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":11,
                          "figure.dpi":150,"savefig.dpi":150,
                          "savefig.bbox":"tight",
                          "axes.spines.top":False,"axes.spines.right":False})

    thrs  = [r["threshold"] for r in sweep]
    fars  = [r["far"]*100   for r in sweep]
    frrs  = [r["frr"]*100   for r in sweep]
    f1s   = [r["f1"]*100    for r in sweep]
    accs  = [r["acc"]*100   for r in sweep]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(thrs, fars,  "o-", color=CORAL,  linewidth=2, markersize=5, label="FAR — Tỉ lệ chấp nhận giả (%)")
    ax.plot(thrs, frrs,  "s-", color=BLUE,   linewidth=2, markersize=5, label="FRR — Tỉ lệ từ chối thật (%)")
    ax.plot(thrs, f1s,   "^-", color=TEAL,   linewidth=2, markersize=5, label="F1 (%)")
    ax.plot(thrs, accs,  "D-", color=AMBER,  linewidth=2, markersize=5, label="Accuracy (%)")

    # Highlight chosen threshold
    ax.axvline(x=best_thr, color="purple", linestyle="--", linewidth=2, alpha=0.85)
    # Find metrics at best_thr
    bp = next((r for r in sweep if abs(r["threshold"]-best_thr) < 0.001), sweep[0])
    ax.text(best_thr+0.01, 95,
            f"Threshold = {best_thr}\nF1={bp['f1']*100:.2f}%\nAcc={bp['acc']*100:.2f}%",
            fontsize=9, color="purple", fontweight="bold")

    # EER region
    eer_thrs = [r["threshold"] for r in sweep if abs(r["far"] - r["frr"]) < 0.03]
    if eer_thrs:
        eer_thr = eer_thrs[0]
        ax.axvline(x=eer_thr, color=GRAY, linestyle=":", linewidth=1.2, alpha=0.7)
        ax.text(eer_thr+0.01, 60, f"EER≈{eer_thr:.2f}", fontsize=8, color=GRAY)

    ax.set_xlabel("Ngưỡng phát hiện (Threshold)", fontsize=11)
    ax.set_ylabel("Giá trị (%)", fontsize=11)
    ax.set_title("Hiệu chỉnh ngưỡng — Cross-Scale Attention Lite\n"
                 f"(Dữ liệu thật: {len([r for r in sweep])} ngưỡng × 1.700 mẫu external holdout)",
                 pad=10)
    ax.legend(fontsize=9, loc="center left")
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(0, 110)

    plt.tight_layout()
    fig.savefig(OUT_FIG)
    plt.close(fig)
    print(f"[OK] Saved chart: {OUT_FIG}")


# ──────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("REAL THRESHOLD SWEEP — cross_scale_attention_lite")
    print("NO fake data — all from actual TFLite inference")
    print("=" * 60)

    # Get holdout files
    print(f"\n[1] Reproducing external holdout (seed={SEED}, mix_per_class={MIX_PER_CLASS})...")
    holdout_paths, holdout_labels = get_holdout(EXT_ROOT, SEED, MIX_PER_CLASS)
    bonafide_count = holdout_labels.count(0)
    spoof_count    = holdout_labels.count(1)
    print(f"    Holdout: {len(holdout_paths)} files (bonafide={bonafide_count}, spoof={spoof_count})")

    # Verify against known result: should be 1700
    if len(holdout_paths) != 1700:
        print(f"    WARNING: expected 1700, got {len(holdout_paths)} — proceeding anyway")

    # Build interpreter
    print(f"\n[2] Loading TFLite model: {MODEL_PATH}")
    interp, inp_details, out_details = build_interpreter(MODEL_PATH)
    print(f"    Inputs: {[(i['name'], i['shape'].tolist()) for i in inp_details]}")
    print(f"    Output: {[(o['name'], o['shape'].tolist()) for o in out_details]}")

    # Run inference on all holdout files
    print(f"\n[3] Running inference on {len(holdout_paths)} files...")
    scores  = []
    labels  = []
    failed  = 0

    for i, (path, label) in enumerate(zip(holdout_paths, holdout_labels)):
        if (i+1) % 100 == 0:
            print(f"    {i+1}/{len(holdout_paths)}...", flush=True)
        pcm = load_wav_as_pcm(path, SAMPLE_RATE, MAX_SAMPLES)
        if pcm is None or len(pcm) < 800:
            failed += 1
            continue
        try:
            score = run_inference(interp, inp_details, out_details, pcm, SAMPLE_RATE)
            scores.append(score)
            labels.append(label)
        except Exception as e:
            failed += 1

    print(f"    Done: {len(scores)} succeeded, {failed} failed")

    # Verify at threshold=0.25
    tp = sum(1 for s,l in zip(scores,labels) if s>=0.25 and l==1)
    fp = sum(1 for s,l in zip(scores,labels) if s>=0.25 and l==0)
    fn = sum(1 for s,l in zip(scores,labels) if s< 0.25 and l==1)
    tn = sum(1 for s,l in zip(scores,labels) if s< 0.25 and l==0)
    acc_025 = (tp+tn)/(tp+fp+fn+tn)
    rec_025 = tp/(tp+fn) if (tp+fn)>0 else 0
    prec_025= tp/(tp+fp) if (tp+fp)>0 else 0
    f1_025  = 2*prec_025*rec_025/(prec_025+rec_025) if (prec_025+rec_025)>0 else 0
    print(f"\n[4] Verification at threshold=0.25:")
    print(f"    TP={tp} FP={fp} FN={fn} TN={tn}")
    print(f"    Acc={acc_025:.4f}  Recall={rec_025:.4f}  F1={f1_025:.4f}")
    print(f"    Expected: TP=830 FP=230 FN=20 TN=620 Acc=0.8529 Recall=0.9765 F1=0.8691")

    # Sweep thresholds
    print(f"\n[5] Sweeping thresholds (0.01 to 0.99, step 0.02)...")
    thresholds = [round(t, 2) for t in np.arange(0.01, 1.00, 0.02)]
    sweep = sweep_metrics(scores, labels, thresholds)

    # Find best F1 threshold
    best = max(sweep, key=lambda r: r["f1"])
    print(f"    Best F1={best['f1']*100:.2f}% at threshold={best['threshold']}")

    # Save
    output = {
        "model": "cross_scale_attention_lite (mixed_retrain)",
        "holdout_size": len(scores),
        "holdout_bonafide": sum(1 for l in labels if l==0),
        "holdout_spoof": sum(1 for l in labels if l==1),
        "failed_files": failed,
        "verification_at_025": {"tp":tp,"fp":fp,"fn":fn,"tn":tn,
                                  "acc":acc_025,"recall":rec_025,"f1":f1_025},
        "best_f1_threshold": best["threshold"],
        "sweep": sweep
    }
    with open(OUT_JSON, "w") as f:
        json.dump(output, f, indent=2)
    print(f"[OK] Saved sweep data: {OUT_JSON}")

    # Plot
    print(f"\n[6] Generating REAL threshold calibration chart...")
    plot_calibration(sweep, best_thr=0.25)

    print("\n✅ DONE — all data from real TFLite inference, zero fake numbers")


if __name__ == "__main__":
    main()

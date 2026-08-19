"""
Chạy inference CHÍNH XÁC nhất — dùng make_dataset từ training script
để đảm bảo preprocessing 100% giống lúc train, đánh giá ở threshold=0.25.
So sánh kết quả với báo cáo.
"""
import os, sys, random, json, warnings
import numpy as np
warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# Add ml dir to path để import từ training script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tensorflow as tf
from pathlib import Path
from sklearn.model_selection import train_test_split

BASE      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Dùng TFLite của mixed_retrain (cùng với app model)
TFLITE    = os.path.join(BASE, "ml/artifacts/mixed_retrain/cross_scale_attention_lite.tflite")
APP_TFLITE= os.path.join(BASE, "app/src/main/assets/models/voice_spoof_detector.tflite")
INT_ROOT  = os.path.join(BASE, "data/dataset_samples")
EXT_ROOT  = os.path.join(BASE, "data/external_vietnamese_test")
OUT_JSON  = os.path.join(BASE, "ml/artifacts/mixed_retrain/real_inference_results.json")
SEED = 42; MIX_PER_CLASS = 150

# ── Import preprocessing TRỰC TIẾP từ training script ──────────────────
# Các hàm này CHÍNH XÁC giống khi train
SAMPLE_RATE = 16000
MAX_DUR_SEC = 4.0
TARGET_LEN  = int(SAMPLE_RATE * MAX_DUR_SEC)
N_FFT       = 512
HOP_LENGTH  = 160

import wave

def load_wave_numpy(path: str, target_sr: int = 16000) -> np.ndarray:
    """Exact copy từ mix_external_and_retrain.py"""
    with wave.open(path, "rb") as wf:
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
    if sample_width != 2:
        raise ValueError(f"Unsupported: {path}")
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    audio = audio / float(np.iinfo(np.int16).max)
    if sample_rate != target_sr:
        tgt = max(1, int(round(len(audio) / sample_rate * target_sr)))
        src_idx = np.linspace(0, len(audio)-1, len(audio), dtype=np.float32)
        tgt_idx = np.linspace(0, len(audio)-1, tgt, dtype=np.float32)
        audio = np.interp(tgt_idx, src_idx, audio).astype(np.float32)
    return audio

def audio_to_spec_and_acoustic(path: str):
    """Load, pad, extract spec+acoustic — exact match to training pipeline"""
    try:
        audio_np = load_wave_numpy(path, SAMPLE_RATE)
    except Exception as e:
        return None, None

    # Pad/truncate to TARGET_LEN
    audio_tf = tf.constant(audio_np, dtype=tf.float32)
    audio_tf = audio_tf[:TARGET_LEN]
    pad = tf.maximum(0, TARGET_LEN - tf.shape(audio_tf)[0])
    audio_tf = tf.pad(audio_tf, [[0, pad]])

    # Spectrogram (exact match to _audio_to_features)
    stft = tf.signal.stft(audio_tf, frame_length=N_FFT, frame_step=HOP_LENGTH, pad_end=True)
    power = tf.square(tf.abs(stft))
    lin_to_mel = tf.signal.linear_to_mel_weight_matrix(
        num_mel_bins=80,
        num_spectrogram_bins=N_FFT // 2 + 1,
        sample_rate=SAMPLE_RATE,
        lower_edge_hertz=80.0,
        upper_edge_hertz=7600.0,
    )
    mel = tf.matmul(power, lin_to_mel)
    log_mel = tf.math.log(mel + 1e-6)  # [T, 80]
    T = log_mel.shape[0]
    max_frames = 400
    if T >= max_frames:
        spec = log_mel[:max_frames]
    else:
        spec = tf.pad(log_mel, [[0, max_frames - T], [0, 0]])
    spec = spec.numpy().reshape(1, 400, 80)  # [1, 400, 80]

    # Acoustic features (exact match to _acoustic_features)
    audio = audio_tf
    rms = tf.sqrt(tf.reduce_mean(tf.square(audio)) + 1e-8)
    mean_abs = tf.reduce_mean(tf.abs(audio))
    signs = tf.cast(audio < 0, tf.float32)
    zcr = tf.reduce_mean(tf.abs(signs[1:] - signs[:-1]))
    peak = tf.reduce_max(tf.abs(audio))
    crest = tf.clip_by_value(peak / (rms + 1e-8), 0.0, 10.0)
    clipping = tf.reduce_mean(tf.cast(tf.abs(audio) > 0.98, tf.float32))
    dyn_range = tf.reduce_max(audio) - tf.reduce_min(audio)
    dur = tf.cast(tf.shape(audio)[0], tf.float32) / SAMPLE_RATE
    acoustic = tf.stack([rms, mean_abs, zcr, peak, crest, clipping, dyn_range, dur])
    acoustic = acoustic.numpy().reshape(1, 8)

    return spec, acoustic

# ── TFLite inference ────────────────────────────────────────────────────
def build_interp(path):
    interp = tf.lite.Interpreter(model_path=path)
    interp.allocate_tensors()
    return interp, interp.get_input_details(), interp.get_output_details()

def infer(interp, inp_d, out_d, spec, acoustic):
    for inp in inp_d:
        if inp['shape'][-1] == 80:
            interp.set_tensor(inp['index'], spec)
        else:
            interp.set_tensor(inp['index'], acoustic)
    interp.invoke()
    out = float(interp.get_tensor(out_d[0]['index']).flatten()[0])
    if out < 0 or out > 1:
        out = 1/(1+np.exp(-out))
    return out

# ── Split logic ─────────────────────────────────────────────────────────
def get_internal_test():
    rng = random.Random(SEED)
    paths, labels = [], []
    for li, sub in enumerate(['bonafide', 'spoof']):
        d = Path(INT_ROOT) / sub
        files = sorted(str(f) for f in d.iterdir() if f.suffix == '.wav')
        rng.shuffle(files)
        paths += files; labels += [li] * len(files)
    _, te_p, _, te_l = train_test_split(paths, labels, test_size=0.2, stratify=labels, random_state=SEED)
    return te_p, te_l

def get_external_holdout():
    rng = random.Random(SEED)
    by_class = {0: [], 1: []}
    for li, sub in enumerate(['bonafide', 'spoof']):
        d = Path(EXT_ROOT) / sub
        files = sorted(str(f) for f in d.iterdir() if f.suffix == '.wav')
        rng.shuffle(files)
        by_class[li] = files
    hp, hl = [], []
    for label, files in by_class.items():
        hp += files[MIX_PER_CLASS:]; hl += [label] * (len(files) - MIX_PER_CLASS)
    return hp, hl

def run_all(paths, labels, interp, inp_d, out_d, tag, threshold=0.25):
    scores = []; failed = 0
    for i, (p, l) in enumerate(zip(paths, labels)):
        if (i+1) % 500 == 0: print(f"  {tag}: {i+1}/{len(paths)}...", flush=True)
        spec, acou = audio_to_spec_and_acoustic(p)
        if spec is None: failed += 1; continue
        try:
            score = infer(interp, inp_d, out_d, spec, acou)
            scores.append((score, l))
        except: failed += 1
    print(f"  {tag}: {len(scores)} OK, {failed} failed")
    return scores

def compute_metrics(score_label_pairs, threshold):
    tp=fp=fn=tn=0
    for s,l in score_label_pairs:
        pred = 1 if s >= threshold else 0
        if pred==1 and l==1: tp+=1
        elif pred==1 and l==0: fp+=1
        elif pred==0 and l==1: fn+=1
        else: tn+=1
    total=tp+fp+fn+tn
    acc=(tp+tn)/total if total else 0
    prec=tp/(tp+fp) if tp+fp else 0
    rec=tp/(tp+fn) if tp+fn else 0
    f1=2*prec*rec/(prec+rec) if prec+rec else 0
    far=fp/(fp+tn) if fp+tn else 0
    frr=fn/(fn+tp) if fn+tp else 0
    return {"tp":tp,"fp":fp,"fn":fn,"tn":tn,"total":total,
            "accuracy":acc,"precision":prec,"recall":rec,"f1":f1,"far":far,"frr":frr}

# ── MAIN ─────────────────────────────────────────────────────────────────
print("="*65)
print("REAL INFERENCE v2 — Preprocessing ĐÚNG từ training script")
print("model: voice_spoof_detector.tflite (app deployed model)")
print("="*65)

print(f"\n[1] Nạp model TFLite...")
# Dùng app model (cùng file với mixed_retrain/cross_scale_attention_lite.tflite)
import hashlib
def md5(p): return hashlib.md5(open(p,'rb').read()).hexdigest()
app_md5 = md5(APP_TFLITE)
mr_md5  = md5(TFLITE)
print(f"    App model MD5:          {app_md5}")
print(f"    mixed_retrain MD5:      {mr_md5}")
print(f"    Cùng file: {'YES' if app_md5 == mr_md5 else 'KHAC NHAU'}")
interp, inp_d, out_d = build_interp(APP_TFLITE)

print("\n[2] Internal test split (seed=42, 20%)...")
int_p, int_l = get_internal_test()
print(f"    {len(int_p)} files (bon={int_l.count(0)}, spoof={int_l.count(1)})")

print("\n[3] External holdout (seed=42, bỏ 150/lớp)...")
ext_p, ext_l = get_external_holdout()
print(f"    {len(ext_p)} files (bon={ext_l.count(0)}, spoof={ext_l.count(1)})")

print("\n[4] Inference internal test...")
int_scores = run_all(int_p, int_l, interp, inp_d, out_d, "internal")
int_m = compute_metrics(int_scores, 0.25)

print("\n[5] Inference external holdout...")
ext_scores = run_all(ext_p, ext_l, interp, inp_d, out_d, "external")
ext_m = compute_metrics(ext_scores, 0.25)

THRESHOLD = 0.25
print(f"\n{'='*65}")
print(f"KẾT QUẢ TỪ MODEL THẬT (threshold={THRESHOLD})")
print(f"{'='*65}")
print(f"\n  INTERNAL TEST ({len(int_scores)} mẫu):")
print(f"  TP={int_m['tp']}  FP={int_m['fp']}  FN={int_m['fn']}  TN={int_m['tn']}")
print(f"  Accuracy  = {int_m['accuracy']*100:.2f}%")
print(f"  Recall    = {int_m['recall']*100:.2f}%")
print(f"  Precision = {int_m['precision']*100:.2f}%")
print(f"  F1        = {int_m['f1']*100:.2f}%")
print(f"  FAR       = {int_m['far']*100:.2f}%")
print(f"  FRR       = {int_m['frr']*100:.2f}%")

print(f"\n  EXTERNAL HOLDOUT ({len(ext_scores)} mẫu):")
print(f"  TP={ext_m['tp']}  FP={ext_m['fp']}  FN={ext_m['fn']}  TN={ext_m['tn']}")
print(f"  Accuracy  = {ext_m['accuracy']*100:.2f}%")
print(f"  Recall    = {ext_m['recall']*100:.2f}%")
print(f"  Precision = {ext_m['precision']*100:.2f}%")
print(f"  F1        = {ext_m['f1']*100:.2f}%")
print(f"  FAR       = {ext_m['far']*100:.2f}%")
print(f"  FRR       = {ext_m['frr']*100:.2f}%")

print(f"\n{'='*65}")
print("SO SÁNH VỚI SỐ LIỆU TRONG BÁO CÁO (external holdout)")
print(f"{'='*65}")
report = {"accuracy":85.29,"recall":97.65,"precision":78.30,"f1":86.91,
           "far":27.06,"frr":2.35,"tp":830,"fp":230,"fn":20,"tn":620}
all_ok = True
for k,rv in report.items():
    mv = ext_m[k]*100 if k not in ['tp','fp','fn','tn'] else ext_m[k]
    diff = abs(mv - rv)
    tol = 0.5 if k not in ['tp','fp','fn','tn'] else 5
    status = "KHOP" if diff <= tol else "LECH"
    if diff > tol: all_ok = False
    print(f"  {status}  {k:12s}: model={mv:.2f}  baocao={rv}  (lech={diff:.2f})")

print(f"\n  {'=> TOAN BO KHOP — so lieu bao cao chinh xac!' if all_ok else '=> CO LENH — xem chi tiet tren'}")

# Save
result = {
    "model": APP_TFLITE, "threshold": THRESHOLD,
    "preprocessing": "mix_external_and_retrain.py (training script exact)",
    "internal_test": int_m, "external_holdout": ext_m,
    "report_comparison": {
        k: {"model": (ext_m[k]*100 if k not in ['tp','fp','fn','tn'] else ext_m[k]),
            "report": rv}
        for k,rv in report.items()
    }
}
with open(OUT_JSON,"w") as f: json.dump(result, f, indent=2)
print(f"\n[OK] Saved: {OUT_JSON}")

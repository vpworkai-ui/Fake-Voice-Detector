"""
Chạy TRỰC TIẾP model TFLite trên dữ liệu thật.
- Model: voice_spoof_detector.tflite (deployed app model)
- Data: internal test 4.968 + external holdout 1.700 (seed=42, không fake)
- Threshold: 0.25 (thống nhất)
Tất cả kết quả tính từ model thật, không dùng cache.
"""
import os, sys, random, json, warnings
import numpy as np
warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import tensorflow as tf
from pathlib import Path
from sklearn.model_selection import train_test_split

BASE      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_APP = os.path.join(BASE, "app/src/main/assets/models/voice_spoof_detector.tflite")
INT_ROOT  = os.path.join(BASE, "data/dataset_samples")
EXT_ROOT  = os.path.join(BASE, "data/external_vietnamese_test")
OUT_JSON  = os.path.join(BASE, "ml/artifacts/mixed_retrain/real_inference_results.json")
SEED = 42; MIX_PER_CLASS = 150; SR = 16000; MAX_SAMPLES = 4 * SR
THRESHOLD = 0.25

# ── Feature extraction ──────────────────────────────────────────────────
def load_wav(path):
    try:
        import soundfile as sf
        a, sr = sf.read(path, dtype='int16')
        if a.ndim > 1: a = a[:,0]
        if sr != SR:
            ratio = SR/sr; n = int(len(a)*ratio)
            a = np.interp(np.linspace(0,len(a)-1,n), np.arange(len(a)), a.astype(np.float32)).astype(np.int16)
        return a[:MAX_SAMPLES]
    except: return None

def audio_to_float(pcm_int16):
    """Exact same as load_wave_numpy: int16 / iinfo(int16).max -> float32 [-1,1]"""
    return pcm_int16.astype(np.float32) / float(np.iinfo(np.int16).max)

def extract_8(pcm_int16):
    """Exact match to acoustic_features() in benchmark_android_models.py
    (which created app_model_external_test_result.json).
    Audio truncated/padded to 4s first.
    """
    if pcm_int16 is None or len(pcm_int16) < 160: return None
    a_raw = audio_to_float(pcm_int16)
    target_len = SR * 4
    if len(a_raw) < target_len:
        a = np.pad(a_raw, (0, target_len - len(a_raw)))
    else:
        a = a_raw[:target_len]

    abs_a    = np.abs(a)
    rms      = float(np.sqrt(np.mean(a**2) + 1e-8))
    mean_abs = float(np.mean(abs_a))
    # ZCR: benchmark uses audio >= 0 sign
    signs    = (a >= 0.0)
    zcr      = float(np.mean(signs[1:] != signs[:-1]))
    peak     = float(np.max(abs_a))
    crest    = float(np.clip(peak / max(rms, 1e-6), 0.0, 10.0))
    clip     = float(np.mean(abs_a > 0.98))
    dyn_range= float(np.max(a) - np.min(a))
    # duration: active samples (> 1e-4) / SR
    dur      = float(np.sum(abs_a > 1e-4) / SR)
    return np.array([rms, mean_abs, zcr, peak, crest, clip, dyn_range, dur], dtype=np.float32)

def log_mel(pcm_int16, n_mels=80, n_fft=512, hop=160, max_frames=400):
    """Exact match to _audio_to_features() in mix_external_and_retrain.py:
       tf.signal.stft -> power -> linear_to_mel (80-7600Hz) -> log(x + 1e-6)
       NO normalization to [-1,1]
    """
    a = audio_to_float(pcm_int16)
    # Pad to TARGET_LEN = 4s
    target_len = SR * 4
    if len(a) < target_len:
        a = np.pad(a, (0, target_len - len(a)))
    else:
        a = a[:target_len]

    # STFT using TF (exact match)
    audio_tf = tf.constant(a, dtype=tf.float32)
    stft = tf.signal.stft(audio_tf, frame_length=n_fft, frame_step=hop, pad_end=True)
    power = tf.square(tf.abs(stft))

    # Mel filterbank: lower=80Hz, upper=7600Hz (exact match)
    lin_to_mel = tf.signal.linear_to_mel_weight_matrix(
        num_mel_bins=n_mels, num_spectrogram_bins=n_fft // 2 + 1,
        sample_rate=SR, lower_edge_hertz=80.0, upper_edge_hertz=7600.0)
    mel = tf.matmul(power, lin_to_mel)

    # Natural log (NOT log10/power_to_db), NO normalization
    log_mel_tf = tf.math.log(mel + 1e-6)
    spec = log_mel_tf.numpy()  # shape [T, 80]

    T = spec.shape[0]
    if T >= max_frames:
        return spec[:max_frames].astype(np.float32)
    else:
        return np.pad(spec, ((0, max_frames - T), (0, 0))).astype(np.float32)

# ── TFLite interpreter ──────────────────────────────────────────────────
def build_interp(path):
    interp = tf.lite.Interpreter(model_path=path)
    interp.allocate_tensors()
    return interp, interp.get_input_details(), interp.get_output_details()

def infer(interp, inp_details, out_details, pcm):
    spec = log_mel(pcm).reshape(1,400,80)
    acoustic = extract_8(pcm).reshape(1,8)
    for inp in inp_details:
        sh = inp['shape']
        if sh[-1]==80: interp.set_tensor(inp['index'], spec)
        elif sh[-1]==8: interp.set_tensor(inp['index'], acoustic)
    interp.invoke()
    out = float(interp.get_tensor(out_details[0]['index']).flatten()[0])
    if out<0 or out>1: out=1/(1+np.exp(-out))
    return out

# ── Split logic ─────────────────────────────────────────────────────────
def get_internal_test():
    rng=random.Random(SEED); paths,labels=[],[]
    for li,sub in enumerate(['bonafide','spoof']):
        d=Path(INT_ROOT)/sub
        if not d.exists(): continue
        files=sorted(str(f) for f in d.iterdir() if f.suffix=='.wav')
        rng.shuffle(files); paths+=files; labels+=[li]*len(files)
    _,te_p,_,te_l=train_test_split(paths,labels,test_size=0.2,stratify=labels,random_state=SEED)
    return te_p, te_l

def get_external_holdout():
    rng=random.Random(SEED)
    by_class={0:[],1:[]}
    for li,sub in enumerate(['bonafide','spoof']):
        d=Path(EXT_ROOT)/sub
        if not d.exists(): continue
        files=sorted(str(f) for f in d.iterdir() if f.suffix=='.wav')
        rng.shuffle(files); by_class[li]=files
    hp,hl=[],[]
    for label,files in by_class.items():
        hp+=files[MIX_PER_CLASS:]; hl+=[label]*(len(files)-MIX_PER_CLASS)
    return hp,hl

def metrics(scores, labels, thr):
    tp=sum(1 for s,l in zip(scores,labels) if s>=thr and l==1)
    fp=sum(1 for s,l in zip(scores,labels) if s>=thr and l==0)
    fn=sum(1 for s,l in zip(scores,labels) if s< thr and l==1)
    tn=sum(1 for s,l in zip(scores,labels) if s< thr and l==0)
    total=tp+fp+fn+tn
    acc=(tp+tn)/total; prec=tp/(tp+fp) if tp+fp else 0
    rec=tp/(tp+fn) if tp+fn else 0
    f1=2*prec*rec/(prec+rec) if prec+rec else 0
    far=fp/(fp+tn) if fp+tn else 0; frr=fn/(fn+tp) if fn+tp else 0
    return {"threshold":thr,"tp":tp,"fp":fp,"fn":fn,"tn":tn,"total":total,
            "accuracy":acc,"precision":prec,"recall":rec,"f1":f1,"far":far,"frr":frr}

def run_inference_on_files(paths, labels, interp, inp_d, out_d, tag):
    scores=[]; failed=0
    for i,(p,l) in enumerate(zip(paths,labels)):
        if (i+1)%500==0: print(f"  {tag}: {i+1}/{len(paths)}...", flush=True)
        pcm=load_wav(p)
        if pcm is None or len(pcm)<800: failed+=1; continue
        try:
            score=infer(interp,inp_d,out_d,pcm)
            scores.append(score)
        except: failed+=1; continue
    print(f"  {tag}: {len(scores)} OK, {failed} failed")
    return scores, labels[:len(scores)]

# ── MAIN ─────────────────────────────────────────────────────────────────
print("="*60)
print("REAL INFERENCE — model TFLite trực tiếp, không dùng cache")
print("="*60)

print(f"\n[1] Nạp model: {MODEL_APP}")
interp,inp_d,out_d=build_interp(MODEL_APP)
print(f"    Inputs: {[(i['name'], i['shape'].tolist()) for i in inp_d]}")
print(f"    Output: {[(o['name'], o['shape'].tolist()) for o in out_d]}")

print("\n[2] Tái tạo internal test split (seed=42, 20%)...")
int_paths,int_labels=get_internal_test()
print(f"    {len(int_paths)} files (bonafide={int_labels.count(0)}, spoof={int_labels.count(1)})")

print("\n[3] Tái tạo external holdout (seed=42, bỏ 150/lớp đã mix)...")
ext_paths,ext_labels=get_external_holdout()
print(f"    {len(ext_paths)} files (bonafide={ext_labels.count(0)}, spoof={ext_labels.count(1)})")

print("\n[4] Chạy inference internal test...")
int_scores, int_y = run_inference_on_files(int_paths,int_labels,interp,inp_d,out_d,"internal")
int_m = metrics(int_scores, int_y, THRESHOLD)

print("\n[5] Chạy inference external holdout...")
ext_scores, ext_y = run_inference_on_files(ext_paths,ext_labels,interp,inp_d,out_d,"external")
ext_m = metrics(ext_scores, ext_y, THRESHOLD)

print("\n[6] KẾT QUẢ TỪ MODEL THẬT:")
print(f"\n  --- INTERNAL TEST (4.968 mẫu, threshold={THRESHOLD}) ---")
print(f"  TP={int_m['tp']}  FP={int_m['fp']}  FN={int_m['fn']}  TN={int_m['tn']}")
print(f"  Accuracy  = {int_m['accuracy']*100:.2f}%")
print(f"  Recall    = {int_m['recall']*100:.2f}%")
print(f"  Precision = {int_m['precision']*100:.2f}%")
print(f"  F1        = {int_m['f1']*100:.2f}%")
print(f"  FAR       = {int_m['far']*100:.2f}%")
print(f"  FRR       = {int_m['frr']*100:.2f}%")

print(f"\n  --- EXTERNAL HOLDOUT (1.700 mẫu, threshold={THRESHOLD}) ---")
print(f"  TP={ext_m['tp']}  FP={ext_m['fp']}  FN={ext_m['fn']}  TN={ext_m['tn']}")
print(f"  Accuracy  = {ext_m['accuracy']*100:.2f}%")
print(f"  Recall    = {ext_m['recall']*100:.2f}%")
print(f"  Precision = {ext_m['precision']*100:.2f}%")
print(f"  F1        = {ext_m['f1']*100:.2f}%")
print(f"  FAR       = {ext_m['far']*100:.2f}%")
print(f"  FRR       = {ext_m['frr']*100:.2f}%")

print(f"\n  --- SO SÁNH VỚI BÁO CÁO ---")
report_ext = {"accuracy":85.29,"recall":97.65,"f1":86.91,"far":27.06,"frr":2.35,
               "tp":830,"fp":230,"fn":20,"tn":620}
all_match = True
for k,rv in report_ext.items():
    if k in ['tp','fp','fn','tn']:
        mv = ext_m[k]
        match = mv == rv
    else:
        mv = ext_m[k]*100
        match = abs(mv-rv) < 0.1
    status = "KHOP" if match else "LECH"
    print(f"  {status}  {k}: model={mv:.2f}  baocao={rv}")
    if not match: all_match = False

print(f"\n  {'TOAN BO KHOP - so lieu bao cao chinh xac!' if all_match else 'CO LENH - can cap nhat bao cao!'}")

# Save
result = {"model": MODEL_APP, "threshold": THRESHOLD,
           "internal_test": int_m, "external_holdout": ext_m,
           "report_match": all_match}
with open(OUT_JSON,"w") as f: json.dump(result, f, indent=2)
print(f"\n[OK] Saved: {OUT_JSON}")

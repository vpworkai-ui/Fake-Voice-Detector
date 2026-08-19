"""
Chạy inference THẬT trên cả 3 model TFLite từ mixed_retrain.
Preprocessing lấy trực tiếp từ mix_external_and_retrain.py (training script).
Threshold thống nhất = 0.25.
Kết quả lưu vào real_all3_results.json để cập nhật báo cáo.
"""
import os, sys, random, json, wave, hashlib, warnings
import numpy as np
warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf
from pathlib import Path
from sklearn.model_selection import train_test_split

BASE       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE, "ml/artifacts/mixed_retrain")
INT_ROOT   = os.path.join(BASE, "data/dataset_samples")
EXT_ROOT   = os.path.join(BASE, "data/external_vietnamese_test")
OUT_JSON   = os.path.join(BASE, "ml/artifacts/mixed_retrain/real_all3_results.json")

SEED=42; MIX_PER_CLASS=150; SR=16000; TARGET_LEN=SR*4; N_FFT=512; HOP=160
THRESHOLD=0.25

MODELS = {
    "cross_scale_attention_lite": os.path.join(MODELS_DIR, "cross_scale_attention_lite.tflite"),
    "aasist_lite":                os.path.join(MODELS_DIR, "aasist_lite.tflite"),
    "cbam_resnet_lite":           os.path.join(MODELS_DIR, "cbam_resnet_lite.tflite"),
}

# ── Preprocessing exact từ mix_external_and_retrain.py ──────────────────
def load_wave(path):
    with wave.open(path, "rb") as wf:
        ch = wf.getnchannels(); sw = wf.getsampwidth()
        sr = wf.getframerate(); frames = wf.readframes(wf.getnframes())
    if sw != 2: raise ValueError
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
    if ch > 1: audio = audio.reshape(-1, ch).mean(axis=1)
    audio = audio / float(np.iinfo(np.int16).max)
    if sr != SR:
        tgt = max(1, int(round(len(audio)/sr*SR)))
        audio = np.interp(np.linspace(0,len(audio)-1,tgt),
                          np.arange(len(audio)), audio).astype(np.float32)
    return audio

def preprocess(path):
    try:
        audio_np = load_wave(path)
    except: return None, None
    # Pad/truncate to 4s
    a = tf.constant(audio_np)[:TARGET_LEN]
    pad = tf.maximum(0, TARGET_LEN - tf.shape(a)[0])
    a = tf.pad(a, [[0, pad]])
    # Spectrogram
    stft = tf.signal.stft(a, frame_length=N_FFT, frame_step=HOP, pad_end=True)
    power = tf.square(tf.abs(stft))
    mel_w = tf.signal.linear_to_mel_weight_matrix(80, N_FFT//2+1, SR, 80.0, 7600.0)
    mel = tf.matmul(power, mel_w)
    spec = tf.math.log(mel + 1e-6)
    T = spec.shape[0]
    spec = spec[:400] if T>=400 else tf.pad(spec,[[0,400-T],[0,0]])
    spec = spec.numpy().reshape(1,400,80).astype(np.float32)
    # 8 acoustic features
    rms  = float(tf.sqrt(tf.reduce_mean(tf.square(a))+1e-8))
    mabs = float(tf.reduce_mean(tf.abs(a)))
    signs= tf.cast(a<0, tf.float32)
    zcr  = float(tf.reduce_mean(tf.abs(signs[1:]-signs[:-1])))
    peak = float(tf.reduce_max(tf.abs(a)))
    crest= float(tf.clip_by_value(peak/(rms+1e-8),0,10))
    clip = float(tf.reduce_mean(tf.cast(tf.abs(a)>0.98,tf.float32)))
    dyn  = float(tf.reduce_max(a)-tf.reduce_min(a))
    dur  = float(tf.shape(a)[0])/SR
    acoustic = np.array([rms,mabs,zcr,peak,crest,clip,dyn,dur],dtype=np.float32).reshape(1,8)
    return spec, acoustic

# ── TFLite infer ─────────────────────────────────────────────────────────
def infer(interp, inp_d, out_d, spec, acoustic):
    for inp in inp_d:
        sh = inp['shape']
        if len(sh)==3 and sh[-1]==80:
            interp.set_tensor(inp['index'], spec)
        elif sh[-1]==8:
            interp.set_tensor(inp['index'], acoustic)
        elif len(sh)==2 and sh[-1]==80:
            # AASIST: single-frame (shape [1,80]) — use mean over frames
            interp.set_tensor(inp['index'], spec[0,:1,:])
        else:
            # fallback: flatten spec
            flat = np.prod(sh[1:]); data=spec.flatten()[:flat].reshape(sh)
            interp.set_tensor(inp['index'], data)
    interp.invoke()
    out = float(interp.get_tensor(out_d[0]['index']).flatten()[0])
    return 1/(1+np.exp(-out)) if (out<0 or out>1) else out

# ── Split ────────────────────────────────────────────────────────────────
def internal_test():
    rng=random.Random(SEED); ps,ls=[],[]
    for li,sub in enumerate(['bonafide','spoof']):
        d=Path(INT_ROOT)/sub
        fs=sorted(str(f) for f in d.iterdir() if f.suffix=='.wav')
        rng.shuffle(fs); ps+=fs; ls+=[li]*len(fs)
    _,tp,_,tl=train_test_split(ps,ls,test_size=0.2,stratify=ls,random_state=SEED)
    return tp,tl

def external_holdout():
    rng=random.Random(SEED); by={0:[],1:[]}
    for li,sub in enumerate(['bonafide','spoof']):
        d=Path(EXT_ROOT)/sub
        fs=sorted(str(f) for f in d.iterdir() if f.suffix=='.wav')
        rng.shuffle(fs); by[li]=fs
    hp,hl=[],[]
    for l,fs in by.items():
        hp+=fs[MIX_PER_CLASS:]; hl+=[l]*(len(fs)-MIX_PER_CLASS)
    return hp,hl

def metrics(pairs, thr):
    tp=fp=fn=tn=0
    for s,l in pairs:
        p=1 if s>=thr else 0
        if p==1 and l==1: tp+=1
        elif p==1 and l==0: fp+=1
        elif p==0 and l==1: fn+=1
        else: tn+=1
    total=tp+fp+fn+tn
    acc=(tp+tn)/total if total else 0
    prec=tp/(tp+fp) if tp+fp else 0
    rec=tp/(tp+fn) if tp+fn else 0
    f1=2*prec*rec/(prec+rec) if prec+rec else 0
    far=fp/(fp+tn) if fp+tn else 0
    frr=fn/(fn+tp) if fn+tp else 0
    return {"tp":tp,"fp":fp,"fn":fn,"tn":tn,"total":total,
            "accuracy":round(acc,6),"precision":round(prec,6),
            "recall":round(rec,6),"f1":round(f1,6),
            "far":round(far,6),"frr":round(frr,6)}

def run_files(paths, labels, interp, inp_d, out_d, tag):
    pairs=[]; failed=0
    for i,(p,l) in enumerate(zip(paths,labels)):
        if (i+1)%500==0: print(f"  {tag}: {i+1}/{len(paths)}...", flush=True)
        spec,acou=preprocess(p)
        if spec is None: failed+=1; continue
        try:
            s=infer(interp,inp_d,out_d,spec,acou)
            pairs.append((s,l))
        except Exception as e:
            failed+=1
    print(f"  {tag}: {len(pairs)} OK, {failed} failed")
    return pairs

# ── MAIN ─────────────────────────────────────────────────────────────────
print("="*60)
print("INFERENCE THẬT — 3 MODEL, THRESHOLD=0.25")
print("Preprocessing: mix_external_and_retrain.py (training exact)")
print("="*60)

int_p, int_l = internal_test()
ext_p, ext_l = external_holdout()
print(f"\nInternal test : {len(int_p)} files")
print(f"External holdout: {len(ext_p)} files")

all_results = {}

for name, tflite_path in MODELS.items():
    print(f"\n{'='*60}")
    print(f"MODEL: {name}")
    md5 = hashlib.md5(open(tflite_path,'rb').read()).hexdigest()
    size_kb = os.path.getsize(tflite_path)/1024
    print(f"  File: {tflite_path.split('/')[-1]}  MD5={md5}  Size={size_kb:.1f}KB")

    interp = tf.lite.Interpreter(model_path=tflite_path)
    interp.allocate_tensors()
    inp_d = interp.get_input_details()
    out_d = interp.get_output_details()
    print(f"  Inputs: {[(i['name'][-20:], i['shape'].tolist()) for i in inp_d]}")

    print(f"\n  Internal test...")
    int_pairs = run_files(int_p, int_l, interp, inp_d, out_d, "internal")
    int_m = metrics(int_pairs, THRESHOLD)

    print(f"  External holdout...")
    ext_pairs = run_files(ext_p, ext_l, interp, inp_d, out_d, "external")
    ext_m = metrics(ext_pairs, THRESHOLD)

    print(f"\n  --- Internal test (threshold={THRESHOLD}) ---")
    print(f"  TP={int_m['tp']} FP={int_m['fp']} FN={int_m['fn']} TN={int_m['tn']}")
    print(f"  Acc={int_m['accuracy']*100:.2f}%  Recall={int_m['recall']*100:.2f}%  F1={int_m['f1']*100:.2f}%")

    print(f"\n  --- External holdout (threshold={THRESHOLD}) ---")
    print(f"  TP={ext_m['tp']} FP={ext_m['fp']} FN={ext_m['fn']} TN={ext_m['tn']}")
    print(f"  Acc={ext_m['accuracy']*100:.2f}%  Recall={ext_m['recall']*100:.2f}%")
    print(f"  Precision={ext_m['precision']*100:.2f}%  F1={ext_m['f1']*100:.2f}%")
    print(f"  FAR={ext_m['far']*100:.2f}%  FRR={ext_m['frr']*100:.2f}%")

    all_results[name] = {
        "tflite_path": tflite_path,
        "md5": md5,
        "size_kb": round(size_kb, 1),
        "threshold": THRESHOLD,
        "internal_test": int_m,
        "external_holdout": ext_m,
    }

# ── Summary table ────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print("BẢNG TỔNG HỢP — 3 MODEL (threshold=0.25, external holdout 1.700)")
print(f"{'='*60}")
print(f"{'Model':30s} {'Acc':>7} {'Recall':>7} {'F1':>7} {'FAR':>7} {'FRR':>7}")
print("-"*60)
for name, r in all_results.items():
    e = r['external_holdout']
    short = name.replace('_attention_lite','').replace('_resnet','')
    print(f"{short:30s} {e['accuracy']*100:>6.2f}% {e['recall']*100:>6.2f}% "
          f"{e['f1']*100:>6.2f}% {e['far']*100:>6.2f}% {e['frr']*100:>6.2f}%")

print(f"\n{'='*60}")
print("INTERNAL TEST (threshold=0.25)")
print(f"{'='*60}")
print(f"{'Model':30s} {'Acc':>7} {'Recall':>7} {'F1':>7}")
print("-"*60)
for name, r in all_results.items():
    i = r['internal_test']
    short = name.replace('_attention_lite','').replace('_resnet','')
    print(f"{short:30s} {i['accuracy']*100:>6.2f}% {i['recall']*100:>6.2f}% {i['f1']*100:>6.2f}%")

with open(OUT_JSON, "w") as f:
    json.dump({"threshold": THRESHOLD, "models": all_results}, f, indent=2)
print(f"\n[OK] Saved: {OUT_JSON}")

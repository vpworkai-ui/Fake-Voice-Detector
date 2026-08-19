#!/usr/bin/env python3
"""
Bước 1: Trích xuất và lưu cache 21 đặc trưng ra file .npy
Chạy một lần duy nhất — train_spoof_model_v2.py đọc từ cache.

Chạy:
  python ml/extract_features_v2.py
"""
from __future__ import annotations
import argparse, math, wave, json, random
from pathlib import Path
import numpy as np
from multiprocessing import Pool, cpu_count

TARGET_SR       = 16000
PRE_EMPHASIS    = 0.97
FRAME_LENGTH    = 512
HOP_LENGTH      = 160
NUM_MEL_FILTERS = 26
NUM_MFCC        = 13
MEL_LOW_HZ      = 80.0
MEL_HIGH_HZ     = 7600.0
FEATURE_SIZE    = 21

FEATURE_NAMES = [
    "rms","mean_abs","zcr","peak","crest_factor","clipping_ratio",
    "dynamic_range","active_duration_sec",
    *[f"mfcc_{i}" for i in range(NUM_MFCC)],
]

def load_wav(path):
    with wave.open(str(path), "rb") as wf:
        ch=wf.getnchannels(); sw=wf.getsampwidth(); sr=wf.getframerate()
        frames=wf.readframes(wf.getnframes())
    if sw!=2: raise ValueError
    audio=np.frombuffer(frames,dtype=np.int16).astype(np.float32)
    if ch>1: audio=audio.reshape(-1,ch).mean(axis=1)
    audio=audio/32767.0
    if sr!=TARGET_SR:
        n=max(1,int(round(len(audio)/sr*TARGET_SR)))
        audio=np.interp(np.linspace(0,len(audio)-1,n),np.linspace(0,len(audio)-1,len(audio)),audio).astype(np.float32)
    return audio

def _build_mel(sr):
    fft=1<<math.ceil(math.log2(FRAME_LENGTH)); nb=fft//2+1
    lo=2595*np.log10(1+MEL_LOW_HZ/700); hi=2595*np.log10(1+min(MEL_HIGH_HZ,sr/2)/700)
    pts=700*(10**np.linspace(lo,hi,NUM_MEL_FILTERS+2)/2595)-700
    bins=np.floor((fft+1)*pts/sr).astype(int)
    fb=np.zeros((NUM_MEL_FILTERS,nb))
    for f in range(NUM_MEL_FILTERS):
        for k in range(bins[f],bins[f+2]+1):
            if k>=nb: break
            if k<=bins[f+1]: fb[f,k]=(k-bins[f])/(bins[f+1]-bins[f]+1e-10)
            else:             fb[f,k]=(bins[f+2]-k)/(bins[f+2]-bins[f+1]+1e-10)
    return fb

_MEL=None
def _get_mel():
    global _MEL
    if _MEL is None: _MEL=_build_mel(TARGET_SR)
    return _MEL

def mfcc_mean(signal):
    if len(signal)<FRAME_LENGTH: return np.zeros(NUM_MFCC,np.float32)
    emph=np.concatenate([[signal[0]],signal[1:]-PRE_EMPHASIS*signal[:-1]])
    fft=1<<math.ceil(math.log2(FRAME_LENGTH)); nb=fft//2+1
    win=0.54-0.46*np.cos(2*np.pi*np.arange(FRAME_LENGTH)/(FRAME_LENGTH-1))
    fb=_get_mel(); acc=np.zeros(NUM_MFCC); n=0; i=0
    while i+FRAME_LENGTH<=len(emph):
        frame=np.zeros(fft); frame[:FRAME_LENGTH]=emph[i:i+FRAME_LENGTH]*win
        ps=np.abs(np.fft.rfft(frame)[:nb])**2
        lm=np.log(fb@ps+1e-10)
        for m in range(NUM_MFCC):
            acc[m]+=np.sum(lm*np.cos(np.pi*m*(np.arange(NUM_MEL_FILTERS)+.5)/NUM_MEL_FILTERS))
        n+=1; i+=HOP_LENGTH
    return (acc/max(n,1)).astype(np.float32)

def extract(signal):
    if signal.size==0: return np.zeros(FEATURE_SIZE,np.float32)
    rms=float(np.sqrt(np.mean(signal**2)))
    mabs=float(np.mean(np.abs(signal)))
    s=np.signbit(signal)
    zcr=float(np.mean(s[1:]!=s[:-1])) if len(signal)>1 else 0.
    peak=float(np.max(np.abs(signal)))
    crest=float(np.clip(peak/(rms+1e-8),0,10))
    clip=float(np.mean(np.abs(signal)>0.98))
    dyn=float(max(signal.max()-signal.min(),0))
    dur=float(len(signal)/TARGET_SR)
    mfcc=mfcc_mean(signal)
    return np.array([rms,mabs,zcr,peak,crest,clip,dyn,dur,*mfcc],np.float32)

def process_file(args):
    path, label = args
    try:
        sig=load_wav(Path(path))
        return extract(sig), label
    except Exception:
        return None, label

def main():
    pa=argparse.ArgumentParser()
    pa.add_argument("--dataset-root",  default="data/dataset_samples",         type=Path)
    pa.add_argument("--external-root", default="data/external_vietnamese_test", type=Path)
    pa.add_argument("--output-dir",    default="ml/artifacts/v2",               type=Path)
    pa.add_argument("--workers",       default=max(1,cpu_count()-1), type=int)
    args=pa.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    def collect(root, limit=0, seed=42):
        rng=random.Random(seed); paths=[]; labels=[]
        for ln,lb in(("bonafide",0),("spoof",1)):
            d=root/ln
            if not d.exists(): continue
            files=sorted(str(p) for p in d.rglob("*.wav"))
            if limit: rng.shuffle(files); files=files[:limit]
            paths+=files; labels+=[lb]*len(files)
        return paths,labels

    print(f"Workers: {args.workers}")

    for name, root, limit in [
        ("internal", args.dataset_root, 0),
        ("external", args.external_root, 0),
    ]:
        if not root.exists(): continue
        out=args.output_dir/f"features_{name}.npz"
        if out.exists():
            print(f"  Cache hit: {out}"); continue
        paths,labels=collect(root,limit)
        print(f"Extracting {name}: {len(paths)} files on {args.workers} workers...")
        with Pool(args.workers) as pool:
            results=list(pool.imap(process_file,zip(paths,labels),chunksize=32))
        feats=[r[0] for r in results if r[0] is not None]
        lbls =[r[1] for r in results if r[0] is not None]
        failed=sum(1 for r in results if r[0] is None)
        X=np.stack(feats).astype(np.float32); y=np.array(lbls,np.float32)
        np.savez(out, X=X, y=y, paths=np.array(paths), feature_names=FEATURE_NAMES)
        print(f"  Saved {X.shape} → {out}  (failed={failed})")

    print("\nDone! Run: python ml/train_spoof_model_v2.py --from-cache")

if __name__=="__main__":
    main()

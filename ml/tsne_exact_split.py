"""
t-SNE visualization dùng ĐÚNG dữ liệu đã đánh giá trong báo cáo:
  - Internal test set : 4.968 mẫu (seed=42, test_size=20%) - tập đã tính 99,32%
  - External holdout  : 1.700 mẫu (seed=42, bỏ 150/lớp đã mix) - tập đã tính 85,29%
  - Tổng              : 6.668 mẫu
Không rút gọn, không dùng random khác.
"""

import os, random, warnings
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings('ignore')

BASE     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INT_ROOT = os.path.join(BASE, 'data', 'dataset_samples')
EXT_ROOT = os.path.join(BASE, 'data', 'external_vietnamese_test')
OUT_DIR  = os.path.join(BASE, 'ml', 'artifacts', 'tsne')
SEED     = 42
MIX_PER_CLASS = 150
SR       = 16000
MAX_SAMPLES = 4 * SR  # 4 giây

os.makedirs(OUT_DIR, exist_ok=True)


# ── Feature extraction (8 acoustic features, giống TFLiteSpoofDetectorEngine) ──
def load_wav(path):
    try:
        import soundfile as sf
        audio, sr = sf.read(path, dtype='int16')
        if len(audio.shape) > 1: audio = audio[:, 0]
        if sr != SR:
            ratio = SR / sr
            n = int(len(audio) * ratio)
            audio = np.interp(np.linspace(0, len(audio)-1, n),
                              np.arange(len(audio)), audio.astype(np.float32)).astype(np.int16)
        return audio[:MAX_SAMPLES]
    except:
        return None

def extract_features(pcm):
    if pcm is None or len(pcm) < 160: return None
    a = pcm.astype(np.float32) / 32768.0
    n = len(a)
    rms         = float(np.sqrt(np.mean(a**2)))
    mean_abs    = float(np.mean(np.abs(a)))
    zcr         = float(np.sum(np.diff(np.sign(a)) != 0) / n)
    peak        = float(np.max(np.abs(a)))
    crest       = float(peak / rms) if rms > 1e-9 else 0.0
    clip_ratio  = float(np.sum(np.abs(a) > 0.99) / n)
    dyn_range   = float(20*np.log10(peak+1e-9) - 20*np.log10(rms+1e-9))
    # Active duration
    frame_sz = int(SR * 0.02); hop = frame_sz // 2
    energies = [np.mean(np.abs(a[i:i+frame_sz])) for i in range(0, n-frame_sz, hop)]
    if energies:
        noise = sorted(energies)[int(len(energies)*0.2)]
        thr   = max(0.005, noise * 1.5)
        act_dur = float(sum(1 for e in energies if e >= thr) * hop / SR)
    else:
        act_dur = float(n / SR)
    return np.array([rms, mean_abs, zcr, peak, crest, clip_ratio, dyn_range, act_dur], dtype=np.float32)


# ── Tái tạo đúng internal test split (seed=42) ──────────────────────────────
def get_internal_test():
    rng = random.Random(SEED)
    paths, labels = [], []
    for li, sub in enumerate(['bonafide', 'spoof']):
        d = Path(INT_ROOT) / sub
        if not d.exists(): continue
        files = sorted(str(f) for f in d.iterdir() if f.suffix == '.wav')
        rng.shuffle(files)
        paths += files; labels += [li] * len(files)

    _, te_p, _, te_l = train_test_split(paths, labels, test_size=0.2, stratify=labels, random_state=SEED)
    return te_p, te_l


# ── Tái tạo đúng external holdout (seed=42, bỏ 150/lớp đã mix) ──────────────
def get_external_holdout():
    rng = random.Random(SEED)
    by_class = {0: [], 1: []}
    for li, sub in enumerate(['bonafide', 'spoof']):
        d = Path(EXT_ROOT) / sub
        if not d.exists(): continue
        files = sorted(str(f) for f in d.iterdir() if f.suffix == '.wav')
        rng.shuffle(files)
        by_class[li] = files

    holdout_paths, holdout_labels = [], []
    for label, files in by_class.items():
        holdout_paths.extend(files[MIX_PER_CLASS:])
        holdout_labels.extend([label] * (len(files) - MIX_PER_CLASS))
    return holdout_paths, holdout_labels


# ── Load features ────────────────────────────────────────────────────────────
def load_features(paths, labels, source_name):
    X, y, sources = [], [], []
    failed = 0
    for i, (p, l) in enumerate(zip(paths, labels)):
        if (i+1) % 500 == 0:
            print(f'  {source_name}: {i+1}/{len(paths)}...', flush=True)
        feat = extract_features(load_wav(p))
        if feat is None: failed += 1; continue
        X.append(feat); y.append(l); sources.append(source_name)
    print(f'  {source_name}: {len(X)} OK, {failed} failed')
    return X, y, sources


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    print('=' * 60)
    print('t-SNE — Đúng dữ liệu báo cáo (seed=42, không rút gọn)')
    print('=' * 60)

    print('\n[1] Tái tạo internal test split...')
    int_paths, int_labels = get_internal_test()
    print(f'    Internal test: {len(int_paths)} files '
          f'(bonafide={int_labels.count(0)}, spoof={int_labels.count(1)})')

    print('\n[2] Tái tạo external holdout...')
    ext_paths, ext_labels = get_external_holdout()
    print(f'    External holdout: {len(ext_paths)} files '
          f'(bonafide={ext_labels.count(0)}, spoof={ext_labels.count(1)})')

    print(f'\n[3] Trích xuất 8 đặc trưng...')
    Xi, yi, si = load_features(int_paths, int_labels, 'internal')
    Xe, ye, se = load_features(ext_paths, ext_labels, 'external')

    X = np.array(Xi + Xe)
    y = np.array(yi + ye)
    sources = si + se

    total = len(X)
    n_int = len(Xi); n_ext = len(Xe)
    print(f'\n    Tổng: {total} mẫu (internal={n_int}, external={n_ext})')

    print('\n[4] Chuẩn hoá và chạy t-SNE...')
    X_scaled = StandardScaler().fit_transform(X)
    tsne = TSNE(n_components=2, perplexity=40, max_iter=1000,
                init='pca', learning_rate='auto', random_state=SEED)
    X_2d = tsne.fit_transform(X_scaled)
    print('    t-SNE xong.')

    # ── Màu & marker ─────────────────────────────────────────────────────────
    LABEL_COLOR  = {0: '#2196F3', 1: '#F44336'}   # xanh=bonafide, đỏ=spoof
    LABEL_NAME   = {0: 'Bonafide (thật)', 1: 'Spoof (giả)'}
    SOURCE_MARKER= {'internal': 'o', 'external': '^'}
    SOURCE_COLOR = {'internal': '#4CAF50', 'external': '#FF9800'}
    SOURCE_NAME  = {'internal': f'Nội bộ ({n_int})', 'external': f'Ngoài ({n_ext})'}

    plt.rcParams.update({'font.size': 10, 'figure.dpi': 150, 'savefig.dpi': 150})

    # ── Fig 1: Nhãn (bonafide vs spoof) ──────────────────────────────────────
    fig, ax = plt.subplots(figsize=(8, 6))
    for src in ['internal', 'external']:
        for lbl in [0, 1]:
            mask = [(s == src and yy == lbl) for s, yy in zip(sources, y)]
            pts  = X_2d[mask]
            if len(pts) == 0: continue
            ax.scatter(pts[:,0], pts[:,1], c=LABEL_COLOR[lbl],
                       marker=SOURCE_MARKER[src], s=8, alpha=0.5, linewidths=0)

    # Legend
    import matplotlib.patches as mpatches, matplotlib.lines as mlines
    handles = [
        mpatches.Patch(color=LABEL_COLOR[0], label=LABEL_NAME[0]),
        mpatches.Patch(color=LABEL_COLOR[1], label=LABEL_NAME[1]),
        mlines.Line2D([],[],marker='o',color='gray',ls='',ms=6,label=SOURCE_NAME['internal']),
        mlines.Line2D([],[],marker='^',color='gray',ls='',ms=6,label=SOURCE_NAME['external']),
    ]
    ax.legend(handles=handles, fontsize=9, loc='upper right')
    ax.set_title(f't-SNE theo nhãn — {total} mẫu\n'
                 f'(Internal test {n_int} + External holdout {n_ext}, seed=42)',
                 fontsize=11)
    ax.set_xlabel('t-SNE 1'); ax.set_ylabel('t-SNE 2')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    out1 = os.path.join(OUT_DIR, 'tsne_label.png')
    fig.savefig(out1, bbox_inches='tight'); plt.close(fig)
    print(f'    Saved: {out1}')

    # ── Fig 2: Nguồn (internal vs external) ──────────────────────────────────
    fig, ax = plt.subplots(figsize=(8, 6))
    for src in ['internal', 'external']:
        mask = [s == src for s in sources]
        pts  = X_2d[mask]
        ax.scatter(pts[:,0], pts[:,1], c=SOURCE_COLOR[src],
                   marker=SOURCE_MARKER[src], s=8, alpha=0.5,
                   label=SOURCE_NAME[src], linewidths=0)
    ax.legend(fontsize=9); ax.set_title(
        f't-SNE theo nguồn — Domain shift\n'
        f'(Internal test {n_int} + External holdout {n_ext}, seed=42)', fontsize=11)
    ax.set_xlabel('t-SNE 1'); ax.set_ylabel('t-SNE 2')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    out2 = os.path.join(OUT_DIR, 'tsne_source.png')
    fig.savefig(out2, bbox_inches='tight'); plt.close(fig)
    print(f'    Saved: {out2}')

    # ── Fig 3: Combined 2x2 ───────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    for ax, (color_by, title) in zip(axes, [
        ('label',  f't-SNE theo nhãn: Bonafide vs Spoof'),
        ('source', f't-SNE theo nguồn: Nội bộ vs Ngoài nguồn'),
    ]):
        for src in ['internal', 'external']:
            for lbl in [0, 1]:
                mask = [(s == src and yy == lbl) for s, yy in zip(sources, y)]
                pts  = X_2d[mask]
                if len(pts) == 0: continue
                color = LABEL_COLOR[lbl] if color_by == 'label' else SOURCE_COLOR[src]
                ax.scatter(pts[:,0], pts[:,1], c=color, marker=SOURCE_MARKER[src],
                           s=6, alpha=0.45, linewidths=0)
        ax.set_title(title, fontsize=10)
        ax.set_xlabel('t-SNE 1'); ax.set_ylabel('t-SNE 2')
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

    # Legend combined
    handles = [
        mpatches.Patch(color=LABEL_COLOR[0], label='Bonafide'),
        mpatches.Patch(color=LABEL_COLOR[1], label='Spoof'),
        mpatches.Patch(color=SOURCE_COLOR['internal'], label=SOURCE_NAME['internal']),
        mpatches.Patch(color=SOURCE_COLOR['external'], label=SOURCE_NAME['external']),
        mlines.Line2D([],[],marker='o',color='gray',ls='',ms=5,label='Nội bộ (tròn)'),
        mlines.Line2D([],[],marker='^',color='gray',ls='',ms=5,label='Ngoài (tam giác)'),
    ]
    fig.legend(handles=handles, loc='lower center', ncol=3, fontsize=9,
               bbox_to_anchor=(0.5, -0.02))
    fig.suptitle(
        f't-SNE Visualization — {total} mẫu đúng với báo cáo\n'
        f'Internal test set: {n_int} | External holdout: {n_ext} | seed={SEED}',
        fontsize=12)
    plt.tight_layout(rect=[0,0.06,1,1])
    out3 = os.path.join(OUT_DIR, 'tsne_combined.png')
    fig.savefig(out3, bbox_inches='tight'); plt.close(fig)
    print(f'    Saved: {out3}')

    print('\nDone. Cập nhật báo cáo với số liệu đúng:')
    print(f'  t-SNE trên {total} mẫu (internal test={n_int}, external holdout={n_ext})')


if __name__ == '__main__':
    main()

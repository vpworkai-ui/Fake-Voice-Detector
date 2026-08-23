from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np
from PIL import Image


ROOT = Path('/Users/phucit/Desktop/Work/Apps/Flutter/Projects/fake_voice_detector/docs/overleaf/springer_progress_report/figures')


def savefig(fig, name, dpi=220):
    fig.savefig(ROOT / name, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close(fig)


def fig_ablation():
    labels = ['ActiveDuration', 'ZCR', 'MeanAbs', 'Peak', 'CrestFactor', 'ClippingRatio', 'RMS', 'DynamicRange']
    values = np.array([0.4806, 0.2258, 0.1612, 0.1363, 0.0613, 0.0351, 0.0218, -0.0218])
    colors = np.where(values >= 0, '#ef3b37', '#148f82')

    fig, ax = plt.subplots(figsize=(13.4, 5.8))
    y = np.arange(len(labels))
    bars = ax.barh(y, values, color=colors, height=0.56)
    ax.axvline(0, color='#2f2f2f', linewidth=1.2)
    ax.set_yticks(y, labels)
    ax.set_xlim(-0.06, 0.56)
    ax.set_xlabel('F1 change (%) after removing a feature (positive = more important)')
    ax.set_title('Ablation Study - 8 Features | Baseline F1 = 98.25%\n(2-layer DNN, internal test 4,968 samples, seed = 42)', pad=12)
    ax.grid(axis='x', linestyle='--', alpha=0.28)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(axis='y', pad=4)
    fig.subplots_adjust(left=0.21, right=0.98, bottom=0.22, top=0.86)

    for bar, value in zip(bars, values):
        y_text = bar.get_y() + bar.get_height() / 2
        if value >= 0:
            ax.text(value + 0.004, y_text, f'+{value:.4f}%', va='center', ha='left', fontsize=10)
        else:
            ax.text(-0.028, y_text, f'{value:.4f}%', va='center', ha='right', fontsize=10, color='black')

    legend_handles = [
        Patch(facecolor='#ef3b37', label='F1 drop (useful feature)'),
        Patch(facecolor='#148f82', label='Small F1 gain (minor redundancy)'),
    ]
    ax.legend(handles=legend_handles, loc='upper center', bbox_to_anchor=(0.5, -0.12), ncol=2, frameon=False)
    savefig(fig, 'image1_clean.png')


def fig_model_comparison():
    models = ['Cross-Scale\nAttention Lite ★', 'AASIST Lite', 'CBAM ResNet Lite']
    accuracy = [84.71, 69.12, 84.47]
    recall = [95.29, 51.76, 93.06]
    f1 = [86.17, 62.63, 85.70]
    far = [25.88, 13.53, 24.12]

    fig, ax = plt.subplots(figsize=(11.6, 6.4))
    x = np.arange(len(models))
    width = 0.2
    series = [
        ('Accuracy (%)', accuracy, '#2f9b92'),
        ('Recall (%)', recall, '#4a90d6'),
        ('F1 (%)', f1, '#9a47b7'),
        ('FAR (%)', far, '#eb554f'),
    ]
    for idx, (label, values, color) in enumerate(series):
        bars = ax.bar(x + (idx - 1.5) * width, values, width=width, label=label, color=color, edgecolor='white')
        for bar, value in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, value + 1.0, f'{value:.1f}', ha='center', va='bottom', fontsize=10, fontweight='bold')

    ax.axhline(80, color='#8aa5ba', linestyle='--', linewidth=1.1, alpha=0.55)
    ax.text(len(models) - 0.05, 80.8, '80% baseline', ha='right', va='bottom', color='#8aa5ba', fontsize=10)
    ax.set_ylim(0, 105)
    ax.set_ylabel('Metric (%)')
    ax.set_xticks(x, models)
    ax.set_title('Three-Model Comparison - External Holdout (1,700 samples, Threshold = 0.25)\n(Direct TFLite inference results)', pad=12)
    ax.grid(axis='y', linestyle='--', alpha=0.25)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.legend(loc='lower right', frameon=True, fancybox=True, framealpha=0.93)
    savefig(fig, 'image10_clean.png')


def fig_confusion_matrix():
    matrix = np.array([[630, 220], [40, 810]])
    fig, ax = plt.subplots(figsize=(6.6, 6.1))
    im = ax.imshow(matrix, cmap='Blues', vmin=0, vmax=900)

    labels = [['TN', 'FP'], ['FN', 'TP']]
    for i in range(2):
        for j in range(2):
            value = matrix[i, j]
            color = 'white' if value >= 500 else 'black'
            ax.text(j, i, f'{labels[i][j]}\n{value}', ha='center', va='center', fontsize=18, fontweight='bold', color=color)

    ax.set_xticks([0, 1], ['Predicted\nBONAFIDE', 'Predicted\nSPOOF'])
    ax.set_yticks([0, 1], ['Actual\nBONAFIDE', 'Actual\nSPOOF'])
    ax.set_title('Confusion Matrix - Cross-Scale\n(External holdout: 1,700 samples, threshold = 0.25)', pad=12)
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_ticks(np.arange(0, 901, 100))

    metrics = 'Accuracy = 84.71%   Recall = 95.29%   F1 = 86.17%   FAR = 25.88%   FRR = 4.71%'
    fig.text(0.5, 0.035, metrics, ha='center', va='center', fontsize=10, color='#555555')
    savefig(fig, 'image9_clean.png')


def _extract_points(image_name, color_ranges, crop):
    arr = np.array(Image.open(ROOT / image_name).convert('RGB'))
    x0, y0, x1, y1 = crop
    crop_arr = arr[y0:y1, x0:x1]
    result = {}
    for key, (lower, upper) in color_ranges.items():
        lower = np.array(lower)
        upper = np.array(upper)
        mask = np.all(crop_arr >= lower, axis=2) & np.all(crop_arr <= upper, axis=2)
        ys, xs = np.where(mask)
        if len(xs) == 0:
            result[key] = np.empty((0, 2))
            continue
        # Reduce dense raster markers into cleaner point clouds by rounding to a coarse grid.
        pts = np.column_stack((xs, ys)).astype(float)
        pts[:, 0] = np.round(pts[:, 0] / 2.2) * 2.2
        pts[:, 1] = np.round(pts[:, 1] / 2.2) * 2.2
        pts = np.unique(pts, axis=0)
        width = x1 - x0
        height = y1 - y0
        x_vals = -70 + pts[:, 0] / width * 155
        y_vals = 75 - pts[:, 1] / height * 135
        result[key] = np.column_stack((x_vals, y_vals))
    return result


def fig_tsne_label():
    crop = (96, 70, 990, 764)
    ranges = {
        'bonafide': ((35, 140, 225), (125, 205, 255)),
        'spoof': ((235, 70, 70), (255, 185, 185)),
    }
    points = _extract_points('image11.png', ranges, crop)

    fig, ax = plt.subplots(figsize=(8.2, 6.6))
    ax.scatter(points['bonafide'][:, 0], points['bonafide'][:, 1], s=9, c='#3aa0f3', alpha=0.62, edgecolors='none', label='Bonafide (real)')
    ax.scatter(points['spoof'][:, 0], points['spoof'][:, 1], s=9, c='#ff5b52', alpha=0.62, edgecolors='none', label='Spoof (fake)')
    ax.set_xlim(-70, 87)
    ax.set_ylim(-58, 76)
    ax.set_xlabel('t-SNE 1')
    ax.set_ylabel('t-SNE 2')
    ax.set_title('t-SNE by label - 6,668 samples\n(Internal test 4,968 + External holdout 1,700, seed = 42)', pad=10)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    handles = [
        Patch(facecolor='#3aa0f3', label='Bonafide (real)'),
        Patch(facecolor='#ff5b52', label='Spoof (fake)'),
        Line2D([0], [0], marker='o', color='gray', linestyle='None', markersize=8, label='Internal (4,968)'),
        Line2D([0], [0], marker='^', color='gray', linestyle='None', markersize=8, label='External (1,700)'),
    ]
    ax.legend(handles=handles, loc='upper right', frameon=True, framealpha=0.95)
    savefig(fig, 'image11_clean.png')


def fig_tsne_source():
    crop = (96, 70, 990, 766)
    ranges = {
        'internal': ((90, 180, 90), (175, 235, 170)),
        'external': ((245, 160, 45), (255, 210, 120)),
    }
    points = _extract_points('image12.png', ranges, crop)

    fig, ax = plt.subplots(figsize=(8.2, 6.6))
    ax.scatter(points['internal'][:, 0], points['internal'][:, 1], s=9, c='#69c56d', alpha=0.62, edgecolors='none', label='Internal (4,968)')
    ax.scatter(points['external'][:, 0], points['external'][:, 1], s=14, c='#ffb23b', alpha=0.82, edgecolors='none', marker='^', label='External (1,700)')
    ax.set_xlim(-70, 87)
    ax.set_ylim(-58, 76)
    ax.set_xlabel('t-SNE 1')
    ax.set_ylabel('t-SNE 2')
    ax.set_title('t-SNE by source - Domain shift\n(Internal test 4,968 + External holdout 1,700, seed = 42)', pad=10)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.legend(loc='upper right', frameon=True, framealpha=0.95)
    savefig(fig, 'image12_clean.png')


if __name__ == '__main__':
    plt.rcParams.update({
        'font.size': 11,
        'axes.titlesize': 14.5,
        'axes.labelsize': 12,
        'xtick.labelsize': 11,
        'ytick.labelsize': 11,
        'legend.fontsize': 10,
        'figure.facecolor': 'white',
        'axes.facecolor': 'white',
        'font.family': 'DejaVu Sans',
    })
    fig_ablation()
    fig_model_comparison()
    fig_confusion_matrix()
    fig_tsne_label()
    fig_tsne_source()
    print('clean charts regenerated')

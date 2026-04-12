"""Generate thesis figures: DNN architecture, Android architecture, UI mockups."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as pe
import numpy as np
import os

OUT = os.path.join(os.path.dirname(__file__), 'charts')
os.makedirs(OUT, exist_ok=True)

# ─── Colour palette ──────────────────────────────────────────
C_NAVY   = '#1a2744'
C_TEAL   = '#0b8fac'
C_BLUE   = '#2e4f8a'
C_GREEN  = '#27ae60'
C_RED    = '#e74c3c'
C_ORANGE = '#e67e22'
C_GRAY   = '#95a5a6'
C_LIGHT  = '#ecf0f1'
C_WHITE  = '#ffffff'
C_DARK   = '#2c3e50'
C_PURPLE = '#8e44ad'

# ════════════════════════════════════════════════════════════
# FIGURE 2.1 — DNN Architecture
# ════════════════════════════════════════════════════════════
def draw_dnn_architecture():
    fig, ax = plt.subplots(figsize=(14, 7))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 7)
    ax.axis('off')
    fig.patch.set_facecolor(C_WHITE)

    # --- layer definitions ---
    layers = [
        {'x': 1.1, 'label': 'Input\nLayer', 'n': 8,   'color': C_BLUE,   'sublabel': '8 đặc trưng\nâm thanh'},
        {'x': 4.2, 'label': 'Dense\n(64, ReLU)', 'n': 6, 'color': C_TEAL, 'sublabel': '64 neurons\n576 params'},
        {'x': 7.0, 'label': 'Dropout\n(0.2)',    'n': 5, 'color': C_ORANGE,'sublabel': 'rate=0.2\ntraining only'},
        {'x': 9.8, 'label': 'Dense\n(32, ReLU)', 'n': 4, 'color': C_TEAL, 'sublabel': '32 neurons\n2.080 params'},
        {'x': 12.9,'label': 'Output\n(Sigmoid)', 'n': 1, 'color': C_GREEN, 'sublabel': 'Spoof\nProbability'},
    ]

    node_radius = 0.22
    node_xs = []
    node_ys_list = []

    for layer in layers:
        n = layer['n']
        cx = layer['x']
        ys = np.linspace(1.0, 6.0, n)
        node_xs.append(cx)
        node_ys_list.append(ys)

        # draw nodes
        for y in ys:
            circle = plt.Circle((cx, y), node_radius,
                                 color=layer['color'], zorder=4, linewidth=1.5,
                                 ec=C_WHITE, alpha=0.92)
            ax.add_patch(circle)

        # layer label above
        ax.text(cx, 6.65, layer['label'], ha='center', va='bottom',
                fontsize=10, fontweight='bold', color=C_DARK,
                bbox=dict(boxstyle='round,pad=0.3', facecolor=layer['color'],
                          edgecolor='none', alpha=0.15))
        # sublabel below
        ax.text(cx, 0.5, layer['sublabel'], ha='center', va='top',
                fontsize=8.5, color='#555555', linespacing=1.4)

    # draw connections between adjacent layers
    for i in range(len(layers) - 1):
        xs_a, ys_a = node_xs[i],   node_ys_list[i]
        xs_b, ys_b = node_xs[i+1], node_ys_list[i+1]
        for ya in ys_a:
            for yb in ys_b:
                ax.plot([xs_a + node_radius, xs_b - node_radius],
                        [ya, yb], color=C_GRAY, lw=0.5, alpha=0.35, zorder=2)

    # arrows between layer groups
    arrow_pairs = [(0,1),(1,2),(2,3),(3,4)]
    for a, b in arrow_pairs:
        xa = node_xs[a] + node_radius
        xb = node_xs[b] - node_radius
        ax.annotate('', xy=(xb, 3.5), xytext=(xa, 3.5),
                    arrowprops=dict(arrowstyle='->', color=C_DARK,
                                   lw=1.5, mutation_scale=14))

    # feature labels on input layer
    features = ['RMS','MeanAbs','ZCR','Peak','Crest','Clip','DynRange','Duration']
    ys_in = node_ys_list[0]
    for feat, y in zip(features, ys_in):
        ax.text(node_xs[0] - node_radius - 0.12, y, feat,
                ha='right', va='center', fontsize=8, color=C_BLUE, fontweight='bold')

    # output label
    ax.text(node_xs[-1] + node_radius + 0.15, node_ys_list[-1][0],
            'P(spoof)\n∈ [0,1]', ha='left', va='center', fontsize=8.5, color=C_GREEN)

    # title
    ax.text(7, 7.1, 'Kiến trúc mô hình DNN phát hiện giả mạo giọng nói',
            ha='center', va='center', fontsize=13, fontweight='bold', color=C_DARK)

    # param summary box
    summary = 'Tổng tham số: 2.689  |  Kích thước TFLite: 12 KB  |  Inference: < 3 ms'
    ax.text(7, -0.15, summary, ha='center', va='top', fontsize=9,
            color=C_WHITE,
            bbox=dict(boxstyle='round,pad=0.4', facecolor=C_NAVY, edgecolor='none'))

    fig.tight_layout(pad=0.3)
    out = os.path.join(OUT, 'fig_dnn_architecture.png')
    fig.savefig(out, dpi=150, bbox_inches='tight', facecolor=C_WHITE)
    plt.close(fig)
    print(f'Saved: {out}')


# ════════════════════════════════════════════════════════════
# FIGURE 3.1 — Android Clean Architecture
# ════════════════════════════════════════════════════════════
def draw_android_architecture():
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8)
    ax.axis('off')
    fig.patch.set_facecolor(C_WHITE)

    def box(ax, x, y, w, h, color, alpha=0.15, ec=None, lw=1.5, radius=0.25):
        b = FancyBboxPatch((x, y), w, h,
                           boxstyle=f'round,pad={radius}',
                           facecolor=color, edgecolor=ec or color,
                           linewidth=lw, alpha=alpha, zorder=2)
        ax.add_patch(b)

    def solid_box(ax, x, y, w, h, color, ec='white', lw=1.2, radius=0.2, alpha=1.0, zorder=3):
        b = FancyBboxPatch((x, y), w, h,
                           boxstyle=f'round,pad={radius}',
                           facecolor=color, edgecolor=ec,
                           linewidth=lw, alpha=alpha, zorder=zorder)
        ax.add_patch(b)

    def label(ax, x, y, text, size=9, color=C_WHITE, bold=False, ha='center', va='center'):
        ax.text(x, y, text, ha=ha, va=va, fontsize=size,
                fontweight='bold' if bold else 'normal', color=color, zorder=5,
                linespacing=1.4)

    def arrow(ax, x1, y1, x2, y2, color=C_DARK, lw=1.5):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', color=color,
                                   lw=lw, mutation_scale=14), zorder=6)

    # ── Layer backgrounds ──────────────────────────────────
    # Presentation (top)
    box(ax, 0.3, 5.6, 13.4, 2.0, C_TEAL,  alpha=0.12, ec=C_TEAL,  lw=2)
    label(ax, 0.85, 7.1, 'PRESENTATION\nLAYER', size=9, color=C_TEAL, bold=True, ha='center')

    # Domain (middle)
    box(ax, 0.3, 3.1, 13.4, 2.1, C_BLUE,  alpha=0.12, ec=C_BLUE,  lw=2)
    label(ax, 0.85, 4.65, 'DOMAIN\nLAYER',       size=9, color=C_BLUE,  bold=True, ha='center')

    # Data (bottom)
    box(ax, 0.3, 0.4, 13.4, 2.3, C_NAVY,  alpha=0.12, ec=C_NAVY,  lw=2)
    label(ax, 0.85, 1.5,  'DATA\nLAYER',          size=9, color=C_NAVY,  bold=True, ha='center')

    # ── Presentation components ────────────────────────────
    # ViewModel
    solid_box(ax, 1.8, 6.0, 2.8, 1.3, C_TEAL, alpha=0.9)
    label(ax, 3.2, 6.95, 'VoiceDetectorViewModel', size=8.5, bold=True)
    label(ax, 3.2, 6.5,  'StateFlow<DetectorUiState>', size=7.5)
    label(ax, 3.2, 6.1,  'MVI pattern • Coroutines', size=7.5)

    # Compose UI
    solid_box(ax, 5.2, 6.0, 3.6, 1.3, C_TEAL, alpha=0.9)
    label(ax, 7.0, 6.95, 'VoiceDetectorScreen', size=8.5, bold=True)
    label(ax, 7.0, 6.5,  'Tab 1: Phát hiện  |  Tab 2: Lịch sử', size=7.5)
    label(ax, 7.0, 6.1,  'Tab 3: Cài đặt  — Jetpack Compose M3', size=7.5)

    # MainActivity
    solid_box(ax, 9.4, 6.0, 3.7, 1.3, C_TEAL, alpha=0.9)
    label(ax, 11.25, 6.95, 'MainActivity', size=8.5, bold=True)
    label(ax, 11.25, 6.5,  'ViewModelFactory • DI manual', size=7.5)
    label(ax, 11.25, 6.1,  'onExportCsv • edge-to-edge', size=7.5)

    # ── Domain components ──────────────────────────────────
    solid_box(ax, 1.8, 3.5, 2.8, 1.3, C_BLUE, alpha=0.9)
    label(ax, 3.2, 4.45, 'Use Cases', size=8.5, bold=True)
    label(ax, 3.2, 4.0,  'AnalyzeVoiceSpoofingUseCase', size=7.5)
    label(ax, 3.2, 3.6,  'FuseAuthenticationUseCase', size=7.5)

    solid_box(ax, 5.2, 3.5, 3.6, 1.3, C_BLUE, alpha=0.9)
    label(ax, 7.0, 4.45, 'Repository Interfaces', size=8.5, bold=True)
    label(ax, 7.0, 4.0,  'VoiceSpoofingRepository', size=7.5)
    label(ax, 7.0, 3.6,  'SecurityConfigRepository  AsvScoreRepository', size=7.5)

    solid_box(ax, 9.4, 3.5, 3.7, 1.3, C_BLUE, alpha=0.9)
    label(ax, 11.25, 4.45, 'Domain Models', size=8.5, bold=True)
    label(ax, 11.25, 4.0,  'DetectionResult  DetectionSession', size=7.5)
    label(ax, 11.25, 3.6,  'SecurityConfig  FusionDecisionResult', size=7.5)

    # ── Data components ────────────────────────────────────
    solid_box(ax, 1.8, 0.7, 2.5, 1.5, C_NAVY, alpha=0.9)
    label(ax, 3.05, 1.75, 'Audio Pipeline', size=8.5, bold=True)
    label(ax, 3.05, 1.35, 'MicrophoneAudioRecorder', size=7.5)
    label(ax, 3.05, 1.0,  'AudioRecord API  16kHz PCM', size=7.5)

    solid_box(ax, 4.7, 0.7, 2.5, 1.5, C_NAVY, alpha=0.9)
    label(ax, 5.95, 1.75, 'Feature & Model', size=8.5, bold=True)
    label(ax, 5.95, 1.35, 'AudioFeatureExtractor', size=7.5)
    label(ax, 5.95, 1.0,  'TFLiteSpoofDetectorEngine 12KB', size=7.5)

    solid_box(ax, 7.6, 0.7, 2.5, 1.5, C_NAVY, alpha=0.9)
    label(ax, 8.85, 1.75, 'Repository Impls', size=8.5, bold=True)
    label(ax, 8.85, 1.35, 'VoiceSpoofingRepositoryImpl', size=7.5)
    label(ax, 8.85, 1.0,  'HttpAsvScoreRepository', size=7.5)

    solid_box(ax, 10.5, 0.7, 2.6, 1.5, C_NAVY, alpha=0.9)
    label(ax, 11.8, 1.75, 'Storage & Export', size=8.5, bold=True)
    label(ax, 11.8, 1.35, 'DataStore Preferences', size=7.5)
    label(ax, 11.8, 1.0,  'CSV Export  FileTelemetry', size=7.5)

    # ── Arrows between layers ──────────────────────────────
    # Presentation → Domain
    arrow(ax, 3.2, 6.0, 3.2, 4.8, color=C_TEAL)
    arrow(ax, 7.0, 6.0, 7.0, 4.8, color=C_TEAL)

    # Domain → Data
    arrow(ax, 3.2, 3.5, 3.2, 2.2, color=C_BLUE)
    arrow(ax, 7.0, 3.5, 6.3, 2.2, color=C_BLUE)
    arrow(ax, 9.5, 3.5, 9.0, 2.2, color=C_BLUE)

    # dependency rule label
    ax.annotate('', xy=(0.5, 0.55), xytext=(0.5, 7.5),
                arrowprops=dict(arrowstyle='<-', color='#cccccc', lw=1.5,
                                mutation_scale=10))
    ax.text(0.18, 4.0, 'Dependency\nRule', ha='center', va='center',
            fontsize=7.5, color='#aaaaaa', rotation=90)

    # title
    ax.text(7.0, 7.85, 'Kiến trúc ứng dụng VoiceGuard — Android Clean Architecture',
            ha='center', va='center', fontsize=12, fontweight='bold', color=C_DARK)

    fig.tight_layout(pad=0.3)
    out = os.path.join(OUT, 'fig_android_architecture.png')
    fig.savefig(out, dpi=150, bbox_inches='tight', facecolor=C_WHITE)
    plt.close(fig)
    print(f'Saved: {out}')


# ════════════════════════════════════════════════════════════
# FIGURE 3.2 — Detection Tab UI mockup
# ════════════════════════════════════════════════════════════
def draw_detection_tab():
    fig = plt.figure(figsize=(5, 9.5))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 190)
    ax.axis('off')
    fig.patch.set_facecolor('#12151e')

    def rect(x, y, w, h, color, alpha=1.0, zorder=2, ec='none', lw=0):
        ax.add_patch(mpatches.Rectangle((x, y), w, h,
                     facecolor=color, edgecolor=ec, linewidth=lw,
                     alpha=alpha, zorder=zorder))

    def txt(x, y, s, size=8, color='white', bold=False, ha='center', va='center'):
        ax.text(x, y, s, ha=ha, va=va, fontsize=size, color=color,
                fontweight='bold' if bold else 'normal', zorder=10,
                fontfamily='monospace' if any(c.isascii() and not c.isalpha() for c in s) else 'sans-serif')

    # Phone body
    rect(2, 2, 96, 186, '#1a1f2e', zorder=1)

    # Status bar
    rect(2, 178, 96, 10, '#0d1117', zorder=2)
    txt(12, 183, '09:41', size=6.5, color='#aaaaaa')
    txt(88, 183, '|||  100%', size=6, color='#aaaaaa')

    # App bar
    rect(2, 164, 96, 14, '#111827', zorder=2)
    txt(50, 171, 'VoiceGuard', size=10, bold=True, color='#17b0d0')

    # Hero section (dark gradient)
    rect(2, 105, 96, 59, '#0a1628', zorder=2)
    rect(2, 105, 96, 25, '#0f1d35', alpha=0.7, zorder=2)

    # Hero text
    txt(50, 159, 'NHAN DE GHI AM', size=7.5, bold=True, color='#17b0d0')
    txt(50, 154, 'Giu 1-15 giay de phan tich', size=6.5, color='#7799bb')

    # Pulse rings (concentric circles around mic)
    for r, a in [(20, 0.06), (15, 0.10), (11, 0.15)]:
        ax.add_patch(plt.Circle((50, 130), r, color='#17b0d0',
                                fill=False, lw=1.2, alpha=a, zorder=3))
    # Mic button circle
    ax.add_patch(plt.Circle((50, 130), 9.5, color='#17b0d0', zorder=4))
    ax.add_patch(plt.Circle((50, 130), 9.5, color='#0b6f86', fill=False, lw=1.5, zorder=4))
    # Mic icon (simple lines)
    rect(47.8, 127.5, 4.4, 5.2, '#0a1628', zorder=5)  # mic body
    rect(48.8, 126.5, 2.4, 1.0, '#0a1628', zorder=5)  # mic base top
    ax.plot([50, 50], [125, 123.5], color='#0a1628', lw=1.5, zorder=5)
    ax.plot([47.5, 52.5], [123.5, 123.5], color='#0a1628', lw=1.5, zorder=5)

    # Timer + status
    txt(50, 116, '00:03', size=12, bold=True, color='white')
    rect(44, 109, 4, 4, '#e74c3c', zorder=3)  # red dot
    txt(52, 111, 'REC', size=6.5, bold=True, color='#e74c3c')

    # Waveform bar chart (simpler than line plot)
    np.random.seed(7)
    bar_vals = np.abs(np.random.normal(0.5, 0.25, 40)).clip(0.05, 1.0)
    bar_vals = np.convolve(bar_vals, np.ones(3)/3, mode='same')
    bw = 1.8
    for i, v in enumerate(bar_vals):
        bx = 8 + i * 2.1
        bh = v * 6
        ax.add_patch(mpatches.Rectangle((bx, 105 - bh/2), bw, bh,
                     facecolor='#17b0d0', alpha=0.4, zorder=3))

    # Result card — BONAFIDE (green)
    rect(5, 61, 90, 40, '#0d2218', zorder=3)
    rect(5, 61,  3, 40, '#27ae60', zorder=4)   # left accent bar
    rect(5, 99, 90,  1, '#1a3d28', zorder=4)   # top border
    txt(52, 96.5, 'BONAFIDE  —  ALLOW', size=9.5, bold=True, color='#27ae60')
    txt(52, 89.5, 'Xac suat gia mao: 3.2%', size=8, color='#88bb99')
    txt(52, 83.5, 'Quyet dinh: ALLOW   |   Tin cay: 96.8%', size=7.5, color='#6a9977')
    txt(52, 77.5, 'ASV score: 0.82   |   Model: TFLite v1', size=7, color='#557766')
    txt(52, 71.5, 'Thoi luong ghi: 3.2 giay', size=7, color='#557766')
    txt(52, 65.5, 'Feature: 4ms   |   Inference: 1ms', size=6.5, color='#446655')

    # Performance card
    rect(5, 22, 90, 36, '#111827', zorder=3)
    rect(5, 57, 90,  1, '#1f2937', zorder=3)
    txt(50, 53.5, 'Hieu nang pipeline', size=8, bold=True, color='#17b0d0')

    perf = [
        ('Feature Extraction', '4 ms',  '#3498db', 46),
        ('TFLite Inference',   '1 ms',  '#27ae60', 39),
        ('Total Pipeline',     '8 ms',  '#9b59b6', 32),
        ('RAM su dung',        '48 MB', '#e67e22', 25),
    ]
    for label_t, val, col, yp in perf:
        txt(30, yp, label_t, size=7, color='#8899aa', ha='center')
        txt(78, yp, val,     size=8.5, bold=True, color=col, ha='center')
        ax.plot([5, 95], [yp - 3, yp - 3], color='#1f2937', lw=0.4, zorder=4)

    # Bottom navigation bar
    rect(2, 2, 96, 18, '#111827', zorder=5)
    rect(2, 19, 96, 0.8, '#1f2937', zorder=5)
    nav_tabs = [('PHAT HIEN', '#17b0d0', True), ('LICH SU', '#555', False), ('CAI DAT', '#555', False)]
    for i, (name, col, active) in enumerate(nav_tabs):
        tx = 17 + i * 33
        if active:
            rect(tx - 13, 2.5, 26, 15, '#17b0d015', zorder=5)
            ax.plot([tx-5, tx+5], [18.5, 18.5], color='#17b0d0', lw=1.5, zorder=6)
        # icon dot
        ax.add_patch(plt.Circle((tx, 14), 2.5 if not active else 2.5,
                                color=col, alpha=0.7 if active else 0.35, zorder=6))
        txt(tx, 7.5, name, size=5.5, color=col, bold=active)

    fig.savefig(os.path.join(OUT, 'fig_ui_detection.png'),
                dpi=150, bbox_inches='tight', facecolor='#12151e')
    plt.close(fig)
    print('Saved: fig_ui_detection.png')


# ════════════════════════════════════════════════════════════
# FIGURE 3.3 — History + Settings Tab UI mockup
# ════════════════════════════════════════════════════════════
def draw_history_settings():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 9.5))
    fig.patch.set_facecolor('#12151e')
    plt.subplots_adjust(wspace=0.05)

    def rect(ax, x, y, w, h, color, alpha=1.0, zorder=2, ec='none', lw=0):
        ax.add_patch(mpatches.Rectangle((x, y), w, h,
                     facecolor=color, edgecolor=ec, linewidth=lw,
                     alpha=alpha, zorder=zorder))

    def txt(ax, x, y, s, size=8, color='white', bold=False, ha='center', va='center'):
        ax.text(x, y, s, ha=ha, va=va, fontsize=size, color=color,
                fontweight='bold' if bold else 'normal', zorder=10)

    def divider(ax, y):
        ax.plot([5, 95], [y, y], color='#1f2937', lw=0.5, zorder=5)

    for ax in (ax1, ax2):
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 190)
        ax.axis('off')
        rect(ax, 2, 2, 96, 186, '#1a1f2e', zorder=1)
        rect(ax, 2, 178, 96, 10, '#0d1117', zorder=2)
        txt(ax, 12, 183, '09:41', size=6.5, color='#aaaaaa')
        txt(ax, 88, 183, '|||  100%', size=6, color='#aaaaaa')
        rect(ax, 2, 2, 96, 18, '#111827', zorder=5)
        rect(ax, 2, 19, 96, 0.8, '#1f2937', zorder=5)

    # ── Tab 2: Lich su ─────────────────────────────────────
    rect(ax1, 2, 164, 96, 14, '#111827', zorder=2)
    txt(ax1, 50, 171, 'Lich su phan tich', size=10, bold=True)

    # Stat chips
    chip_data = [('Tong: 5', '#17b0d0', '#163558', 5),
                 ('That: 4', '#27ae60', '#0d2218', 36),
                 ('Gia: 1',  '#e74c3c', '#2e1010', 67)]
    for label_c, fg, bg, cx in chip_data:
        rect(ax1, cx, 151, 27, 10, bg, zorder=3)
        txt(ax1, cx+13.5, 156, label_c, size=7.5, color=fg, bold=True)

    # Export button
    rect(ax1, 15, 138, 70, 10, '#17b0d0', zorder=3)
    txt(ax1, 50, 143, 'Xuat CSV', size=8.5, bold=True, color='#0a1628')

    # Session list
    sessions = [
        ('14:32:10', 'BONAFIDE', '3.2%',  '#27ae60', '96.8%', '3.2s'),
        ('14:31:05', 'BONAFIDE', '8.1%',  '#27ae60', '91.9%', '2.8s'),
        ('14:29:42', 'SPOOF',    '87.4%', '#e74c3c', '87.4%', '4.1s'),
        ('14:28:11', 'BONAFIDE', '5.5%',  '#27ae60', '94.5%', '3.5s'),
        ('14:26:30', 'BONAFIDE', '2.1%',  '#27ae60', '97.9%', '2.5s'),
    ]
    for i, (ts, dec, prob, col, conf, dur) in enumerate(sessions):
        y = 124 - i * 22
        rect(ax1, 5, y, 90, 19, '#111827', zorder=3)
        rect(ax1, 5, y, 3,  19, col,       zorder=4)
        txt(ax1, 52, y+13.5, f'{dec}   {prob}', size=8, bold=True, color=col)
        txt(ax1, 52, y+8,    f'{ts}  |  Tin cay: {conf}', size=7, color='#888888')
        txt(ax1, 52, y+3,    f'Thoi luong: {dur}  |  TFLite', size=6.5, color='#555555')

    # Bottom nav
    nav1 = [('PHAT HIEN', '#555', False), ('LICH SU', '#17b0d0', True), ('CAI DAT', '#555', False)]
    for i, (name, col, active) in enumerate(nav1):
        tx = 17 + i * 33
        if active:
            rect(ax1, tx-13, 2.5, 26, 15, '#17b0d015', zorder=5)
            ax1.plot([tx-5, tx+5], [18.5, 18.5], color='#17b0d0', lw=1.5, zorder=6)
        ax1.add_patch(plt.Circle((tx, 14), 2.5, color=col, alpha=0.6 if active else 0.3, zorder=6))
        txt(ax1, tx, 7.5, name, size=5.5, color=col, bold=active)

    # ── Tab 3: Cai dat ─────────────────────────────────────
    rect(ax2, 2, 164, 96, 14, '#111827', zorder=2)
    txt(ax2, 50, 171, 'Cai dat', size=10, bold=True)

    # Model info card
    rect(ax2, 5, 141, 90, 22, '#0d1e3a', zorder=3)
    rect(ax2, 5, 162, 90,  1, '#17b0d040', zorder=3)
    txt(ax2, 50, 158, 'Thong tin mo hinh TFLite', size=8.5, bold=True, color='#17b0d0')
    metrics = [('Accuracy', '98.23%', '#27ae60', 22),
               ('F1-Score', '98.23%', '#3498db', 50),
               ('AUC',      '0.9974', '#9b59b6', 78)]
    for mk, mv, mc, mx in metrics:
        txt(ax2, mx, 151.5, mk,  size=7,   color='#7799aa')
        txt(ax2, mx, 145.5, mv,  size=8,   color=mc, bold=True)
    txt(ax2, 50, 142.5, 'EER = 1.93%  |  Kich thuoc: 12 KB', size=6.5, color='#556677')

    # Settings groups
    groups = [
        ('Nguong phat hien', [
            ('Spoof Threshold', '0.50', '#17b0d0'),
            ('ASV Threshold',   '0.70', '#17b0d0'),
        ]),
        ('ASV tu xa', [
            ('Su dung ASV tu xa', 'BAT',              '#27ae60'),
            ('ASV Endpoint',      'http://10.0.2.2/', '#777777'),
        ]),
    ]
    gy = 129
    for gtitle, items in groups:
        gh = len(items) * 12 + 10
        rect(ax2, 5, gy - gh, 90, gh, '#111827', zorder=3)
        txt(ax2, 10, gy - 3, gtitle, size=7, bold=True, color='#7788aa', ha='left')
        for j, (k, v, vc) in enumerate(items):
            iy = gy - 10 - j * 12
            txt(ax2, 12, iy, k, size=7.5, color='#cccccc', ha='left')
            txt(ax2, 88, iy, v, size=7.5, bold=True, color=vc, ha='right')
            if j < len(items) - 1:
                divider(ax2, iy - 5)
        gy -= gh + 5

    # About card
    rect(ax2, 5, 25, 90, 44, '#0a1221', zorder=3)
    rect(ax2, 5, 68, 90,  1, '#17b0d030', zorder=3)
    txt(ax2, 50, 64.5, 'Thong tin de tai luan van', size=8, bold=True, color='#17b0d0')
    about = [
        ('De tai:',    'Phat hien gia mao giong noi Android'),
        ('Hoc vien:', 'Nguyen Kim Ngan — CHAT10'),
        ('GVHD:',     'TS. Mai Duc Tho'),
        ('Truong:',   'Hoc vien Ky thuat Mat ma'),
        ('Cong nghe:','Kotlin | Compose | TFLite'),
    ]
    for i, (k, v) in enumerate(about):
        iy = 58 - i * 7.5
        txt(ax2, 12, iy, k, size=7, color='#7788aa', ha='left')
        txt(ax2, 88, iy, v, size=7, color='#cccccc', ha='right')

    # Bottom nav
    nav2 = [('PHAT HIEN', '#555', False), ('LICH SU', '#555', False), ('CAI DAT', '#17b0d0', True)]
    for i, (name, col, active) in enumerate(nav2):
        tx = 17 + i * 33
        if active:
            rect(ax2, tx-13, 2.5, 26, 15, '#17b0d015', zorder=5)
            ax2.plot([tx-5, tx+5], [18.5, 18.5], color='#17b0d0', lw=1.5, zorder=6)
        ax2.add_patch(plt.Circle((tx, 14), 2.5, color=col, alpha=0.6 if active else 0.3, zorder=6))
        txt(ax2, tx, 7.5, name, size=5.5, color=col, bold=active)

    out = os.path.join(OUT, 'fig_ui_history_settings.png')
    fig.savefig(out, dpi=150, bbox_inches='tight', facecolor='#12151e')
    plt.close(fig)
    print(f'Saved: {out}')


if __name__ == '__main__':
    draw_dnn_architecture()
    draw_android_architecture()
    draw_detection_tab()
    draw_history_settings()
    print('All figures generated.')

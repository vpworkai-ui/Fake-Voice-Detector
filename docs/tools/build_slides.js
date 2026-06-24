/**
 * VoiceGuard Thesis Defense Slides
 * Nguyễn Kim Ngân — HV Kỹ thuật Mật mã — 2026
 * Data: 100% real from evaluation files
 */
const pptxgen = require("pptxgenjs");

const DEST = "/Users/phucit/Desktop/Work/Apps/Flutter/Projects/fake_voice_detector/docs/SlideThuyetTrinh_VoiceGuard_NguyenKimNgan.pptx";
const SHOTS = "/Users/phucit/Desktop/Work/Apps/Flutter/Projects/fake_voice_detector/docs/figures/screenshots";
const FIGS  = "/Users/phucit/Desktop/Work/Apps/Flutter/Projects/fake_voice_detector/ml/artifacts/report_figures";
const TSNE  = "/Users/phucit/Desktop/Work/Apps/Flutter/Projects/fake_voice_detector/ml/artifacts/tsne";

// ── Palette ──────────────────────────────────────────────────────────────
const NAVY   = "0D1B2A";   // deep navy (dominant)
const NAVY2  = "1B2A3B";   // slightly lighter navy
const TEAL   = "00897B";   // teal accent
const TEAL2  = "00BFA5";   // lighter teal
const WHITE  = "FFFFFF";
const OFFWHT = "F0F4F8";   // off-white for content slides
const GRAY   = "64748B";
const LGRAY  = "CBD5E1";
const RED    = "E53935";
const GREEN  = "2E7D32";
const AMBER  = "F9A825";

const pres = new pptxgen();
pres.layout  = "LAYOUT_16x9";
pres.author  = "Nguyen Kim Ngan";
pres.title   = "VoiceGuard — Deepfake Voice Detection";

// ── Helper: slide section label ──────────────────────────────────────────
function sectionDot(slide, label) {
  slide.addShape("rect", { x: 0.4, y: 0.22, w: 0.06, h: 0.06, fill: { color: TEAL2 }, line: { color: TEAL2 } });
  slide.addText(label, { x: 0.55, y: 0.15, w: 9, h: 0.28, fontSize: 9, color: TEAL2, bold: true, charSpacing: 2, margin: 0 });
}

// ── Helper: stat card ───────────────────────────────────────────────────
function statCard(slide, x, y, w, h, value, label, color) {
  slide.addShape("rect", { x, y, w, h, fill: { color: NAVY2 }, line: { color: color, width: 1.5 },
    shadow: { type: "outer", blur: 4, offset: 2, angle: 135, color: "000000", opacity: 0.25 } });
  slide.addText(value, { x: x+0.05, y: y+0.1,  w: w-0.1, h: h*0.55, fontSize: 26, color: color, bold: true, align: "center", valign: "middle" });
  slide.addText(label, { x: x+0.05, y: y+h*0.62, w: w-0.1, h: h*0.35, fontSize: 9,  color: LGRAY, align: "center", valign: "top" });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 1 — TITLE
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: NAVY };

  // Teal accent left bar
  s.addShape("rect", { x: 0, y: 0, w: 0.12, h: 5.625, fill: { color: TEAL }, line: { color: TEAL } });

  // Institution
  s.addText("HỌC VIỆN KỸ THUẬT MẬT MÃ", {
    x: 0.3, y: 0.35, w: 9.4, h: 0.4, fontSize: 11, color: TEAL2, bold: true,
    charSpacing: 3, align: "center"
  });

  // Main title
  s.addText("NGHIÊN CỨU GIẢI PHÁP", {
    x: 0.3, y: 1.0, w: 9.4, h: 0.7, fontSize: 30, color: WHITE, bold: true, align: "center"
  });
  s.addText("PHÁT HIỆN GIẢ MẠO GIỌNG NÓI", {
    x: 0.3, y: 1.65, w: 9.4, h: 0.7, fontSize: 30, color: WHITE, bold: true, align: "center"
  });
  s.addText("(DEEPFAKE VOICE DETECTION)", {
    x: 0.3, y: 2.3, w: 9.4, h: 0.55, fontSize: 18, color: TEAL2, bold: true, align: "center"
  });
  s.addText("Sử dụng AI tích hợp trên thiết bị Android", {
    x: 0.3, y: 2.82, w: 9.4, h: 0.4, fontSize: 14, color: LGRAY, align: "center", italic: true
  });

  // Divider
  s.addShape("rect", { x: 3.5, y: 3.35, w: 3.0, h: 0.03, fill: { color: TEAL }, line: { color: TEAL } });

  // Author info
  s.addText([
    { text: "Học viên: ", options: { color: LGRAY, fontSize: 12 } },
    { text: "Nguyễn Kim Ngân", options: { color: WHITE, fontSize: 12, bold: true } },
  ], { x: 0.3, y: 3.55, w: 9.4, h: 0.35, align: "center" });
  s.addText([
    { text: "GVHD: ", options: { color: LGRAY, fontSize: 11 } },
    { text: "TS. Mai Đức Thọ", options: { color: WHITE, fontSize: 11 } },
    { text: "   |   Chuyên ngành: Kỹ thuật Mật mã   |   2026", options: { color: LGRAY, fontSize: 11 } },
  ], { x: 0.3, y: 3.92, w: 9.4, h: 0.32, align: "center" });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 2 — ĐẶT VẤN ĐỀ
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: OFFWHT };
  sectionDot(s, "ĐẶT VẤN ĐỀ");
  s.addText("Deepfake Voice đang là mối đe dọa bảo mật nghiêm trọng", {
    x: 0.4, y: 0.4, w: 9.2, h: 0.6, fontSize: 22, color: NAVY, bold: true
  });

  // 3 cards
  const cards = [
    { icon: "TTS", title: "Text-to-Speech", body: "AI tổng hợp giọng nói chân thực từ văn bản. Khó phân biệt bằng tai người.", color: RED },
    { icon: "VC",  title: "Voice Conversion", body: "Chuyển đổi giọng người này thành người khác trong thời gian thực.", color: AMBER },
    { icon: "RP",  title: "Replay Attack", body: "Phát lại giọng nói đã ghi âm trước để qua mặt hệ thống xác thực.", color: "1565C0" },
  ];
  cards.forEach((c, i) => {
    const x = 0.4 + i * 3.1;
    s.addShape("rect", { x, y: 1.1, w: 2.9, h: 2.2,
      fill: { color: WHITE },
      shadow: { type: "outer", blur: 5, offset: 2, angle: 135, color: "000000", opacity: 0.12 } });
    s.addShape("rect", { x, y: 1.1, w: 2.9, h: 0.08, fill: { color: c.color }, line: { color: c.color } });
    s.addText(c.icon, { x: x+0.1, y: 1.25, w: 0.7, h: 0.55, fontSize: 22, color: c.color, bold: true });
    s.addText(c.title, { x: x+0.1, y: 1.8, w: 2.7, h: 0.35, fontSize: 13, color: NAVY, bold: true });
    s.addText(c.body, { x: x+0.1, y: 2.18, w: 2.7, h: 0.9, fontSize: 10.5, color: GRAY });
  });

  // Impact
  s.addShape("rect", { x: 0.4, y: 3.5, w: 9.2, h: 1.6,
    fill: { color: NAVY }, line: { color: NAVY },
    shadow: { type: "outer", blur: 4, offset: 2, angle: 135, color: "000000", opacity: 0.2 } });
  s.addText("Tại Việt Nam:", { x: 0.6, y: 3.6, w: 9.0, h: 0.35, fontSize: 12, color: TEAL2, bold: true });
  s.addText([
    { text: "Ngân hàng số, chính phủ điện tử đang dùng xác thực giọng nói — cần giải pháp phát hiện giả mạo ", options: { color: LGRAY, fontSize: 11 } },
    { text: "nhỏ gọn, chạy offline, real-time", options: { color: WHITE, fontSize: 11, bold: true } },
    { text: " trên thiết bị di động.", options: { color: LGRAY, fontSize: 11 } },
  ], { x: 0.6, y: 3.95, w: 9.0, h: 0.45 });
  s.addText("→ Đề tài: VoiceGuard — ứng dụng Android phát hiện deepfake voice bằng AI on-device", {
    x: 0.6, y: 4.42, w: 9.0, h: 0.35, fontSize: 11, color: TEAL2, bold: true
  });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 3 — GIẢI PHÁP TỔNG QUAN
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: OFFWHT };
  sectionDot(s, "GIẢI PHÁP");
  s.addText("Kiến trúc hai lớp: On-device AI + Acoustic Features", {
    x: 0.4, y: 0.4, w: 9.2, h: 0.55, fontSize: 21, color: NAVY, bold: true
  });

  // Pipeline boxes
  const steps = [
    { label: "Thu âm\n(16kHz)", sub: "AudioSource\nVOICE_RECOGNITION", color: "1565C0" },
    { label: "8 Đặc trưng\nâm thanh", sub: "< 5ms\ntrên CPU", color: TEAL },
    { label: "Log-Mel\nSpectrogram", sub: "[400×80]\nFFT nội bộ", color: TEAL },
    { label: "Cross-Scale\nAttention Lite", sub: "42KB TFLite\nDual-input", color: "6A1B9A" },
    { label: "Score\n0 → 1", sub: ">= 0.25\n= SPOOF", color: RED },
  ];
  steps.forEach((st, i) => {
    const x = 0.3 + i * 1.88;
    s.addShape("rect", { x, y: 1.15, w: 1.65, h: 1.3,
      fill: { color: NAVY2 }, line: { color: st.color, width: 1.5 } });
    s.addText(st.label, { x: x+0.05, y: 1.2, w: 1.55, h: 0.72, fontSize: 11, color: WHITE, bold: true, align: "center", valign: "middle" });
    s.addText(st.sub,   { x: x+0.05, y: 1.92, w: 1.55, h: 0.45, fontSize: 8.5, color: st.color, align: "center" });
    if (i < steps.length - 1) {
      s.addShape("rect", { x: x+1.65, y: 1.7, w: 0.23, h: 0.03, fill: { color: LGRAY }, line: { color: LGRAY } });
      s.addText(">", { x: x+1.72, y: 1.58, w: 0.2, h: 0.28, fontSize: 14, color: LGRAY, align: "center" });
    }
  });

  // Spec và Acoustic merge note
  s.addShape("rect", { x: 3.7, y: 2.6, w: 2.5, h: 0.4,
    fill: { color: "6A1B9A" }, line: { color: "6A1B9A" } });
  s.addText("Dual-input: Spec + Acoustic", { x: 3.7, y: 2.6, w: 2.5, h: 0.4, fontSize: 9, color: WHITE, align: "center", valign: "middle" });

  // Key specs
  s.addShape("rect", { x: 0.4, y: 3.2, w: 9.2, h: 1.9,
    fill: { color: NAVY }, line: { color: NAVY } });
  s.addText("Thông số kỹ thuật chính", { x: 0.6, y: 3.28, w: 9.0, h: 0.32, fontSize: 11, color: TEAL2, bold: true });

  const specs = [
    ["Model", "Cross-Scale Attention Lite"],
    ["Kích thước TFLite", "42,2 KB"],
    ["Tham số", "9.313"],
    ["Threshold", "0,25"],
    ["Pipeline latency", "311 ms"],
    ["RAM", "14,7 MB"],
  ];
  specs.forEach(([k, v], i) => {
    const col = i < 3 ? 0 : 1;
    const row = i % 3;
    const x = 0.6 + col * 4.6;
    const y = 3.65 + row * 0.36;
    s.addText(k + ": ", { x, y, w: 2.0, h: 0.32, fontSize: 10, color: LGRAY, margin: 0 });
    s.addText(v, { x: x + 1.7, y, w: 2.5, h: 0.32, fontSize: 10, color: WHITE, bold: true, margin: 0 });
  });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 4 — DỮ LIỆU HUẤN LUYỆN
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: OFFWHT };
  sectionDot(s, "DỮ LIỆU");
  s.addText("Dataset: 24.840 mẫu nội bộ + Dữ liệu ngoài nguồn", {
    x: 0.4, y: 0.4, w: 9.2, h: 0.55, fontSize: 21, color: NAVY, bold: true
  });

  // Internal data block
  s.addShape("rect", { x: 0.4, y: 1.1, w: 4.4, h: 3.9,
    fill: { color: NAVY2 }, line: { color: TEAL, width: 1.5 } });
  s.addText("DATASET NỘI BỘ", { x: 0.5, y: 1.18, w: 4.2, h: 0.35, fontSize: 11, color: TEAL2, bold: true, charSpacing: 2 });
  s.addText("24.840 mẫu", { x: 0.5, y: 1.52, w: 4.2, h: 0.55, fontSize: 26, color: WHITE, bold: true });
  s.addText([
    { text: "12.420 bonafide", options: { color: "64B5F6", breakLine: true } },
    { text: "12.420 spoof", options: { color: "EF9A9A", breakLine: true } },
    { text: "Nguồn: VIVOS + mc_thu_hue\n(tiếng Việt, 16kHz)", options: { color: LGRAY } },
  ], { x: 0.6, y: 2.1, w: 4.0, h: 1.1, fontSize: 11 });

  s.addShape("rect", { x: 0.5, y: 3.25, w: 4.1, h: 0.03, fill: { color: TEAL }, line: { color: TEAL } });
  s.addText("Phân chia:", { x: 0.6, y: 3.35, w: 4.0, h: 0.28, fontSize: 10, color: TEAL2, bold: true });
  s.addText([
    { text: "Train:      16.197 (65%)", options: { color: LGRAY, breakLine: true } },
    { text: "Val:          3.975 (16%)", options: { color: LGRAY, breakLine: true } },
    { text: "Test:         4.968 (20%)", options: { color: WHITE, bold: true } },
  ], { x: 0.6, y: 3.63, w: 4.0, h: 1.0, fontSize: 10.5 });

  // External data block
  s.addShape("rect", { x: 5.1, y: 1.1, w: 4.5, h: 3.9,
    fill: { color: NAVY2 }, line: { color: AMBER, width: 1.5 } });
  s.addText("DATASET NGOÀI NGUỒN", { x: 5.2, y: 1.18, w: 4.2, h: 0.35, fontSize: 11, color: AMBER, bold: true, charSpacing: 2 });
  s.addText("2.000 mẫu", { x: 5.2, y: 1.52, w: 4.2, h: 0.55, fontSize: 26, color: WHITE, bold: true });
  s.addText([
    { text: "1.000 bonafide", options: { color: "64B5F6", breakLine: true } },
    { text: "1.000 spoof", options: { color: "EF9A9A", breakLine: true } },
    { text: "Nguồn: VietSuperSpeech\n+ Google TTS tiếng Việt", options: { color: LGRAY } },
  ], { x: 5.3, y: 2.1, w: 4.1, h: 1.1, fontSize: 11 });

  s.addShape("rect", { x: 5.2, y: 3.25, w: 4.1, h: 0.03, fill: { color: AMBER }, line: { color: AMBER } });
  s.addText("Phân chia (theo yêu cầu GVHD):", { x: 5.3, y: 3.35, w: 4.0, h: 0.28, fontSize: 10, color: AMBER, bold: true });
  s.addText([
    { text: "Mix vào train:    300 (150/lớp = 15%)", options: { color: AMBER, breakLine: true } },
    { text: "Holdout test:  1.700 (850/lớp = 85%)", options: { color: WHITE, bold: true } },
  ], { x: 5.3, y: 3.63, w: 4.2, h: 0.75, fontSize: 10.5 });
  s.addText("→ Giảm domain shift, tăng tổng quát hóa", {
    x: 5.3, y: 4.42, w: 4.1, h: 0.35, fontSize: 10, color: TEAL2, bold: true
  });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 5 — 8 ĐẶC TRƯNG ÂM THANH
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: OFFWHT };
  sectionDot(s, "8 ĐẶC TRƯNG ÂM THANH");
  s.addText("Tại sao chọn đúng 8 đặc trưng này?", {
    x: 0.4, y: 0.4, w: 9.2, h: 0.55, fontSize: 21, color: NAVY, bold: true
  });

  const features = [
    { name: "RMS",          formula: "sqrt(1/N·Σx²)",        why: "Năng lượng tổng. TTS ổn định bất thường",    group: "NL", gc: TEAL },
    { name: "MeanAbs",      formula: "1/N·Σ|x|",             why: "Biên độ TB. TTS đều đặn hơn giọng thật",     group: "NL", gc: TEAL },
    { name: "ZCR",          formula: "Σ|sgn(xᵢ)-sgn(xᵢ₋₁)|/2N", why: "Tần số tức thời. TTS thiếu nhiễu tự nhiên", group: "TF", gc: "1565C0" },
    { name: "Peak",         formula: "max(|xᵢ|)",            why: "TTS peak gần 1.0, giọng thật phân tán",      group: "DD", gc: "6A1B9A" },
    { name: "CrestFactor",  formula: "Peak / RMS",           why: "Méo tín hiệu. Replay attack có CF cao",      group: "DD", gc: "6A1B9A" },
    { name: "ClippingRatio",formula: "count(|x|>0.99)/N",   why: "Tỉ lệ cắt xén. Cao trong replay attack",    group: "DD", gc: "6A1B9A" },
    { name: "DynamicRange", formula: "20·log(Peak/RMS)",     why: "Dải động. TTS ổn định, giọng thật biến động", group: "DD", gc: "6A1B9A" },
    { name: "ActiveDuration",formula: "VAD duration (s)",    why: "TTS cắt chuẩn theo câu, giọng thật tự nhiên", group: "TG", gc: RED },
  ];

  features.forEach((f, i) => {
    const col = i < 4 ? 0 : 1;
    const row = i % 4;
    const x = 0.35 + col * 4.85;
    const y = 1.1 + row * 1.05;
    s.addShape("rect", { x, y, w: 4.6, h: 0.95,
      fill: { color: WHITE },
      shadow: { type: "outer", blur: 3, offset: 1, angle: 135, color: "000000", opacity: 0.10 } });
    s.addShape("rect", { x, y, w: 0.07, h: 0.95, fill: { color: f.gc }, line: { color: f.gc } });
    s.addText(f.name, { x: x+0.15, y: y+0.05, w: 1.5, h: 0.35, fontSize: 11, color: NAVY, bold: true, margin: 0 });
    s.addText(f.formula, { x: x+0.15, y: y+0.43, w: 2.0, h: 0.38, fontSize: 8.5, color: GRAY, italic: true, margin: 0 });
    s.addText(f.why, { x: x+1.9, y: y+0.1, w: 2.55, h: 0.75, fontSize: 9, color: GRAY, margin: 0 });
  });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 6 — ABLATION STUDY
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: OFFWHT };
  sectionDot(s, "ABLATION STUDY");
  s.addText("Xác nhận định lượng tầm quan trọng từng đặc trưng", {
    x: 0.4, y: 0.4, w: 9.2, h: 0.55, fontSize: 21, color: NAVY, bold: true
  });
  s.addText("Baseline DNN (8 đặc trưng): Accuracy = 98,25%  |  F1 = 98,25%", {
    x: 0.4, y: 0.95, w: 9.2, h: 0.32, fontSize: 11, color: GRAY, italic: true
  });

  // Bar chart — drop in F1 (real data from ablation_results.json)
  const ablData = [
    { feat: "ActiveDuration", drop: 0.4806 },
    { feat: "ZCR",            drop: 0.2258 },
    { feat: "MeanAbs",        drop: 0.1612 },
    { feat: "Peak",           drop: 0.1363 },
    { feat: "CrestFactor",    drop: 0.0613 },
    { feat: "ClippingRatio",  drop: 0.0351 },
    { feat: "RMS",            drop: 0.0218 },
    { feat: "DynamicRange",   drop: -0.0218 },
  ];

  s.addChart(pres.charts.BAR, [{
    name: "Mức giảm F1 (%)",
    labels: ablData.map(d => d.feat),
    values: ablData.map(d => Math.abs(d.drop)),
  }], {
    x: 0.4, y: 1.35, w: 5.8, h: 3.9,
    barDir: "bar",
    chartColors: ablData.map(d => d.drop > 0 ? "E53935" : "2E7D32"),
    showValue: true,
    dataLabelColor: "1E293B",
    dataLabelFontSize: 9,
    valAxisLabelColor: "64748B",
    catAxisLabelColor: "1E293B",
    valGridLine: { color: "E2E8F0", size: 0.5 },
    catGridLine: { style: "none" },
    chartArea: { fill: { color: "FFFFFF" } },
    showLegend: false,
    showTitle: false,
    valAxisMinVal: 0,
    valAxisMaxVal: 0.55,
  });

  // Right side — conclusion
  s.addShape("rect", { x: 6.4, y: 1.35, w: 3.2, h: 3.9,
    fill: { color: NAVY }, line: { color: NAVY } });
  s.addText("Kết luận", { x: 6.55, y: 1.5, w: 2.9, h: 0.35, fontSize: 12, color: TEAL2, bold: true });
  s.addText([
    { text: "7/8 đặc trưng đều có đóng góp dương khi bỏ đi F1 giảm.\n\n", options: { color: LGRAY, fontSize: 10, breakLine: false } },
    { text: "ActiveDuration ", options: { color: WHITE, fontSize: 10, bold: true } },
    { text: "quan trọng nhất: F1 giảm 0,48% khi bỏ.\n\n", options: { color: LGRAY, fontSize: 10 } },
    { text: "DynamicRange ", options: { color: "4CAF50", fontSize: 10, bold: false } },
    { text: "ít nhất: F1 tăng 0,02% — giữ lại để đảm bảo tổng quát hóa.\n\n", options: { color: LGRAY, fontSize: 10 } },
    { text: "Giữ đúng 8 đặc trưng ", options: { color: RED, fontSize: 10, bold: true } },
    { text: "giúp phần app demo và phần giải thích bám sát pipeline runtime hiện tại.", options: { color: LGRAY, fontSize: 10 } },
  ], { x: 6.55, y: 1.9, w: 2.9, h: 3.1 });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 7 — KẾT QUẢ 3 MODEL
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: OFFWHT };
  sectionDot(s, "KẾT QUẢ ĐÁNH GIÁ");
  s.addText("So sánh 3 mô hình — Threshold đồng nhất = 0,25", {
    x: 0.4, y: 0.4, w: 9.2, h: 0.55, fontSize: 21, color: NAVY, bold: true
  });

  // Internal results
  s.addText("INTERNAL TEST (4.968 mẫu, threshold 0,5)", {
    x: 0.4, y: 1.05, w: 9.2, h: 0.3, fontSize: 10, color: TEAL, bold: true, charSpacing: 1
  });
  s.addChart(pres.charts.BAR, [
    { name: "Accuracy (%)", labels: ["Cross-Scale\n★", "AASIST Lite", "CBAM ResNet"], values: [99.32, 96.68, 99.26] },
    { name: "F1 (%)",       labels: ["Cross-Scale\n★", "AASIST Lite", "CBAM ResNet"], values: [99.32, 96.69, 99.26] },
  ], {
    x: 0.4, y: 1.35, w: 9.2, h: 1.6,
    barDir: "col", barGrouping: "clustered",
    chartColors: ["028090", "00A896"],
    showValue: true, dataLabelFontSize: 9,
    valAxisMinVal: 93, valAxisMaxVal: 101,
    valAxisLabelColor: "64748B", catAxisLabelColor: "1E293B",
    valGridLine: { color: "E2E8F0", size: 0.5 }, catGridLine: { style: "none" },
    chartArea: { fill: { color: "FFFFFF" } },
    legendPos: "r", legendFontSize: 9,
    showTitle: false,
  });

  // External results
  s.addText("EXTERNAL HOLDOUT (1.700 mẫu, threshold đồng nhất 0,25)", {
    x: 0.4, y: 3.05, w: 9.2, h: 0.3, fontSize: 10, color: AMBER, bold: true, charSpacing: 1
  });
  s.addChart(pres.charts.BAR, [
    { name: "Accuracy (%)", labels: ["Cross-Scale ★", "AASIST Lite", "CBAM ResNet"], values: [85.29, 70.88, 85.53] },
    { name: "Recall (%)",   labels: ["Cross-Scale ★", "AASIST Lite", "CBAM ResNet"], values: [97.65, 55.88, 96.47] },
    { name: "F1 (%)",       labels: ["Cross-Scale ★", "AASIST Lite", "CBAM ResNet"], values: [86.91, 65.74, 86.96] },
  ], {
    x: 0.4, y: 3.35, w: 9.2, h: 1.9,
    barDir: "col", barGrouping: "clustered",
    chartColors: ["028090", "F9A825", "6A1B9A"],
    showValue: true, dataLabelFontSize: 8.5,
    valAxisMinVal: 40, valAxisMaxVal: 105,
    valAxisLabelColor: "64748B", catAxisLabelColor: "1E293B",
    valGridLine: { color: "E2E8F0", size: 0.5 }, catGridLine: { style: "none" },
    chartArea: { fill: { color: "FFFFFF" } },
    legendPos: "r", legendFontSize: 9,
    showTitle: false,
  });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 8 — LÝ DO CHỌN CROSS-SCALE + CONFUSION MATRIX
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: OFFWHT };
  sectionDot(s, "MODEL ĐÃ CHỌN");
  s.addText("Cross-Scale Attention Lite — Lý do chọn và Ma trận nhầm lẫn", {
    x: 0.4, y: 0.4, w: 9.2, h: 0.55, fontSize: 19, color: NAVY, bold: true
  });

  // Left: why choose
  s.addShape("rect", { x: 0.4, y: 1.05, w: 4.2, h: 4.0,
    fill: { color: NAVY2 }, line: { color: TEAL, width: 1.5 } });
  s.addText("Tại sao chọn Cross-Scale?", { x: 0.55, y: 1.15, w: 3.9, h: 0.35, fontSize: 11, color: TEAL2, bold: true });

  const reasons = [
    ["Accuracy ngoài", "85,29%", "Ngang CBAM (85,53%)"],
    ["Recall Spoof",   "97,65%", "Cao nhất — bảo mật tốt"],
    ["Kích thước",     "42,2 KB", "Nhỏ hơn CBAM 31%"],
    ["Tham số",        "9.313",  "Ít hơn CBAM 34%"],
    ["AASIST Recall",  "55,88%", "Loại — quá thấp"],
  ];
  reasons.forEach(([label, val, note], i) => {
    const y = 1.6 + i * 0.67;
    const col = i === 4 ? RED : TEAL2;
    s.addText(label + ":", { x: 0.55, y, w: 1.8, h: 0.3, fontSize: 10, color: LGRAY, margin: 0 });
    s.addText(val, { x: 2.0, y, w: 1.1, h: 0.3, fontSize: 11, color: col, bold: true, margin: 0 });
    s.addText(note, { x: 0.55, y: y+0.3, w: 3.9, h: 0.3, fontSize: 9, color: GRAY, italic: true, margin: 0 });
  });

  // Right: confusion matrix numbers
  s.addShape("rect", { x: 4.8, y: 1.05, w: 4.8, h: 4.0,
    fill: { color: NAVY2 }, line: { color: AMBER, width: 1.5 } });
  s.addText("Ma trận nhầm lẫn @ threshold=0,25", { x: 4.95, y: 1.15, w: 4.5, h: 0.35, fontSize: 11, color: AMBER, bold: true });
  s.addText("External holdout — 1.700 mẫu", { x: 4.95, y: 1.5, w: 4.5, h: 0.28, fontSize: 9.5, color: LGRAY });

  // 2x2 matrix cells
  const cells = [
    { label: "TN", val: "620", sub: "Bonafide dự đúng", x: 5.1, y: 1.9, col: "2E7D32" },
    { label: "FP", val: "230", sub: "Bonafide → SPOOF sai", x: 7.1, y: 1.9, col: RED },
    { label: "FN", val: "20",  sub: "SPOOF bị bỏ sót", x: 5.1, y: 3.2, col: AMBER },
    { label: "TP", val: "830", sub: "SPOOF phát hiện đúng", x: 7.1, y: 3.2, col: "2E7D32" },
  ];
  cells.forEach(c => {
    s.addShape("rect", { x: c.x, y: c.y, w: 1.85, h: 1.1,
      fill: { color: NAVY }, line: { color: c.col, width: 1.2 } });
    s.addText(c.label, { x: c.x+0.08, y: c.y+0.05, w: 0.5, h: 0.3, fontSize: 10, color: c.col, bold: true, margin: 0 });
    s.addText(c.val,   { x: c.x+0.08, y: c.y+0.3,  w: 1.7, h: 0.45, fontSize: 24, color: WHITE, bold: true, align: "center" });
    s.addText(c.sub,   { x: c.x+0.05, y: c.y+0.77, w: 1.75, h: 0.28, fontSize: 7.5, color: LGRAY, align: "center" });
  });
  // Axis labels
  s.addText("Dự đoán\nBONAFIDE", { x: 5.1, y: 1.62, w: 1.85, h: 0.28, fontSize: 8, color: LGRAY, align: "center" });
  s.addText("Dự đoán\nSPOOF",    { x: 7.1, y: 1.62, w: 1.85, h: 0.28, fontSize: 8, color: LGRAY, align: "center" });
  s.addText("Thật\nBONAFIDE", { x: 4.72, y: 1.9,  w: 0.38, h: 1.1, fontSize: 7, color: LGRAY, align: "center", valign: "middle" });
  s.addText("Thật\nSPOOF",    { x: 4.72, y: 3.2,  w: 0.38, h: 1.1, fontSize: 7, color: LGRAY, align: "center", valign: "middle" });

  // Key metrics
  s.addText("Acc=85,29%  Recall=97,65%  F1=86,91%  FAR=27,06%  FRR=2,35%", {
    x: 4.95, y: 4.45, w: 4.5, h: 0.35, fontSize: 9, color: TEAL2, align: "center"
  });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 9 — t-SNE DOMAIN SHIFT
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: OFFWHT };
  sectionDot(s, "PHÂN TÍCH DOMAIN SHIFT");
  s.addText("t-SNE: Domain shift trước và sau khi mix dữ liệu ngoài", {
    x: 0.4, y: 0.4, w: 9.2, h: 0.55, fontSize: 20, color: NAVY, bold: true
  });

  // t-SNE combined image
  s.addImage({ path: TSNE + "/tsne_combined.png", x: 0.4, y: 1.0, w: 7.5, h: 3.8 });

  // Right insight box
  s.addShape("rect", { x: 8.05, y: 1.0, w: 1.6, h: 3.8,
    fill: { color: NAVY }, line: { color: NAVY } });
  s.addText([
    { text: "Phát hiện\n\n", options: { color: TEAL2, bold: true, fontSize: 10 } },
    { text: "Bonafide vs Spoof tách biệt ro\n\n", options: { color: LGRAY, fontSize: 8.5 } },
    { text: "Domain shift:\n", options: { color: AMBER, bold: true, fontSize: 9 } },
    { text: "Internal va External nam rieng\n\n", options: { color: LGRAY, fontSize: 8.5 } },
    { text: "Sau mix:\n", options: { color: TEAL2, bold: true, fontSize: 9 } },
    { text: "Acc tang\n42,9%->85,3%", options: { color: WHITE, bold: true, fontSize: 9 } },
  ], { x: 8.1, y: 1.1, w: 1.5, h: 3.5 });

  s.addText("6.668 mau: internal test 4.968 + external holdout 1.700 | seed=42", {
    x: 0.4, y: 5.0, w: 9.2, h: 0.28, fontSize: 8.5, color: GRAY, italic: true
  });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 10 — ỨNG DỤNG ANDROID
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: OFFWHT };
  sectionDot(s, "ỨNG DỤNG ANDROID");
  s.addText("VoiceGuard — Minh chứng chạy thực tế trên Emulator", {
    x: 0.4, y: 0.4, w: 9.2, h: 0.55, fontSize: 20, color: NAVY, bold: true
  });

  // 3 screenshots
  const screenData = [
    { path: SHOTS + "/new_04_bonafide_all3.png", cap: "File BONAFIDE\n3 model: BONAFIDE", capCol: "2E7D32" },
    { path: SHOTS + "/new_05_spoof_result.png",  cap: "File SPOOF\n3 model: SPOOF", capCol: RED },
    { path: SHOTS + "/new_06_settings_clean.png", cap: "Cai dat\nNguong spoof | Dataset", capCol: TEAL },
  ];
  screenData.forEach((sc, i) => {
    const x = 0.35 + i * 3.15;
    s.addShape("rect", { x, y: 1.05, w: 2.8, h: 3.6,
      fill: { color: NAVY2 }, line: { color: sc.capCol, width: 1 },
      shadow: { type: "outer", blur: 5, offset: 2, angle: 135, color: "000000", opacity: 0.2 } });
    s.addImage({ path: sc.path, x: x+0.08, y: 1.13, w: 2.64, h: 2.9 });
    s.addText(sc.cap, { x, y: 4.08, w: 2.8, h: 0.52, fontSize: 10, color: sc.capCol, bold: true, align: "center" });
  });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 11 — HIỆU NĂNG THIẾT BỊ
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: OFFWHT };
  sectionDot(s, "HIỆU NĂNG THIẾT BỊ");
  s.addText("Đo từ app chạy trên Android Emulator — real-time on-device", {
    x: 0.4, y: 0.4, w: 9.2, h: 0.55, fontSize: 20, color: NAVY, bold: true
  });

  // Big stat cards
  const stats = [
    { val: "311 ms", lbl: "Tổng pipeline\n(ghi âm → kết quả)", col: TEAL },
    { val: "63 ms",  lbl: "TFLite inference\n(dual-input model)", col: "1565C0" },
    { val: "135 ms", lbl: "Trích đặc trưng\n(8 features + Log-Mel)", col: AMBER },
    { val: "14,7 MB",lbl: "RAM sử dụng\n(JVM heap)", col: "6A1B9A" },
    { val: "42 KB",  lbl: "Model TFLite\n(cross_scale_lite)", col: GREEN },
  ];
  stats.forEach((st, i) => {
    statCard(s, 0.35 + i * 1.87, 1.2, 1.72, 1.65, st.val, st.lbl, st.col);
  });

  // Pipeline chart
  s.addChart(pres.charts.BAR, [{
    name: "Thời gian (ms)",
    labels: ["Trich dac trung", "TFLite inference", "Overhead/other", "Tong pipeline"],
    values: [135, 63, 113, 311],
  }], {
    x: 0.4, y: 3.05, w: 5.5, h: 2.2,
    barDir: "col",
    chartColors: [AMBER.replace("F9","F9"), "1565C0", "64748B", TEAL],
    showValue: true, dataLabelFontSize: 9,
    valAxisLabelColor: "64748B", catAxisLabelColor: "1E293B",
    valGridLine: { color: "E2E8F0", size: 0.5 }, catGridLine: { style: "none" },
    chartArea: { fill: { color: "FFFFFF" } },
    showLegend: false, showTitle: false,
  });

  // Tiêu chí nghiệm thu
  s.addShape("rect", { x: 6.1, y: 3.05, w: 3.5, h: 2.2,
    fill: { color: NAVY }, line: { color: NAVY } });
  s.addText("Tieu chi nghiem thu", { x: 6.25, y: 3.12, w: 3.2, h: 0.32, fontSize: 11, color: TEAL2, bold: true });
  const criteria = [
    ["Accuracy >= 80%",   "85,29%", true],
    ["Recall >= 85%",     "97,65%", true],
    ["F1 >= 80%",         "86,91%", true],
    ["TFLite <= 100KB",   "42,2 KB", true],
    ["Latency <= 500ms",  "311 ms",  true],
    ["RAM <= 50MB",       "14,7 MB", true],
  ];
  criteria.forEach(([req, got, pass], i) => {
    const y = 3.5 + i * 0.28;
    s.addText(req, { x: 6.25, y, w: 2.2, h: 0.26, fontSize: 9, color: LGRAY, margin: 0 });
    s.addText(got, { x: 8.0, y, w: 1.45, h: 0.26, fontSize: 9, color: pass ? TEAL2 : RED, bold: true, margin: 0 });
  });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 12 — KẾT LUẬN
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: NAVY };

  s.addShape("rect", { x: 0, y: 0, w: 0.12, h: 5.625, fill: { color: TEAL }, line: { color: TEAL } });

  s.addText("KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN", {
    x: 0.3, y: 0.3, w: 9.4, h: 0.45, fontSize: 11, color: TEAL2, bold: true, charSpacing: 3, align: "center"
  });

  // Left — achievements
  s.addShape("rect", { x: 0.3, y: 0.9, w: 4.6, h: 3.9,
    fill: { color: NAVY2 }, line: { color: TEAL, width: 1.2 } });
  s.addText("Da dat duoc", { x: 0.45, y: 1.0, w: 4.3, h: 0.32, fontSize: 11, color: TEAL2, bold: true });
  const done = [
    "Mo hinh Cross-Scale Attention Lite 42KB, on-device",
    "8 dac trung am thanh co can cu khoa hoc (ablation study)",
    "External accuracy 85,29% sau khi mix du lieu ngoai",
    "Recall spoof 97,65% - it bo sot giong gia mao",
    "App Android VoiceGuard: 311ms, 14,7MB RAM",
    "t-SNE phan tich domain shift ro rang",
  ];
  done.forEach((item, i) => {
    s.addShape("rect", { x: 0.5, y: 1.42+i*0.38, w: 0.08, h: 0.08, fill: { color: TEAL2 }, line: { color: TEAL2 } });
    s.addText(item, { x: 0.68, y: 1.38+i*0.38, w: 4.1, h: 0.35, fontSize: 9.5, color: LGRAY });
  });

  // Right — future work
  s.addShape("rect", { x: 5.15, y: 0.9, w: 4.5, h: 3.9,
    fill: { color: NAVY2 }, line: { color: AMBER, width: 1.2 } });
  s.addText("Huong phat trien", { x: 5.3, y: 1.0, w: 4.2, h: 0.32, fontSize: 11, color: AMBER, bold: true });
  const future = [
    "Test tren thiet bi Android that de do latency/RAM thuc te",
    "Mo rong them lop xac minh khac neu can cho phien ban sau",
    "Tang du lieu ngoai nguon len 30-50% de tiep tuc giam domain shift",
    "Trien khai tren iOS (CoreML)",
    "Chong lai cac tan cong deepfake moi (diffusion-based TTS)",
  ];
  future.forEach((item, i) => {
    s.addShape("rect", { x: 5.3, y: 1.42+i*0.46, w: 0.08, h: 0.08, fill: { color: AMBER }, line: { color: AMBER } });
    s.addText(item, { x: 5.48, y: 1.38+i*0.46, w: 4.0, h: 0.4, fontSize: 9.5, color: LGRAY });
  });

  // Bottom
  s.addShape("rect", { x: 0.3, y: 4.95, w: 9.4, h: 0.38,
    fill: { color: TEAL }, line: { color: TEAL } });
  s.addText("Cam on GVHD TS. Mai Duc Tho va Hoi dong da lang nghe!", {
    x: 0.3, y: 4.95, w: 9.4, h: 0.38, fontSize: 12, color: WHITE, bold: true, align: "center", valign: "middle"
  });
}

pres.writeFile({ fileName: DEST })
  .then(() => console.log("OK: " + DEST))
  .catch(e => { console.error("ERROR:", e); process.exit(1); });

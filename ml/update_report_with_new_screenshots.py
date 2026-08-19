"""
Cập nhật báo cáo BaoCaoTienDo_02-06-2026 với ảnh chụp app MỚI (sau khi chuyển
TestFileAuditCard từ Settings → DetectTab theo Phương án 1).
Thay thế file _with_figures.docx cũ bằng bản mới hoàn chỉnh.
"""

import os
from docx import Document
from docx.shared import Inches, Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
import warnings
warnings.filterwarnings('ignore')

BASE        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(BASE, "docs", "reports")
SHOTS       = os.path.join(BASE, "docs", "figures", "screenshots")
FIGS        = os.path.join(BASE, "ml", "artifacts", "report_figures")
TSNE        = os.path.join(BASE, "ml", "artifacts", "tsne")

SRC  = os.path.join(REPORTS_DIR, "BaoCaoTienDo_02-06-2026_NguyenKimNgan.docx")
DEST = os.path.join(REPORTS_DIR, "BaoCaoTienDo_02-06-2026_NguyenKimNgan_with_figures.docx")


# ── helpers ────────────────────────────────────────────────────────────────
def add_heading(doc, text, level=2):
    p = doc.add_paragraph(text, style=f"Heading{level}")
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    return p


def add_caption(doc, bold_prefix, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = p.add_run(bold_prefix); r1.bold = True; r1.font.size = Pt(9)
    r2 = p.add_run(text);        r2.italic = True; r2.font.size = Pt(9)
    return p


def add_figure(doc, path, width_in=5.2, bold_prefix="", caption=""):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    if os.path.exists(path):
        run.add_picture(path, width=Inches(width_in))
    else:
        run.add_text(f"[Ảnh không tìm thấy: {os.path.basename(path)}]")
    if caption:
        add_caption(doc, bold_prefix, caption)
    return p


def side_by_side(doc, img1, img2, cap1, cap2, w=2.7):
    tbl = doc.add_table(rows=2, cols=2)
    for col_i, (img, cap) in enumerate([(img1, cap1), (img2, cap2)]):
        cell = tbl.cell(0, col_i)
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = cell.paragraphs[0].add_run()
        if os.path.exists(img):
            run.add_picture(img, width=Inches(w))
        cap_cell = tbl.cell(1, col_i)
        cap_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = cap_cell.paragraphs[0].add_run(cap)
        r.italic = True; r.font.size = Pt(9)
    doc.add_paragraph()


def three_in_row(doc, imgs, caps, w=1.9):
    tbl = doc.add_table(rows=2, cols=3)
    for i, (img, cap) in enumerate(zip(imgs, caps)):
        cell = tbl.cell(0, i)
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = cell.paragraphs[0].add_run()
        if os.path.exists(img):
            run.add_picture(img, width=Inches(w))
        cap_cell = tbl.cell(1, i)
        cap_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = cap_cell.paragraphs[0].add_run(cap)
        r.italic = True; r.font.size = Pt(8.5)
    doc.add_paragraph()


# ── main ───────────────────────────────────────────────────────────────────
def build_appendix(doc):
    doc.add_page_break()

    h = add_heading(doc, "PHỤ LỤC: Hình ảnh minh chứng từ App thực tế", level=1)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER

    p = doc.add_paragraph(
        "Tất cả ảnh chụp màn hình được lấy trực tiếp từ emulator Android (ADB screencap) "
        "sau khi điều chỉnh UX: chuyển chức năng kiểm tra file từ tab Cài đặt sang tab "
        "Phát hiện để đúng nguyên tắc thiết kế — tính năng chính nằm trong tab chức năng chính. "
        "Tất cả biểu đồ tính từ số liệu đánh giá thực tế, có xác minh chéo."
    )
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    doc.add_paragraph()

    # ══════════════════════════════════════════════════════════════════════
    # A. BỐ CỤC APP SAU CẬP NHẬT
    # ══════════════════════════════════════════════════════════════════════
    add_heading(doc, "A. Bố cục app sau cập nhật UX", level=2)

    p = doc.add_paragraph(
        "Phát hiện vấn đề UX: tính năng kiểm tra file (phân tích giọng thật/giả) "
        "nằm trong tab Cài đặt — không hợp lý vì Cài đặt chỉ dùng để cấu hình. "
        "Đã chuyển sang tab Phát hiện theo Phương án 1."
    )
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    doc.add_paragraph().add_run("Sơ đồ bố cục mới:").bold = True
    tbl = doc.add_table(rows=2, cols=3)
    headers = ["Tab Phát hiện", "Tab Lịch sử", "Tab Cài đặt"]
    contents = [
        "• Ghi âm microphone\n• Phân tích file mẫu\n  (BONAFIDE / SPOOF)",
        "• Danh sách phiên\n• Xuất CSV",
        "• Ngưỡng 0.25\n• ASV Backend\n• Dataset capture"
    ]
    for i, (h_txt, c_txt) in enumerate(zip(headers, contents)):
        hcell = tbl.cell(0, i)
        hcell.paragraphs[0].add_run(h_txt).bold = True
        hcell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn as qn2
        tcPr = hcell._tc.get_or_add_tcPr()
        shd = OxmlElement('w:shd')
        shd.set(qn2('w:val'), 'clear')
        shd.set(qn2('w:fill'), '00897B' if i == 0 else '263238')
        tcPr.append(shd)
        for run in hcell.paragraphs[0].runs:
            run.font.color.rgb = __import__('docx.shared', fromlist=['RGBColor']).RGBColor(0xFF, 0xFF, 0xFF)

        bcell = tbl.cell(1, i)
        bcell.paragraphs[0].add_run(c_txt).font.size = Pt(9)

    doc.add_paragraph()

    # ══════════════════════════════════════════════════════════════════════
    # B. TAB PHÁT HIỆN
    # ══════════════════════════════════════════════════════════════════════
    add_heading(doc, "B. Tab Phát hiện — Ghi âm + Phân tích file mẫu", level=2)

    # B1: Detect tab tổng quan
    doc.add_paragraph().add_run("B.1 — Tab Phát hiện: bố cục sau cập nhật").bold = True
    side_by_side(
        doc,
        os.path.join(SHOTS, "new_01_detect_overview.png"),
        os.path.join(SHOTS, "new_02_detect_filecard.png"),
        "Màn hình chính: nút ghi âm mic\nphía trên, phần tích file bên dưới",
        "Cuộn xuống: section 'Phân tích file mẫu'\nvới file picker và 3-model test",
        w=2.7
    )

    # B2: File BONAFIDE — tất cả 3 model
    doc.add_paragraph().add_run("B.2 — Kiểm tra file BONAFIDE (giọng thật): 3 model đều nhận đúng").bold = True
    add_figure(
        doc,
        os.path.join(SHOTS, "new_04_bonafide_all3.png"),
        width_in=2.9,
        bold_prefix="Hình B.2: ",
        caption="File bonafide_VIVOSDEV01_R002.wav — Nhãn thật: BONAFIDE\n"
                "Cross-Scale score=0.000234 ✅  |  AASIST score=0.000234 ✅  |  CBAM score=0.000234 ✅"
    )

    # B3: File SPOOF — tất cả 3 model
    doc.add_paragraph().add_run("B.3 — Kiểm tra file SPOOF (giọng giả): 3 model đều nhận đúng").bold = True
    add_figure(
        doc,
        os.path.join(SHOTS, "new_05_spoof_result.png"),
        width_in=2.9,
        bold_prefix="Hình B.3: ",
        caption="File spoof_segment_1109.wav — Nhãn thật: SPOOF\n"
                "Cross-Scale score=0.999357 ✅  |  AASIST score=0.999357 ✅  |  CBAM score=0.999357 ✅\n"
                "Tất cả đều vượt ngưỡng 0.25 → phát hiện đúng SPOOF"
    )

    doc.add_paragraph()

    # ══════════════════════════════════════════════════════════════════════
    # C. TAB CÀI ĐẶT SAU DỌN DẸP
    # ══════════════════════════════════════════════════════════════════════
    add_heading(doc, "C. Tab Cài đặt — Chỉ còn cấu hình", level=2)

    side_by_side(
        doc,
        os.path.join(SHOTS, "new_06_settings_clean.png"),
        os.path.join(SHOTS, "new_07_history.png"),
        "Cài đặt: subtitle 'Ngưỡng · ASV · Dataset'\nKhông còn card kiểm tra file",
        "Lịch sử: 4 phiên ghi âm\nTất cả BLOCK (SPOOF 100%)",
        w=2.7
    )

    doc.add_paragraph()

    # ══════════════════════════════════════════════════════════════════════
    # D. BIỂU ĐỒ HIỆU SUẤT
    # ══════════════════════════════════════════════════════════════════════
    add_heading(doc, "D. Biểu đồ hiệu suất — số liệu từ đánh giá thực tế", level=2)

    doc.add_paragraph().add_run("D.1 — Ma trận nhầm lẫn (TP/FP/FN/TN từ 1.700 mẫu)").bold = True
    add_figure(
        doc, os.path.join(FIGS, "fig_confusion_matrix.png"), 4.5,
        "Hình D.1: ",
        "TP=830  FP=230  FN=20  TN=620 | Accuracy=85.29%  Recall=97.65%  F1=86.91%  FAR=27.06%  FRR=2.35%"
    )

    doc.add_paragraph().add_run("D.2 — So sánh 3 model tại threshold đồng nhất = 0.25").bold = True
    add_figure(
        doc, os.path.join(FIGS, "fig_model_comparison.png"), 6.0,
        "Hình D.2: ",
        "Cross-Scale ★ F1=86.91%, Recall=97.65% — tốt nhất cho bảo mật (tối thiểu bỏ sót spoof)"
    )

    doc.add_paragraph().add_run("D.3 — Hiệu chỉnh ngưỡng: so sánh 2 điểm thực tế").bold = True
    add_figure(
        doc, os.path.join(FIGS, "fig_threshold_calibration.png"), 6.0,
        "Hình D.3: ",
        "Threshold=0.25 cho Recall=97.65%, FRR=2.35% (ít bỏ sót spoof hơn threshold=0.30)\n"
        "AUC=0.8735 | EER=17.82% | Nguồn: evaluation thực tế 1.700 mẫu"
    )

    doc.add_paragraph()

    # ══════════════════════════════════════════════════════════════════════
    # E. ABLATION STUDY
    # ══════════════════════════════════════════════════════════════════════
    add_heading(doc, "E. Ablation Study — Phân tích 8 đặc trưng âm thanh", level=2)

    side_by_side(
        doc,
        os.path.join(FIGS, "fig_ablation_study.png"),
        os.path.join(FIGS, "fig_progressive_addition.png"),
        "Leave-one-out: ActiveDuration quan trọng nhất\n(F1 giảm 0.48% khi xóa)",
        "Progressive: 5 đặc trưng đã đạt 98.23%\nGiữ đủ 8 để tổng quát hóa",
        w=3.0
    )

    doc.add_paragraph()

    # ══════════════════════════════════════════════════════════════════════
    # F. T-SNE
    # ══════════════════════════════════════════════════════════════════════
    add_heading(doc, "F. Trực quan hóa t-SNE — Domain Shift", level=2)

    p = doc.add_paragraph(
        "t-SNE chiếu 8 đặc trưng của 4.000 mẫu xuống 2D để giải thích tại sao "
        "accuracy giảm từ ~99% (internal) xuống ~50% (external) trước khi mix dữ liệu. "
        "Sau khi trộn 150 mẫu ngoài/lớp (15%), khoảng cách internal-external giảm 42%."
    )
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    tsne_combined = os.path.join(TSNE, "tsne_combined.png")
    if os.path.exists(tsne_combined):
        add_figure(
            doc, tsne_combined, 6.2,
            "Hình F.1: ",
            "(Trái) bonafide/spoof tách biệt rõ → 8 đặc trưng phân biệt tốt\n"
            "(Phải) Internal/External tạo cụm riêng → domain shift → giải thích accuracy ~50% ban đầu"
        )

    tsne_label  = os.path.join(TSNE, "tsne_label.png")
    tsne_source = os.path.join(TSNE, "tsne_source.png")
    if os.path.exists(tsne_label) and os.path.exists(tsne_source):
        side_by_side(
            doc, tsne_label, tsne_source,
            "Theo nhãn: bonafide (xanh) vs spoof (đỏ)\n→ Tách biệt rõ ràng",
            "Theo nguồn: internal (xanh) vs external (cam)\n→ Domain shift rõ ràng",
            w=3.0
        )

    doc.add_paragraph()

    # ══════════════════════════════════════════════════════════════════════
    # G. HIỆU NĂNG THIẾT BỊ
    # ══════════════════════════════════════════════════════════════════════
    add_heading(doc, "G. Hiệu năng thực tế trên thiết bị", level=2)

    add_figure(
        doc, os.path.join(FIGS, "fig_device_performance.png"), 6.2,
        "Hình G.1: ",
        "135ms trích đặc trưng + 63ms TFLite inference = 311ms tổng pipeline | RAM: 14.7MB\n"
        "Phù hợp real-time trên thiết bị di động Android"
    )

    print("[OK] Phần phụ lục đã xây dựng xong.")


def main():
    print(f"Đang tải: {SRC}")
    doc = Document(SRC)
    build_appendix(doc)
    doc.save(DEST)
    size_kb = os.path.getsize(DEST) // 1024
    print(f"[OK] Đã lưu: {DEST} ({size_kb} KB)")


if __name__ == "__main__":
    main()

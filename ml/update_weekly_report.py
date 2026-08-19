"""
Cập nhật BaoCaoTienDo_02-06-2026 trực tiếp:
1. Mục I  — thêm bullet về UX fix (chuyển kiểm tra file sang tab Phát hiện)
2. Sau Mục V — thêm ảnh chụp app thực tế (BONAFIDE + SPOOF + Settings mới)
3. Trước Mục VI — thêm ảnh biểu đồ hiệu suất và t-SNE
4. Mục VII — viết lại kế hoạch tuần 3 cụ thể hơn
"""

import os, copy
from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

BASE        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(BASE, "docs", "reports")
SHOTS       = os.path.join(BASE, "docs", "figures", "screenshots")
FIGS        = os.path.join(BASE, "ml", "artifacts", "report_figures")
TSNE_DIR    = os.path.join(BASE, "ml", "artifacts", "tsne")

SRC  = os.path.join(REPORTS_DIR, "BaoCaoTienDo_02-06-2026_NguyenKimNgan.docx")
DEST = os.path.join(REPORTS_DIR, "BaoCaoTienDo_02-06-2026_NguyenKimNgan.docx")


# ── helpers ────────────────────────────────────────────────────────────────
def add_img_centered(doc, path, width_in, caption="", caption_prefix=""):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    if os.path.exists(path):
        run.add_picture(path, width=Inches(width_in))
    else:
        p.add_run(f"[Ảnh không tìm thấy: {os.path.basename(path)}]")
    if caption:
        cp = doc.add_paragraph()
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if caption_prefix:
            r = cp.add_run(caption_prefix); r.bold = True; r.font.size = Pt(9)
        r2 = cp.add_run(caption); r2.italic = True; r2.font.size = Pt(9)


def side_by_side(doc, img1, img2, cap1, cap2, w=2.7):
    tbl = doc.add_table(rows=2, cols=2)
    for ci, (img, cap) in enumerate([(img1, cap1), (img2, cap2)]):
        cell = tbl.cell(0, ci)
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = cell.paragraphs[0].add_run()
        if os.path.exists(img):
            run.add_picture(img, width=Inches(w))
        cap_cell = tbl.cell(1, ci)
        cap_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = cap_cell.paragraphs[0].add_run(cap)
        r.italic = True; r.font.size = Pt(9)
    doc.add_paragraph()


def add_bold_para(doc, text, size=11):
    p = doc.add_paragraph()
    r = p.add_run(text); r.bold = True; r.font.size = Pt(size)
    return p


def insert_para_after(doc, ref_para, new_para):
    """Insert new_para XML after ref_para in document body."""
    ref_para._p.addnext(new_para._p)


# ── main ───────────────────────────────────────────────────────────────────
def main():
    print(f"Đang tải: {SRC}")
    doc = Document(SRC)

    # ══════════════════════════════════════════════════════════════════════
    # 1. Mục I — thêm bullet UX fix vào cuối danh sách công việc
    # ══════════════════════════════════════════════════════════════════════
    # Tìm paragraph index 8 (bullet "Tích hợp cross_scale...") và thêm sau đó
    target_text = "Tích hợp cross_scale_attention_lite"
    for i, p in enumerate(doc.paragraphs):
        if target_text in p.text:
            # Thêm bullet mới sau đoạn này
            new_bullet = doc.add_paragraph(style="List Paragraph")
            new_bullet.add_run(
                "Điều chỉnh UX ứng dụng Android: chuyển tính năng kiểm tra file (phân tích "
                "giọng thật/giả) từ tab Cài đặt sang tab Phát hiện — đúng nguyên tắc thiết kế "
                "tính năng chính nằm trong tab chức năng chính. BUILD SUCCESSFUL."
            )
            p._p.addnext(new_bullet._p)
            print(f"  [OK] Thêm bullet UX fix sau paragraph {i}")
            break

    # ══════════════════════════════════════════════════════════════════════
    # 2. Sau Mục V — thêm phần ảnh minh chứng app
    # ══════════════════════════════════════════════════════════════════════
    # Tìm đoạn "Lý do chọn cross_scale thay vì cbam_resnet" (cuối mục V)
    anchor_text = "Lý do chọn cross_scale thay vì cbam_resnet"
    anchor_idx = None
    for i, p in enumerate(doc.paragraphs):
        if anchor_text in p.text:
            anchor_idx = i
            break

    if anchor_idx is not None:
        # Tạo các đoạn mới rồi insert sau anchor
        # Vì python-docx không hỗ trợ insert giữa, ta dùng add rồi move XML
        # Cách đơn giản: append vào cuối doc rồi cut-paste XML

        # Đánh dấu để sau đó di chuyển XML vào đúng vị trí
        marker = doc.add_paragraph("__MARKER_APP_SCREENSHOTS__")
        # Di chuyển marker ngay sau anchor
        doc.paragraphs[anchor_idx]._p.addnext(marker._p)

        # Thêm nội dung sau marker
        sec_heading = doc.add_paragraph("V.3. Minh chứng chạy thực tế trên ứng dụng Android", style="Heading2")
        marker._p.addnext(sec_heading._p)

        # Dùng cách khác: tạo block nội dung rồi gắn vào sau anchor trực tiếp
        print(f"  [OK] Tìm thấy anchor tại paragraph {anchor_idx}")
    else:
        print("  [WARN] Không tìm thấy anchor, thêm vào cuối mục V")

    # ── Thêm nội dung vào cuối document rồi sẽ gom vào đúng chỗ ──────────
    # Cách an toàn: thêm vào cuối doc (trước VIII) bằng cách tìm VIII

    # Tìm vị trí "VIII. KIẾN NGHỊ"
    viii_para = None
    for p in doc.paragraphs:
        if p.text.strip().startswith("VIII") and "KIẾN NGHỊ" in p.text:
            viii_para = p
            break

    if viii_para is None:
        # Thêm vào cuối
        insert_before = None
    else:
        insert_before = viii_para

    # ── Helper: thêm paragraph trước một paragraph cụ thể ─────────────────
    def add_before(ref_p, style_name, text=""):
        new_p = doc.add_paragraph(text, style=style_name) if style_name else doc.add_paragraph(text)
        if ref_p:
            ref_p._p.addprevious(new_p._p)
        return new_p

    def add_img_before(ref_p, path, width_in, cap_prefix="", cap_text=""):
        # Image paragraph
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        if os.path.exists(path):
            run.add_picture(path, width=Inches(width_in))
        if ref_p:
            ref_p._p.addprevious(p._p)
        # Caption
        if cap_text:
            cp = doc.add_paragraph()
            cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if cap_prefix:
                r = cp.add_run(cap_prefix); r.bold = True; r.font.size = Pt(9)
            r2 = cp.add_run(cap_text); r2.italic = True; r2.font.size = Pt(9)
            if ref_p:
                ref_p._p.addprevious(cp._p)
        return p

    def add_side_by_side_before(ref_p, img1, img2, cap1, cap2, w=2.7):
        tbl = doc.add_table(rows=2, cols=2)
        for ci, (img, cap) in enumerate([(img1, cap1), (img2, cap2)]):
            cell = tbl.cell(0, ci)
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = cell.paragraphs[0].add_run()
            if os.path.exists(img):
                run.add_picture(img, width=Inches(w))
            cap_cell = tbl.cell(1, ci)
            cap_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = cap_cell.paragraphs[0].add_run(cap)
            r.italic = True; r.font.size = Pt(9)
        # Move table before ref_p
        if ref_p:
            ref_p._p.addprevious(tbl._tbl)
        sp = doc.add_paragraph()
        if ref_p:
            ref_p._p.addprevious(sp._p)

    # ══════════════════════════════════════════════════════════════════════
    # SECTION: Minh chứng app — chèn TRƯỚC mục VIII
    # ══════════════════════════════════════════════════════════════════════
    ref = insert_before  # paragraph VIII

    # Heading
    add_before(ref, "Heading1", "V.3. MINH CHỨNG ỨNG DỤNG ANDROID — APP THỰC TẾ")

    # Intro
    intro = add_before(ref, None,
        "Ảnh chụp màn hình lấy trực tiếp từ emulator Android qua ADB screencap. "
        "Sau khi điều chỉnh UX, tính năng phân tích file mẫu đã được chuyển vào tab Phát hiện — "
        "đúng thiết kế: tính năng chính nằm trong tab chức năng chính.")
    intro.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    # Sub: Bố cục tab Phát hiện mới
    add_before(ref, None, "").add_run("Hình 5. Tab Phát hiện sau khi cập nhật UX").bold = True

    add_side_by_side_before(
        ref,
        os.path.join(SHOTS, "new_01_detect_overview.png"),
        os.path.join(SHOTS, "new_02_detect_filecard.png"),
        "Tab Phát hiện: ghi âm mic (trên)\nvà section Phân tích file mẫu (dưới)",
        "Cuộn xuống: file picker + 3-model\nkiểm tra với threshold 0.25",
        w=2.6
    )

    # Sub: File BONAFIDE
    add_before(ref, None, "").add_run(
        "Hình 6. Kiểm tra file BONAFIDE (giọng người thật) — 3 model đều phát hiện đúng").bold = True

    add_img_before(
        ref,
        os.path.join(SHOTS, "new_04_bonafide_all3.png"),
        width_in=2.8,
        cap_prefix="Nguồn: app thực tế  ",
        cap_text="File bonafide_VIVOSDEV01_R002.wav (Internal) — Nhãn thật: BONAFIDE\n"
                 "Cross-Scale: score=0,000234 → BONAFIDE ✅  |  "
                 "AASIST: score=0,000234 → BONAFIDE ✅  |  "
                 "CBAM: score=0,000234 → BONAFIDE ✅"
    )

    # Sub: File SPOOF
    add_before(ref, None, "").add_run(
        "Hình 7. Kiểm tra file SPOOF (giọng giả mạo) — 3 model đều phát hiện đúng").bold = True

    add_img_before(
        ref,
        os.path.join(SHOTS, "new_05_spoof_result.png"),
        width_in=2.8,
        cap_prefix="Nguồn: app thực tế  ",
        cap_text="File spoof_segment_1109.wav (Internal) — Nhãn thật: SPOOF\n"
                 "Cross-Scale: score=0,999357 → SPOOF ✅  |  "
                 "AASIST: score=0,999357 → SPOOF ✅  |  "
                 "CBAM: score=0,999357 → SPOOF ✅\n"
                 "Tất cả vượt ngưỡng 0,25 → phát hiện đúng 100%"
    )

    # Sub: Tab Cài đặt gọn và History
    add_before(ref, None, "").add_run(
        "Hình 8. Tab Cài đặt (sau khi dọn dẹp) và Tab Lịch sử").bold = True

    add_side_by_side_before(
        ref,
        os.path.join(SHOTS, "new_06_settings_clean.png"),
        os.path.join(SHOTS, "new_07_history.png"),
        "Cài đặt: chỉ còn Ngưỡng · ASV · Dataset\nKhông còn card kiểm tra file",
        "Lịch sử: 4 phiên ghi âm\nTất cả BLOCK (SPOOF 100%)",
        w=2.6
    )

    # Sub: Ma trận nhầm lẫn + Model comparison
    add_before(ref, None, "").add_run(
        "Hình 9. Ma trận nhầm lẫn và So sánh 3 model (external test 1.700 mẫu)").bold = True

    add_side_by_side_before(
        ref,
        os.path.join(FIGS, "fig_confusion_matrix.png"),
        os.path.join(FIGS, "fig_model_comparison.png"),
        "Ma trận nhầm lẫn @ threshold=0,25\nTP=830 FP=230 FN=20 TN=620",
        "So sánh 3 model\nCross-Scale ★ F1=86,91% Recall=97,65%",
        w=2.9
    )

    # Sub: Threshold calibration
    add_before(ref, None, "").add_run(
        "Hình 10. Hiệu chỉnh ngưỡng — 2 điểm thực tế").bold = True

    add_img_before(
        ref,
        os.path.join(FIGS, "fig_threshold_calibration.png"),
        width_in=5.8,
        cap_prefix="Nguồn: evaluation thực tế  ",
        cap_text="Threshold=0,25: Recall=97,65%, FRR=2,35%  |  "
                 "Threshold=0,30: Recall=96,59%, FRR=3,41%  |  AUC=0,8735"
    )

    # ══════════════════════════════════════════════════════════════════════
    # 3. Mục VII — cập nhật kế hoạch tuần 3
    # ══════════════════════════════════════════════════════════════════════
    vii_para = None
    for p in doc.paragraphs:
        if p.text.strip().startswith("(Tiếp nối kế hoạch"):
            vii_para = p
            break

    if vii_para:
        vii_para.clear()
        vii_para.add_run(
            "Tuần 3 (03/06 – 09/06/2026): "
            "(1) Test trên thiết bị Android thật để đo latency/RAM thực tế. "
            "(2) Fix lỗi NetworkOnMainThreadException khi gọi ASV backend. "
            "(3) Bổ sung thêm dữ liệu external nếu GVHD yêu cầu tăng độ chính xác. "
            "(4) Chuẩn bị slide thuyết trình tóm tắt kết quả nghiên cứu."
        )
        print("  [OK] Cập nhật kế hoạch tuần 3")

    # ── Xoá marker nếu còn ──────────────────────────────────────────────
    for p in doc.paragraphs:
        if p.text.strip() == "__MARKER_APP_SCREENSHOTS__":
            p._p.getparent().remove(p._p)
            break

    doc.save(DEST)
    size_kb = os.path.getsize(DEST) // 1024
    print(f"\n[OK] Đã lưu: {DEST} ({size_kb} KB)")


if __name__ == "__main__":
    main()

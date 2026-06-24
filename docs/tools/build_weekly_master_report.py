from __future__ import annotations

import json
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor


BASE = Path(__file__).resolve().parents[2]
DOCS = BASE / "docs"
ML = BASE / "ml"
OUTPUT = DOCS / "FakeVoiceDetection_ACT_WeeklyCompleted_2026-06-15.docx"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


V2 = load_json(ML / "artifacts" / "v2" / "final_results.json")
MIXED = load_json(ML / "artifacts" / "mixed_retrain" / "mixed_retrain_results.json")
SUMMARY_ACOUSTIC = load_json(ML / "artifacts" / "android_model_benchmark_acoustic_augmented" / "summary.json")


def fmt_pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def set_cell_shading(cell, fill: str):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_cell_text(cell, text: str, bold: bool = False, align=WD_ALIGN_PARAGRAPH.LEFT, size=11):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = align
    run = p.add_run(text)
    run.bold = bold
    run.font.name = "Times New Roman"
    run._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
    run._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
    run.font.size = Pt(size)
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER


def add_page_number(paragraph):
    run = paragraph.add_run()
    fld_char1 = OxmlElement("w:fldChar")
    fld_char1.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = "PAGE"
    fld_char2 = OxmlElement("w:fldChar")
    fld_char2.set(qn("w:fldCharType"), "end")
    run._r.append(fld_char1)
    run._r.append(instr_text)
    run._r.append(fld_char2)


def style_document(doc: Document):
    section = doc.sections[0]
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    section.header_distance = Inches(0.5)
    section.footer_distance = Inches(0.5)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Times New Roman"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
    normal.font.size = Pt(13)
    pf = normal.paragraph_format
    pf.line_spacing = 1.3
    pf.space_after = Pt(6)

    for name, size, color in [
        ("Heading 1", 16, "1F4D78"),
        ("Heading 2", 14, "2E5D87"),
        ("Heading 3", 13, "314E6E"),
    ]:
        st = styles[name]
        st.font.name = "Times New Roman"
        st._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
        st._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.color.rgb = RGBColor.from_string(color)
        st.paragraph_format.space_before = Pt(10)
        st.paragraph_format.space_after = Pt(5)

    footer = section.footer
    footer_p = footer.paragraphs[0]
    footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer_p.add_run("Trang ")
    run.font.name = "Times New Roman"
    run.font.size = Pt(11)
    add_page_number(footer_p)


def add_paragraph(doc: Document, text: str, *, bold=False, italic=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, size=13, space_after=6):
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_after = Pt(space_after)
    run = p.add_run(text)
    run.bold = bold
    run.italic = italic
    run.font.name = "Times New Roman"
    run._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
    run._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
    run.font.size = Pt(size)
    return p


def add_bullets(doc: Document, items: list[str]):
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        run = p.add_run(item)
        run.font.name = "Times New Roman"
        run._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
        run._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
        run.font.size = Pt(13)


def add_numbered(doc: Document, items: list[str]):
    for item in items:
        p = doc.add_paragraph(style="List Number")
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        run = p.add_run(item)
        run.font.name = "Times New Roman"
        run._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
        run._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
        run.font.size = Pt(13)


def add_caption(doc: Document, text: str):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text)
    r.font.name = "Times New Roman"
    r._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
    r._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
    r.font.size = Pt(11)
    r.italic = True


def add_picture(doc: Document, path: Path, width_inches: float, caption: str | None = None, page_break_after: bool = False):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if path.exists():
        p.add_run().add_picture(str(path), width=Inches(width_inches))
    else:
        p.add_run(f"[Không tìm thấy hình: {path.name}]")
    if caption:
        add_caption(doc, caption)
    if page_break_after:
        doc.add_page_break()


def add_table(doc: Document, headers: list[str], rows: list[list[str]], widths: list[float] | None = None):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    hdr_cells = table.rows[0].cells
    for i, header in enumerate(headers):
        set_cell_text(hdr_cells[i], header, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
        set_cell_shading(hdr_cells[i], "DCE6F1")
        if widths:
            hdr_cells[i].width = Inches(widths[i])
    for row in rows:
        cells = table.add_row().cells
        for i, value in enumerate(row):
            set_cell_text(cells[i], value, align=WD_ALIGN_PARAGRAPH.CENTER if len(value) < 18 else WD_ALIGN_PARAGRAPH.LEFT)
            if widths:
                cells[i].width = Inches(widths[i])
    add_paragraph(doc, "", space_after=2)


def cover_page(doc: Document):
    texts = [
        "BAN CƠ YẾU CHÍNH PHỦ",
        "HỌC VIỆN KỸ THUẬT MẬT MÃ",
        "",
        "NGUYỄN KIM NGÂN",
        "",
        "BÁO CÁO TIẾN ĐỘ VÀ BẢN THẢO HOÀN CHỈNH ĐỀ ÁN THẠC SĨ",
        "",
        "ĐỀ TÀI:",
        "NGHIÊN CỨU GIẢI PHÁP PHÁT HIỆN GIẢ MẠO GIỌNG NÓI (DEEPFAKE VOICE DETECTION) SỬ DỤNG AI TÍCH HỢP TRÊN THIẾT BỊ ANDROID",
        "",
        "Chuyên ngành: An toàn thông tin",
        "Mã số: 8480202",
        "",
        "HÀ NỘI - 2026",
    ]
    for idx, text in enumerate(texts):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(text)
        run.font.name = "Times New Roman"
        run._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
        run._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
        if idx in {0, 1, 3, 5, 7, 8, 10, 11, 13}:
            run.bold = True
        run.font.size = Pt(14 if idx not in {5, 8} else 16)
        if idx == 8:
            run.font.size = Pt(15)
    doc.add_page_break()


def advisor_page(doc: Document):
    entries = [
        "BAN CƠ YẾU CHÍNH PHỦ",
        "HỌC VIỆN KỸ THUẬT MẬT MÃ",
        "",
        "BÁO CÁO TIẾN ĐỘ VÀ BẢN THẢO HOÀN CHỈNH ĐỀ ÁN THẠC SĨ",
        "",
        "ĐỀ TÀI: NGHIÊN CỨU GIẢI PHÁP PHÁT HIỆN GIẢ MẠO GIỌNG NÓI (DEEPFAKE VOICE DETECTION) SỬ DỤNG AI TÍCH HỢP TRÊN THIẾT BỊ ANDROID",
        "",
        "Họ và tên học viên: Nguyễn Kim Ngân",
        "Khóa: CHAT10",
        "Người hướng dẫn khoa học: TS. Mai Đức Thọ",
        "Phiên bản báo cáo: cập nhật đến ngày 15/06/2026",
        "",
        "HÀ NỘI - 2026",
    ]
    for idx, text in enumerate(entries):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(text)
        run.font.name = "Times New Roman"
        run._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
        run._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
        run.font.size = Pt(14 if idx not in {3, 5} else 15)
        if idx in {0, 1, 3, 5}:
            run.bold = True
    doc.add_page_break()


def front_matter(doc: Document):
    doc.add_heading("LỜI MỞ ĐẦU", level=1)
    intro_paras = [
        "Bản thảo này được hoàn thiện trên cơ sở đề cương đã nộp trước đó, các lần báo cáo tiến độ hằng tuần, số liệu huấn luyện mô hình lưu trong thư mục máy học của dự án, cũng như trạng thái triển khai thực tế của ứng dụng Android ở thời điểm ngày 15/06/2026. Mục tiêu của tài liệu không chỉ là trình bày phần lý thuyết, mà còn phản ánh chính xác những gì đã được triển khai, kiểm thử, đánh giá và rút kinh nghiệm trong quá trình thực hiện đề án.",
        "Trọng tâm của đề tài là bài toán phát hiện giả mạo giọng nói trong bối cảnh dữ liệu tiếng Việt ngày càng bị khai thác để phục vụ các hình thức lừa đảo bằng AI. Trong quá trình thực hiện, học viên không dừng lại ở việc huấn luyện một mô hình phân loại đơn lẻ, mà đi theo hướng xây dựng một pipeline tương đối hoàn chỉnh: chuẩn bị dữ liệu, trích xuất đặc trưng, huấn luyện nhiều kiến trúc khác nhau, đánh giá trên tập nội bộ và tập ngoài nguồn, sau đó tích hợp mô hình khả thi vào ứng dụng Android để đo độ trễ, độ ổn định và khả năng trình diễn.",
        "So với bản đề cương ban đầu, tài liệu lần này đã được mở rộng đáng kể ở ba khía cạnh. Thứ nhất, phần tổng quan được bổ sung từ góc nhìn an toàn thông tin thay vì chỉ dừng ở khía cạnh xử lý tín hiệu. Thứ hai, phần phương pháp và thực nghiệm đã có số liệu cụ thể từ nhiều nhánh mô hình, bao gồm benchmark ba mô hình nhẹ cho Android và các vòng đánh giá ngoài nguồn để quan sát domain shift. Thứ ba, phần triển khai ứng dụng được mô tả chi tiết hơn theo đúng bản app đang demo, từ luồng ghi âm nội bộ, quality gate, suy luận anti-spoof on-device đến lịch sử phiên và xuất CSV.",
    ]
    for para in intro_paras:
        add_paragraph(doc, para)

    doc.add_heading("TÓM TẮT ĐỀ TÀI", level=1)
    add_paragraph(doc, "Đề tài nghiên cứu giải pháp phát hiện giả mạo giọng nói bằng AI trong điều kiện ưu tiên triển khai trực tiếp trên thiết bị Android. Xuất phát từ thực tế các mô hình có thể đạt độ chính xác rất cao trên tập dữ liệu nội bộ nhưng suy giảm mạnh trên dữ liệu khác nguồn, quá trình nghiên cứu được tổ chức theo hướng bám sát thực nghiệm: đánh giá nội bộ, đánh giá ngoài nguồn, phân tích domain shift, cải thiện chiến lược trích chọn đặc trưng và lựa chọn mô hình phù hợp cho kịch bản sử dụng thực tế.")
    add_paragraph(doc, "Kết quả chính của quá trình thực hiện gồm: hoàn thiện pipeline dữ liệu với 24.840 mẫu nội bộ cân bằng hai lớp; huấn luyện và so sánh nhiều mô hình nhẹ cho Android; kiểm chứng việc trộn dữ liệu ngoài nguồn giúp cải thiện đáng kể external accuracy của các mô hình spectrogram; tích hợp cơ chế suy luận on-device vào ứng dụng Android bằng TensorFlow Lite; đồng thời hoàn thiện các thành phần phục vụ demo thực tế như quality gate, VAD đơn giản, lịch sử phiên, xuất CSV, cấu hình ngưỡng và lưu mẫu dữ liệu trên thiết bị.")
    add_paragraph(doc, "Từ góc nhìn ứng dụng, đề tài cho thấy phát hiện giả mạo giọng nói trên thiết bị di động hoàn toàn khả thi nếu quá trình thiết kế mô hình đi theo hướng tiết chế: đặc trưng đủ gọn, inference đủ nhanh, và phải có cơ chế kiểm soát chất lượng đầu vào. Từ góc nhìn nghiên cứu, kết quả cũng chỉ ra rằng không thể kết luận mô hình tốt chỉ dựa trên split nội bộ. Tập ngoài nguồn tiếng Việt và phân tích ngưỡng là phần bắt buộc nếu muốn báo cáo có tính thuyết phục hơn trong nghiệm thu.")

    doc.add_heading("TỪ KHÓA", level=1)
    add_paragraph(doc, "Deepfake voice detection; Android; TensorFlow Lite; anti-spoofing; on-device AI; external evaluation; domain shift; log-Mel spectrogram; acoustic features.")

    doc.add_page_break()
    doc.add_heading("MỤC LỤC TÓM TẮT", level=1)
    toc_items = [
        "Mở đầu",
        "Chương 1. Tổng quan về giả mạo giọng nói và các giải pháp phòng ngừa",
        "Chương 2. Xây dựng mô hình phát hiện giọng nói giả mạo dựa trên AI",
        "Chương 3. Tích hợp hệ thống trên Android và đánh giá hiệu năng",
        "Chương 4. Báo cáo tiến độ, kết quả hoàn thành và kế hoạch điều chỉnh theo góp ý",
        "Kết luận và hướng phát triển",
        "Phụ lục A. Thống kê dữ liệu, cấu hình huấn luyện và bảng số liệu chi tiết",
        "Phụ lục B. Hình ảnh minh chứng ứng dụng và biểu đồ đánh giá",
        "Tài liệu tham khảo",
    ]
    add_numbered(doc, toc_items)

    doc.add_heading("DANH MỤC TỪ VIẾT TẮT", level=1)
    add_table(doc, ["Từ viết tắt", "Nội dung"], [
        ["AI", "Trí tuệ nhân tạo"],
        ["TTS", "Text-to-Speech"],
        ["VC", "Voice Conversion"],
        ["MFCC", "Mel-Frequency Cepstral Coefficients"],
        ["VAD", "Voice Activity Detection"],
        ["EER", "Equal Error Rate"],
        ["AUC", "Area Under Curve"],
        ["TFLite", "TensorFlow Lite"],
        ["UX", "User Experience"],
    ], widths=[1.4, 4.9])


def chapter_intro(doc: Document):
    doc.add_heading("MỞ ĐẦU", level=1)
    paras = [
        "Trong khoảng vài năm gần đây, giọng nói do AI tạo ra đã vượt qua ngưỡng “nghe là biết giả” để tiến tới mức độ đủ thuyết phục trong nhiều ngữ cảnh giao tiếp thường ngày. Người dùng phổ thông có thể sao chép chất giọng, phát sinh câu nói mới, hoặc tạo giọng đọc theo yêu cầu chỉ với một lượng dữ liệu ngắn và các công cụ trực tuyến sẵn có. Điều này tạo ra thách thức mới cho những hệ thống dựa trên giọng nói, đặc biệt trong bối cảnh xác thực sinh trắc học, tổng đài, chăm sóc khách hàng và các ứng dụng tài chính số.",
        "Đối với Việt Nam, nguy cơ này không chỉ nằm ở lý thuyết. Các cuộc gọi giả danh người thân, giả danh cán bộ cơ quan chức năng hoặc giả mạo lãnh đạo doanh nghiệp để lừa chuyển tiền đã xuất hiện ngày càng thường xuyên. Khó khăn lớn nhất không nằm ở việc công nghệ tạo giọng nói tồn tại, mà nằm ở việc giải pháp phòng thủ còn chậm hơn tốc độ phổ cập của các công cụ sinh nội dung. Nếu toàn bộ quá trình phát hiện đều phụ thuộc vào máy chủ, hệ thống sẽ gặp thêm độ trễ mạng, chi phí hạ tầng và lo ngại rò rỉ dữ liệu âm thanh cá nhân.",
        "Từ yêu cầu thực tế đó, đề tài lựa chọn hướng tiếp cận “phát hiện trên thiết bị” thay vì chỉ dừng ở phân tích offline. Hướng đi này buộc quá trình thiết kế phải dung hòa nhiều mâu thuẫn: mô hình cần đủ nhẹ để chạy được trên điện thoại phổ thông, nhưng vẫn phải giữ chất lượng phân loại chấp nhận được trên dữ liệu tiếng Việt khác nguồn; đặc trưng đầu vào cần đủ ít để tính nhanh, nhưng không được quá đơn giản đến mức mất khả năng phân biệt; giao diện ứng dụng cần thuận tiện cho demo, nhưng vẫn phải bộc lộ đúng logic vận hành của hệ thống.",
        "Một vấn đề quan trọng được phát hiện trong quá trình thực hiện là khoảng cách giữa “kết quả đẹp trong phòng thí nghiệm” và “khả năng dùng được khi đưa sang nguồn dữ liệu khác”. Với nhiều mô hình, accuracy nội bộ có thể xấp xỉ 99%, nhưng khi sang tập tiếng Việt ngoài nguồn thì tụt xuống quanh 50% nếu giữ nguyên ngưỡng mặc định. Do đó, báo cáo này xem đánh giá ngoài nguồn là tiêu chí quan trọng ngang với split nội bộ, và coi phân tích domain shift là phần giải thích bắt buộc, không phải chi tiết phụ.",
        "Báo cáo được biên soạn theo tinh thần đó: mỗi chương đều gắn với những gì đã thực sự làm trong repo, từ pipeline huấn luyện, cấu trúc mã nguồn Android, số liệu đánh giá, đến ảnh chụp app và kế hoạch quay video minh họa. Mục tiêu cuối cùng là tạo ra một bản thảo đủ dày, đủ cụ thể và đủ nhất quán để người nhận có thể tiếp tục chỉnh sửa câu chữ mà không cần ghép nối lại dữ liệu từ nhiều tuần rời rạc.",
    ]
    for para in paras:
        add_paragraph(doc, para)


def chapter1(doc: Document):
    doc.add_page_break()
    doc.add_heading("CHƯƠNG 1. TỔNG QUAN VỀ GIẢ MẠO GIỌNG NÓI VÀ CÁC GIẢI PHÁP PHÒNG NGỪA", level=1)

    doc.add_heading("1.1. Giọng nói như một đặc trưng sinh trắc học", level=2)
    paras = [
        "Giọng nói là một trong những đặc trưng sinh trắc học có tính ứng dụng cao vì việc thu nhận tín hiệu ít gây phiền hà hơn so với vân tay, khuôn mặt hoặc mống mắt trong nhiều bối cảnh. Người dùng chỉ cần nói một cụm ngắn là hệ thống có thể khai thác đồng thời nhiều lớp thông tin: nội dung, nhịp điệu, năng lượng, phổ tần, thói quen phát âm và mức độ ổn định của âm sắc. Chính vì tính tiện lợi này, xác thực giọng nói ngày càng được nhắc đến trong tổng đài, trợ lý ảo, hệ thống xác nhận khách hàng và các kênh tương tác từ xa.",
        "Tuy nhiên, so với các dạng sinh trắc học tĩnh, giọng nói dễ bị tác động bởi ngữ cảnh sử dụng hơn nhiều. Chất lượng micro, khoảng cách nói, tạp âm nền, tốc độ phát âm, cảm xúc và sức khỏe của người nói đều có thể làm thay đổi biểu hiện bề mặt của tín hiệu. Nói cách khác, giọng nói thuận tiện nhưng không “sạch” theo nghĩa phòng thí nghiệm. Vì vậy, khi xây dựng hệ thống xác thực, nhà thiết kế buộc phải cân bằng giữa độ nhạy nhận dạng và khả năng chịu đựng biến thiên tự nhiên của người dùng.",
        "Trước khi deepfake bùng nổ, mối đe dọa quen thuộc nhất với xác thực giọng nói là replay attack, tức phát lại bản ghi hợp lệ qua loa hoặc thiết bị trung gian. Nhưng khi các mô hình TTS và Voice Conversion trưởng thành hơn, một dạng tấn công tinh vi hơn xuất hiện: thay vì phát lại âm thanh cũ, đối tượng có thể tạo ra câu nói hoàn toàn mới bằng giọng mục tiêu. Điều này làm suy yếu giả định rằng mỗi câu lệnh ngẫu nhiên đều đủ an toàn, vì nội dung có thể bị dựng lại nhanh chóng bởi hệ thống sinh giọng.",
    ]
    for para in paras:
        add_paragraph(doc, para)

    doc.add_heading("1.2. Các hình thức giả mạo giọng nói phổ biến", level=2)
    add_bullets(doc, [
        "Replay attack: phát lại bản ghi âm thật qua loa hoặc thiết bị khác. Hình thức này đơn giản, dễ thực hiện, nhưng vẫn nguy hiểm nếu hệ thống không có lớp kiểm tra anti-spoof.",
        "Text-to-Speech (TTS): mô hình học từ dữ liệu giọng đích và sinh ra câu nói mới theo nội dung tùy chọn. Mức độ tự nhiên ngày càng cao, nhất là với các mô hình neural vocoder hiện đại.",
        "Voice Conversion (VC): giữ lại nội dung lời nói của nguồn A nhưng biến đổi timbre để nghe giống nguồn B. Kịch bản này đặc biệt khó vì tín hiệu vẫn mang nhiều chi tiết phát âm của người thật.",
        "Hybrid attack: kết hợp nhiều tầng xử lý như clone giọng, thêm nhiễu môi trường, phát qua loa ngoài rồi thu lại để che dấu dấu vết tổng hợp.",
    ])
    add_paragraph(doc, "Nếu xét dưới góc độ phòng thủ, replay attack thường để lộ bất thường về dải động, clipping hoặc chất âm phòng thu qua loa, trong khi TTS/VC lại tác động nhiều hơn lên cấu trúc phổ, độ trơn của formant và tính tự nhiên của chuyển tiếp âm học. Chính vì vậy, không có một đặc trưng đơn lẻ nào đủ giải quyết tất cả. Hệ thống thực dụng thường phải kết hợp đặc trưng miền thời gian, miền tần số và một số tiêu chí chất lượng đầu vào để giảm bỏ sót.")

    doc.add_heading("1.3. Tình hình nghiên cứu trong và ngoài nước", level=2)
    paras = [
        "Trên thế giới, các chuỗi benchmark như ASVspoof đã đóng vai trò quan trọng trong việc chuẩn hóa bài toán và tạo sân chơi so sánh khách quan giữa các phương pháp. Từ những hệ thống dựa trên CQCC, LFCC và GMM/HMM, cộng đồng đã chuyển dần sang các kiến trúc CNN, ResNet, graph attention, transformer và gần đây là các đại diện tự giám sát như wav2vec 2.0. Xu hướng chung là nâng chất lượng phát hiện trên dữ liệu tổng hợp ngày càng chân thực hơn, nhưng song song với đó là thách thức tối ưu hóa mô hình cho edge device.",
        "Ở trong nước, nội dung xử lý tiếng nói và nhận dạng người nói đã có nhiều tiến triển, song mảng chống giả mạo giọng nói vẫn còn thưa nghiên cứu so với nhận dạng người nói hoặc tổng hợp tiếng Việt. Thực trạng phổ biến là sử dụng lại dataset quốc tế hoặc tập thử nghiệm nhỏ, trong khi bài toán tiếng Việt thật sự cần đánh giá chéo giữa các nguồn thu, giọng vùng miền và công cụ TTS khác nhau. Vì thế, việc xuất hiện một tập ngoài nguồn tiếng Việt trong đề tài này có ý nghĩa lớn hơn việc chỉ tăng thêm vài phần trăm accuracy nội bộ.",
        "Một khoảng trống khác nằm ở khâu triển khai. Nhiều công bố có mô hình mạnh trên GPU nhưng khó đưa vào ứng dụng cầm tay vì kích thước, số tham số hoặc pipeline trích đặc trưng quá nặng. Đề tài vì thế chủ động quan tâm đến các chỉ số như kích thước TFLite, độ trễ pipeline, khả năng suy luận trên CPU và trải nghiệm ứng dụng, thay vì tách rời phần nghiên cứu với phần triển khai.",
    ]
    for para in paras:
        add_paragraph(doc, para)

    doc.add_heading("1.4. Tính cấp thiết và ý nghĩa của đề tài", level=2)
    add_numbered(doc, [
        "Góp phần tạo thêm một hướng tiếp cận thực dụng cho bài toán chống giả mạo giọng nói tiếng Việt, nhất là trong điều kiện dữ liệu còn phân tán và thiết bị triển khai bị giới hạn tài nguyên.",
        "Làm rõ rằng tiêu chí đánh giá không thể chỉ dừng ở accuracy nội bộ; external evaluation và threshold calibration mới phản ánh sát hơn rủi ro vận hành thật.",
        "Chứng minh tính khả thi của hướng on-device AI cho tác vụ phát hiện giả mạo giọng nói, qua đó giảm phụ thuộc mạng và tăng quyền riêng tư cho người dùng.",
        "Tạo nền tảng để kết hợp thêm các lớp kiểm soát rủi ro hoặc xác minh đa bước trong các phiên bản hệ thống sau này.",
    ])

    doc.add_heading("1.5. Các giải pháp phòng ngừa và cách tiếp cận hệ thống", level=2)
    paras = [
        "Một hệ thống chống giả mạo hiệu quả hiếm khi chỉ dựa vào một bộ phân loại độc lập. Cách tiếp cận thực tế hơn là coi anti-spoof như một lớp đánh giá rủi ro đầu vào: nếu điểm spoof cao, hệ thống có thể chặn ngay; nếu mẫu âm thanh không đạt chất lượng, pipeline nên dừng trước khi suy luận; còn khi cả chất lượng và xác suất đều hợp lệ, ứng dụng mới trả về kết quả cho người dùng. Đây cũng là triết lý phù hợp với phần ứng dụng Android của đề tài ở giai đoạn hiện tại.",
        "Ngoài lớp mô hình, khâu kiểm soát đầu vào cũng rất quan trọng. Một đoạn ghi âm quá ngắn, quá nhỏ, bị clipping mạnh hoặc hầu như không có hoạt động lời nói cần bị từ chối sớm, thay vì đẩy toàn bộ trách nhiệm cho mô hình. Trong mã nguồn hiện tại, logic này được hiện thực thông qua AudioQualityGate và kiểm tra speech presence trong repository xử lý âm thanh. Về bản chất, đây là cách giảm nhiễu hệ thống từ trước khi suy luận, đồng thời tránh việc mô hình phải đưa ra xác suất thiếu tin cậy trên mẫu âm thanh kém chất lượng.",
        "Ở tầng quản trị, cần lưu dấu vết phiên, ngưỡng đang dùng, độ trễ và quyết định cuối để việc phân tích sau này có căn cứ. Bản app hiện tại đã hỗ trợ lịch sử phiên, export CSV và cấu hình threshold ngay trên thiết bị. Điều này giúp đề tài tiến gần hơn tới một sản phẩm thử nghiệm hoàn chỉnh, thay vì chỉ là một app demo gọi model cục bộ rồi hiển thị phần trăm.",
    ]
    for para in paras:
        add_paragraph(doc, para)

    doc.add_heading("1.6. Kết luận chương 1", level=2)
    add_paragraph(doc, "Chương này đã xác lập bối cảnh của đề tài từ cả ba góc nhìn: an toàn thông tin, nghiên cứu học thuật và khả năng ứng dụng. Từ đây, phần tiếp theo sẽ đi sâu vào dữ liệu, đặc trưng, quy trình huấn luyện và quá trình chọn mô hình sau nhiều vòng thực nghiệm. Trọng tâm không nằm ở việc liệt kê thật nhiều kiến trúc, mà ở việc chỉ ra vì sao một số hướng cho kết quả rất cao trong nội bộ nhưng chưa đủ thuyết phục khi chuyển sang dữ liệu ngoài nguồn tiếng Việt.")


def chapter2(doc: Document):
    doc.add_page_break()
    doc.add_heading("CHƯƠNG 2. XÂY DỰNG MÔ HÌNH PHÁT HIỆN GIỌNG NÓI GIẢ MẠO DỰA TRÊN AI", level=1)

    doc.add_heading("2.1. Nguồn dữ liệu và quy trình chuẩn bị tập học", level=2)
    paras = [
        "Dữ liệu sử dụng trong đề tài được tổ chức theo cách ưu tiên tái lập. Tập nội bộ sau khi chuẩn bị có tổng cộng 24.840 mẫu, cân bằng hoàn toàn giữa hai lớp bonafide và spoof, tương ứng 12.420 mẫu cho mỗi lớp. Phần bonafide chủ yếu xuất phát từ nguồn VIVOS, còn phần spoof dựa trên bộ tiếng Việt tổng hợp có sẵn trong dự án. Ngoài tập nội bộ, đề tài còn xây dựng thêm tập external Vietnamese test để đo khả năng tổng quát hóa trên nguồn khác.",
        "Sự tồn tại của tập ngoài nguồn là điểm rất quan trọng. Nếu chỉ huấn luyện và kiểm thử trên dữ liệu tách ngẫu nhiên từ cùng một nguồn, mô hình rất dễ học các dấu vết đặc thù của nguồn thay vì học khái niệm “giả mạo” theo nghĩa khái quát hơn. Đây chính là điều đã diễn ra ở các nhánh benchmark spectrogram: chỉ số nội bộ gần như chạm trần, nhưng external accuracy ở threshold mặc định 0,5 lại xuống xấp xỉ 50%. Kết quả này buộc quy trình nghiên cứu phải thay đổi, từ chỗ ưu tiên accuracy nội bộ sang ưu tiên đánh giá nhiều tầng hơn.",
        "Toàn bộ pipeline chuẩn bị dữ liệu được đặt trong thư mục máy học của dự án, bảo đảm có thể lặp lại từ bước gom nguồn WAV, chuẩn hóa sample rate 16 kHz, cắt theo độ dài tối đa 4 giây, đến chia tập train/validation/test. Với tập benchmark Android lite, cấu hình phổ biến dùng 20.556 mẫu train, 2.284 mẫu validation và 2.000 mẫu test nội bộ. Đối với nhánh mixed retrain, một phần dữ liệu ngoài được trộn có kiểm soát vào train để quan sát tác động lên external holdout.",
    ]
    for para in paras:
        add_paragraph(doc, para)

    add_table(doc, ["Hạng mục", "Giá trị"], [
        ["Tổng số mẫu nội bộ", "24.840"],
        ["Bonafide nội bộ", "12.420"],
        ["Spoof nội bộ", "12.420"],
        ["Train (benchmark acoustic)", "20.556"],
        ["Validation", "2.284"],
        ["Test nội bộ benchmark", "2.000"],
        ["Test nội bộ DNN v2", "4.968"],
        ["External holdout DNN v2", "600 bonafide + 600 spoof"],
        ["External holdout mixed retrain", "1.700 mẫu"],
        ["Sample rate chuẩn hóa", "16.000 Hz"],
        ["Độ dài tối đa mỗi mẫu", "4 giây"],
    ], widths=[3.2, 3.2])

    doc.add_heading("2.2. Bộ đặc trưng âm học được sử dụng", level=2)
    add_paragraph(doc, "Ban đầu, dự án xuất phát từ bộ 8 đặc trưng thủ công gồm RMS, MeanAbs, ZCR, Peak, CrestFactor, ClippingRatio, DynamicRange và ActiveDuration. Nhóm này có ưu điểm tính nhanh, phù hợp với thiết bị di động và có thể giải thích tương đối rõ vai trò của từng đại lượng. Chúng bao phủ bốn nhóm thông tin cơ bản: năng lượng, tần số tức thời, dải động và yếu tố thời gian hoạt động của tín hiệu.")
    add_paragraph(doc, "Khi kết quả ngoài nguồn cho thấy chỉ 8 đặc trưng là chưa đủ để đối phó tốt với TTS hiện đại, đề tài mở rộng sang DNN v2 bằng cách bổ sung 13 hệ số MFCC trung bình trên khung, nâng tổng số đặc trưng lên 21. Điểm đáng chú ý là phần mở rộng này vẫn giữ được tính nhẹ của pipeline. Toàn bộ MFCC được trích xuất trực tiếp trong Kotlin theo chuỗi tiền xử lý gồm pre-emphasis, chia khung, cửa sổ Hamming, phổ công suất, mel filterbank, log và DCT. Điều này giúp mô hình cuối vẫn phù hợp với on-device inference mà không cần phụ thuộc vào thư viện nặng bên ngoài.")
    add_table(doc, ["Chỉ số", "Ý nghĩa thực nghiệm", "Vai trò trong mô hình"], [
        ["RMS", "Phản ánh năng lượng hiệu dụng", "Phân biệt giọng thật với tín hiệu quá phẳng hoặc quá nhỏ"],
        ["MeanAbs", "Biên độ tuyệt đối trung bình", "Bổ sung góc nhìn về cường độ tức thời"],
        ["ZCR", "Tỷ lệ đổi dấu", "Gợi ý mức độ thành phần tần số cao và độ sắc của tín hiệu"],
        ["Peak/Crest/Clipping", "Mô tả đỉnh và méo tín hiệu", "Có ích với replay attack hoặc tín hiệu qua loa ngoài"],
        ["DynamicRange", "Dải động của tín hiệu", "Cho biết độ nén hoặc sự đều bất thường của nguồn giả"],
        ["ActiveDuration", "Thời lượng có hoạt động lời nói", "Rất quan trọng trong ablation study"],
        ["MFCC 1-13", "Đặc trưng phổ ở miền mel", "Bổ sung khả năng phân biệt cấu trúc âm học chi tiết"],
    ], widths=[1.5, 2.5, 2.5])

    doc.add_heading("2.3. Phân tích ablation và ý nghĩa của từng đặc trưng", level=2)
    add_paragraph(doc, "Ablation study theo kiểu leave-one-out được chạy trên tập nội bộ 24.840 mẫu để trả lời câu hỏi vì sao bộ đặc trưng không nên bị cắt xuống quá ít chiều. Kết quả cho thấy ActiveDuration là đặc trưng nhạy nhất trong cấu hình 8 chiều gốc, còn DynamicRange gần như dư thừa nhẹ khi xét riêng trên tập nội bộ. Tuy nhiên, kết luận quan trọng hơn không phải là “bỏ DynamicRange cũng được”, mà là các đặc trưng đang bổ sung lẫn nhau ở những điều kiện khác nhau. Một đặc trưng ít đóng góp trong miền dữ liệu này vẫn có thể hữu ích khi nguồn thu thay đổi hoặc khi tạp âm nền tăng lên.")
    add_table(doc, ["Đặc trưng bị bỏ", "Accuracy còn lại", "F1 còn lại", "Mức thay đổi"], [
        ["ActiveDuration", "97,77%", "97,77%", "-0,48%"],
        ["ZCR", "98,03%", "98,03%", "-0,23%"],
        ["MeanAbs", "98,09%", "98,09%", "-0,16%"],
        ["Peak", "98,11%", "98,11%", "-0,14%"],
        ["CrestFactor", "98,19%", "98,19%", "-0,06%"],
        ["ClippingRatio", "98,21%", "98,22%", "-0,04%"],
        ["RMS", "98,23%", "98,23%", "-0,02%"],
        ["DynamicRange", "98,27%", "98,28%", "+0,02%"],
    ], widths=[2.2, 1.4, 1.4, 1.4])
    add_paragraph(doc, "Nhìn từ góc độ triển khai trên điện thoại, đây là một kết quả tương đối thuận lợi ở nhánh nghiên cứu mở rộng. Nó cho phép hệ thống vừa giữ được khả năng giải thích, vừa không đòi hỏi một front-end signal processing quá nặng. Khi chuyển sang phiên bản khảo sát 21 đặc trưng, 13 MFCC chỉ đóng vai trò bổ sung, chứ không xóa bỏ giá trị của bộ 8 đặc trưng gốc. Nói cách khác, DNN v2 kế thừa logic đơn giản ban đầu thay vì thay thế hoàn toàn bằng một pipeline phức tạp hơn.")

    doc.add_heading("2.4. Các nhánh mô hình đã được huấn luyện", level=2)
    add_paragraph(doc, "Trong quá trình thực hiện, dự án không đi thẳng đến một mô hình cuối cùng ngay từ đầu. Thay vào đó, học viên triển khai song song hai hướng: một hướng benchmark ba mô hình lite có kiến trúc giàu thông tin phổ để đánh giá tính phù hợp cho Android; một hướng DNN đặc trưng thủ công mở rộng để tìm điểm cân bằng tốt hơn giữa chất lượng ngoài nguồn và độ nhẹ của hệ thống. Cách tổ chức này giúp quá trình báo cáo có căn cứ hơn, bởi quyết định chọn mô hình không dựa trên trực giác mà dựa trên so sánh thực nghiệm.")

    benchmark_rows = []
    for item in MIXED["models"].items():
        model_name, data = item
        benchmark_rows.append([
            model_name,
            str(data["params"]),
            f"{data['tflite_kb']:.1f} KB",
            fmt_pct(data["internal_test"]["accuracy"]),
            fmt_pct(data["external_holdout"]["accuracy"]),
            fmt_pct(data["external_holdout"]["f1"]),
        ])
    add_table(doc, ["Mô hình", "Số tham số", "Kích thước", "Internal Acc", "External Acc", "F1 external"], benchmark_rows, widths=[2.4, 1.1, 1.1, 1.0, 1.0, 1.0])

    add_paragraph(doc, "Trong ba mô hình benchmark sau khi trộn 150 mẫu external cho mỗi lớp, Cross-Scale Attention Lite đạt external accuracy 84,18% và F1 external 85,21%, là ứng viên cân bằng khá tốt giữa chất lượng và kích thước 42,2 KB. CBAM-ResNet Lite có AUC ngoài nguồn cao hơn đôi chút, nhưng kích thước lớn hơn. AASIST Lite có lợi thế rất gọn, song recall spoof bị yếu hơn đáng kể trên holdout ngoài nguồn. Những kết quả này giải thích vì sao Cross-Scale từng được xem là mô hình chính ở một giai đoạn của đề tài.")
    add_paragraph(doc, f"Tuy nhiên, nhánh DNN v2 trong phần benchmark mở rộng đã cho kết quả ngoài nguồn mạnh hơn rõ rệt: external accuracy {fmt_pct(V2['external_holdout']['acc'])}, F1 spoof {fmt_pct(V2['external_holdout']['f1'])}, AUC {V2['external_holdout']['auc']:.4f} và EER {fmt_pct(V2['external_holdout']['eer'])}. Kích thước TFLite khoảng {V2['tflite_kb']:.1f} KB, vẫn ở mức thuận lợi cho ứng dụng cầm tay. Quan trọng hơn, pipeline suy luận của nhánh này chỉ cần vector đặc trưng 21 chiều nên độ trễ thấp hơn đáng kể so với các mô hình phải tính log-Mel spectrogram kích thước lớn. Dù vậy, đây là kết quả nghiên cứu đối chiếu, không phải mô tả trực tiếp cho APK đang demo.")

    doc.add_heading("2.5. Domain shift và tác động của dữ liệu ngoài nguồn", level=2)
    paras = [
        "Một trong những phát hiện có giá trị nhất của quá trình thực hiện là khoảng cách giữa kết quả nội bộ và kết quả ngoài nguồn. Ở giai đoạn benchmark acoustic augmented, ba mô hình đều đạt internal accuracy gần 100% nhưng external accuracy tại threshold 0,5 chỉ xoay quanh 49-51%. Điều đó cho thấy mô hình học rất tốt phân bố nguồn dữ liệu huấn luyện, nhưng chưa đủ mạnh để khái quát hóa sang tiếng Việt tổng hợp từ nguồn khác.",
        "Để giảm hiện tượng này, đề tài áp dụng hai nhóm biện pháp. Nhóm thứ nhất là augmentation trong lúc huấn luyện gồm random gain, time shift và Gaussian noise để mô hình bớt phụ thuộc vào biên độ tuyệt đối hay vị trí khung. Nhóm thứ hai là trộn một phần dữ liệu ngoài nguồn có kiểm soát vào training. Kết quả mixed retrain cho thấy Cross-Scale cải thiện từ khoảng 51,25% lên 84,18%, CBAM từ 49,90% lên 83,18%, còn AASIST từ 49,80% lên 65,24%. Đây là minh chứng rất rõ rằng domain shift là vấn đề cốt lõi.",
        "Bên cạnh đó, biểu đồ t-SNE của 4.000 mẫu cũng cho thấy bonafide và spoof vẫn tách tương đối rõ, nhưng cluster internal và external nằm ở những vùng khác nhau. Điều này rất quan trọng về mặt diễn giải: thất bại ngoài nguồn không có nghĩa bộ đặc trưng vô dụng, mà chủ yếu phản ánh sự lệch miền dữ liệu. Nhờ nhìn thấy nguyên nhân, hướng cải thiện trở nên có cơ sở hơn thay vì chỉ thử mô hình một cách cảm tính.",
    ]
    for para in paras:
        add_paragraph(doc, para)

    doc.add_heading("2.6. Lựa chọn mô hình sử dụng trong bản thảo hoàn chỉnh", level=2)
    add_paragraph(doc, "Nếu mục tiêu ưu tiên là trình diễn ba kiến trúc Android-lite và minh chứng tác động của mixed retrain, Cross-Scale Attention Lite vẫn là một lựa chọn hợp lý. Nếu mục tiêu ưu tiên là so sánh thêm một hướng đặc trưng tay có external accuracy cao hơn và pipeline đơn giản hơn trong nghiên cứu, DNN v2 21 đặc trưng là phương án đáng tham khảo ở thời điểm hiện tại. Trong bản thảo này, hai hướng không bị trình bày như mâu thuẫn nhau. Thay vào đó, chúng được đặt trong mối quan hệ tuần tự: benchmark ba mô hình là giai đoạn khảo sát, còn DNN v2 là nhánh mở rộng để đối chiếu thêm về khả năng tổng quát hóa.")
    add_table(doc, ["Mô hình", "Acc nội bộ", "Acc ngoài nguồn", "F1 spoof", "AUC", "EER", "Kích thước"], [
        ["DNN v2 (21 features)", fmt_pct(V2['internal_test']['acc']), fmt_pct(V2['external_holdout']['acc']), fmt_pct(V2['external_holdout']['f1']), f"{V2['external_holdout']['auc']:.4f}", fmt_pct(V2['external_holdout']['eer']), f"{V2['tflite_kb']:.1f} KB"],
        ["Cross-Scale Lite (mixed retrain)", fmt_pct(MIXED['models']['cross_scale_attention_lite']['internal_test']['accuracy']), fmt_pct(MIXED['models']['cross_scale_attention_lite']['external_holdout']['accuracy']), fmt_pct(MIXED['models']['cross_scale_attention_lite']['external_holdout']['f1']), f"{MIXED['models']['cross_scale_attention_lite']['external_holdout']['auc']:.4f}", fmt_pct(MIXED['models']['cross_scale_attention_lite']['external_holdout']['eer']), f"{MIXED['models']['cross_scale_attention_lite']['tflite_kb']:.1f} KB"],
        ["CBAM-ResNet Lite (mixed retrain)", fmt_pct(MIXED['models']['cbam_resnet_lite']['internal_test']['accuracy']), fmt_pct(MIXED['models']['cbam_resnet_lite']['external_holdout']['accuracy']), fmt_pct(MIXED['models']['cbam_resnet_lite']['external_holdout']['f1']), f"{MIXED['models']['cbam_resnet_lite']['external_holdout']['auc']:.4f}", fmt_pct(MIXED['models']['cbam_resnet_lite']['external_holdout']['eer']), f"{MIXED['models']['cbam_resnet_lite']['tflite_kb']:.1f} KB"],
    ], widths=[2.5, 0.9, 0.9, 0.8, 0.8, 0.8, 0.8])

    doc.add_heading("2.7. Kết luận chương 2", level=2)
    add_paragraph(doc, "Chương 2 đã mô tả toàn bộ phần lõi của quá trình nghiên cứu: chuẩn bị dữ liệu, lựa chọn đặc trưng, triển khai các nhánh mô hình, phân tích domain shift và đưa ra tiêu chí chọn mô hình cuối. Điểm rút ra lớn nhất là bài toán anti-spoof không thể đánh giá nghiêm túc nếu thiếu tập ngoài nguồn. Chính phát hiện này đã đẩy dự án từ một bài demo accuracy cao nội bộ sang một quá trình chọn mô hình thực tế hơn, có khả năng bảo vệ tốt hơn khi gặp dữ liệu lạ.")


def chapter3(doc: Document):
    doc.add_page_break()
    doc.add_heading("CHƯƠNG 3. TÍCH HỢP HỆ THỐNG TRÊN ANDROID VÀ ĐÁNH GIÁ HIỆU NĂNG", level=1)

    doc.add_heading("3.1. Kiến trúc tổng thể của ứng dụng", level=2)
    paras = [
        "Ứng dụng Android trong dự án được tổ chức theo cấu trúc khá rõ ràng giữa tầng giao diện, tầng domain và tầng data. Tại lớp trên cùng, màn hình chính do `VoiceDetectorScreen` đảm nhiệm với ba tab: Phát hiện, Lịch sử và Cài đặt. Tầng điều phối trung gian nằm ở `VoiceDetectorViewModel`, chịu trách nhiệm quản lý trạng thái UI, điều phối ghi âm, chạy suy luận và cập nhật các chỉ số hiệu năng cùng lịch sử phiên. Tầng xử lý dữ liệu gồm các thành phần như `MicrophoneAudioRecorder`, `AudioFeatureExtractor`, `TFLiteSpoofDetectorEngine` và `VoiceSpoofingRepositoryImpl`.",
        "Điểm đáng chú ý là engine TFLite được viết theo hướng tự nhận biết loại mô hình tại thời gian chạy. Nếu file model có một input dạng vector, hệ thống coi đó là single-input model; nếu có hai input với một nhánh spectrogram và một nhánh acoustic, engine sẽ chuyển sang chế độ dual-input. Cách làm này rất thực dụng vì cho phép cùng một app thử nhiều nhánh mô hình mà không cần viết lại toàn bộ tầng suy luận mỗi lần đổi kiến trúc.",
        "Đối với luồng anti-spoof on-device, người dùng ghi âm, repository sẽ trích đặc trưng, kiểm tra điều kiện chất lượng, sau đó gọi engine TFLite để ra xác suất spoof. Kết quả tiếp tục được đưa về ViewModel để hiển thị quyết định, thời lượng, độ trễ trích đặc trưng, độ trễ suy luận và cập nhật session mới ở tab lịch sử. Điều này cho thấy ứng dụng không chỉ là giao diện hiển thị phần trăm giả mạo, mà đã có đầy đủ một vòng thao tác khép kín phục vụ trình diễn và đối chiếu kết quả.",
    ]
    for para in paras:
        add_paragraph(doc, para)

    add_table(doc, ["Thành phần", "Vai trò chính", "Ghi chú"], [
        ["VoiceDetectorScreen", "Giao diện Jetpack Compose", "Chứa tab Phát hiện, Lịch sử, Cài đặt"],
        ["VoiceDetectorViewModel", "Điều phối trạng thái", "Kết nối recording, inference, lịch sử phiên và cấu hình ngưỡng"],
        ["MicrophoneAudioRecorder", "Ghi âm PCM 16 kHz", "Nguồn dữ liệu cho pipeline anti-spoof"],
        ["AudioFeatureExtractor", "Tạo đặc trưng âm thanh", "Runtime dùng 8 acoustic feature; mã nguồn còn hỗ trợ thêm MFCC cho nghiên cứu"],
        ["TFLiteSpoofDetectorEngine", "Suy luận mô hình", "Hỗ trợ single-input và dual-input"],
        ["VoiceSpoofingRepositoryImpl", "Kiểm tra và phân tích mẫu ghi âm", "Có kiểm tra chất lượng và speech presence"],
        ["DetectorUiState / session history", "Giữ kết quả gần nhất", "Phục vụ tab Lịch sử và export CSV"],
    ], widths=[1.7, 2.5, 2.3])

    doc.add_heading("3.2. Trích đặc trưng và suy luận mô hình trên thiết bị", level=2)
    add_paragraph(doc, "Trong phiên bản app đang demo, `AudioFeatureExtractor` cung cấp phần đặc trưng âm học phục vụ kiểm tra đầu vào và nhánh acoustic của model deploy. Dù mã nguồn vẫn còn khả năng tính thêm MFCC để hỗ trợ các hướng nghiên cứu khác, pipeline runtime được mô tả trong báo cáo chỉ bám theo những gì APK đang gọi thật: log-Mel spectrogram và 8 đặc trưng acoustic nền.")
    add_paragraph(doc, "Ở phía engine suy luận, app phân biệt hai tình huống. Với model single-input, hệ thống chỉ lấy đúng số chiều mà tensor yêu cầu và bỏ phần dư. Với model dual-input đang dùng trong APK, app tính thêm log-Mel spectrogram, nhận diện tensor nào là input phổ và tensor nào là input acoustic rồi thực hiện `runForMultipleInputsOutputs`. Cách tổ chức này cho phép phần app giữ được tính linh hoạt kỹ thuật, nhưng phần mô tả trong báo cáo vẫn tập trung vào nhánh dual-input đang chạy thật trên thiết bị.")

    doc.add_heading("3.3. Các kiểm tra chất lượng đầu vào và tính ổn định của pipeline", level=2)
    add_paragraph(doc, "Một mô hình mạnh chưa đủ đảm bảo hành vi hệ thống ổn định nếu đầu vào có chất lượng quá kém. Trong `VoiceSpoofingRepositoryImpl`, ứng dụng chặn sớm nhiều tình huống: không có âm thanh, thời lượng dưới 1 giây, quá dài, RMS quá thấp hoặc tỷ lệ clipping vượt ngưỡng. Đồng thời, với môi trường không phải emulator, hệ thống còn chạy một dạng VAD đơn giản theo frame năng lượng để tránh trường hợp người dùng ghi âm nhưng hầu như không nói gì. Đây là lựa chọn cần thiết vì nhiều lỗi “model dự đoán linh tinh” thực chất bắt nguồn từ audio rỗng hoặc audio không có nội dung lời nói.")
    add_table(doc, ["Điều kiện", "Ngưỡng hiện tại", "Ý nghĩa"], [
        ["Thời lượng tối thiểu", "1,0 giây", "Tránh suy luận trên mẫu quá ngắn"],
        ["Thời lượng tối đa", "15,0 giây", "Giữ app phản hồi nhanh, tránh ghi kéo dài"],
        ["RMS tối thiểu", "0,001", "Loại tín hiệu quá nhỏ hoặc quá xa micro"],
        ["Clipping ratio tối đa", "0,35", "Loại tín hiệu méo mạnh"],
        ["Số frame voiced tối thiểu", "3 frame", "Bảo đảm có hoạt động lời nói"],
        ["Tỷ lệ voiced tối thiểu", "10%", "Giảm rủi ro mẫu rỗng/ồn nền"],
    ], widths=[2.6, 1.3, 2.6])
    add_paragraph(doc, "Đáng chú ý, các kiểm tra này được nới lỏng khi chạy trên emulator vì micro ảo thường cho kết quả không ổn định. Đây là một quyết định hợp lý về mặt thực dụng: nếu vẫn ép quality gate trên emulator, phần demo UI sẽ thường xuyên dừng ở lỗi đầu vào và khó trình bày cho người xem. Ngược lại, khi quay video trên thiết bị thật, các điều kiện đầy đủ nên được bật để phản ánh đúng hành vi mong muốn của hệ thống.")

    doc.add_heading("3.4. Quản lý lịch sử phiên, cấu hình ngưỡng và dữ liệu minh chứng", level=2)
    add_paragraph(doc, "Ngoài lớp anti-spoof on-device, bản app hiện tại còn hoàn thiện các chức năng hỗ trợ đối chiếu kết quả trực tiếp trên thiết bị. Tab `Lịch sử` lưu lại các session vừa phân tích, hiển thị quyết định, xác suất spoof, thời lượng và thời gian tạo phiên. Từ đó, người dùng có thể kiểm tra lại nhiều lần chạy liên tiếp thay vì chỉ nhìn kết quả của một lần ghi âm duy nhất.")
    add_paragraph(doc, "Tab `Cài đặt` cho phép thay đổi spoof threshold và chọn nhãn dữ liệu phục vụ lưu mẫu WAV. Kết hợp với chức năng export CSV, ứng dụng tạo ra một vòng thao tác đủ để quay video minh họa, chụp ảnh báo cáo và đối chiếu số liệu mà không cần phụ thuộc vào backend ngoài. Từ góc nhìn báo cáo, đây là phần chứng minh rõ nhất rằng hệ thống đã vượt khỏi mức demo tối thiểu và có khả năng tái hiện kết quả một cách kiểm chứng được.")

    doc.add_heading("3.5. Kết quả đánh giá mô hình và đối chiếu với bản app đang demo", level=2)
    add_table(doc, ["Chỉ số", "Tập nội bộ", "Tập ngoài nguồn"], [
        ["Accuracy", fmt_pct(V2['internal_test']['acc']), fmt_pct(V2['external_holdout']['acc'])],
        ["Precision spoof", fmt_pct(V2['internal_test']['prec']), fmt_pct(V2['external_holdout']['prec'])],
        ["Recall spoof", fmt_pct(V2['internal_test']['rec']), fmt_pct(V2['external_holdout']['rec'])],
        ["F1 spoof", fmt_pct(V2['internal_test']['f1']), fmt_pct(V2['external_holdout']['f1'])],
        ["AUC", f"{V2['internal_test']['auc']:.4f}", f"{V2['external_holdout']['auc']:.4f}"],
        ["EER", fmt_pct(V2['internal_test']['eer']), fmt_pct(V2['external_holdout']['eer'])],
        ["Confusion", f"TP={V2['internal_test']['tp']} FP={V2['internal_test']['fp']} FN={V2['internal_test']['fn']} TN={V2['internal_test']['tn']}", f"TP={V2['external_holdout']['tp']} FP={V2['external_holdout']['fp']} FN={V2['external_holdout']['fn']} TN={V2['external_holdout']['tn']}"],
    ], widths=[1.8, 2.2, 2.5])
    add_paragraph(doc, "Số liệu trên cho thấy khoảng cách giữa internal và external vẫn tồn tại, nhưng đã giảm rất mạnh so với giai đoạn benchmark ban đầu. Tại ngưỡng 0,05 trên tập ngoài nguồn 1.200 mẫu, mô hình giữ được recall spoof 95,33%, đồng nghĩa bỏ sót ít mẫu giả mạo hơn đáng kể. Trong bối cảnh phòng thủ, đây là tín hiệu tích cực, bởi lỗi nguy hiểm nhất thường là cho phép một mẫu spoof đi qua chứ không phải chặn nhầm thêm một số bonafide. Dù vậy, FP vẫn còn 72 mẫu nên hệ thống nên được xem là lớp đánh giá rủi ro bổ sung hơn là cơ chế xác thực đơn độc.")

    doc.add_heading("3.6. Độ trễ và chi phí tính toán", level=2)
    add_table(doc, ["Thành phần", "Trung bình", "P95", "Max"], [
        ["Load WAV", f"{V2['latency']['load_wav_ms']:.1f} ms", "1,8 ms", "1,8 ms"],
        ["Trích đặc trưng âm thanh", f"{V2['latency']['feature_ms']:.1f} ms", "31,2 ms", "43,3 ms"],
        ["TFLite inference", f"{V2['latency']['inference_ms']:.1f} ms", "0,1 ms", "0,6 ms"],
        ["Tổng pipeline", f"{V2['latency']['total_ms']:.1f} ms", f"{V2['latency']['p95_ms']:.1f} ms", f"{V2['latency']['max_ms']:.1f} ms"],
    ], widths=[2.8, 1.2, 1.2, 1.2])
    add_paragraph(doc, "Các số đo trên được lấy trên máy tính trong quá trình chạy thử pipeline, nhưng vẫn có giá trị định hướng cho thiết bị Android. Khi đối chiếu với app đang demo, báo cáo chỉ nên dùng các chỉ số runtime đọc trực tiếp từ giao diện như thời gian trích đặc trưng, thời gian suy luận, tổng pipeline và RAM tức thời. Những con số này mới phản ánh đúng hành vi của APK đang chạy, thay vì suy diễn từ một nhánh mô hình khác không phải tâm điểm của bản build hiện tại.")

    doc.add_heading("3.7. Chức năng ứng dụng đã hoàn thành phục vụ demo", level=2)
    add_bullets(doc, [
        "Ghi âm nội bộ bằng microphone và phân tích xác suất spoof trên thiết bị.",
        "Kiểm tra file âm thanh ngoài (external) để minh họa trường hợp giọng thật và giọng giả bằng các file mẫu.",
        "Lưu lịch sử phiên phát hiện, hiển thị quyết định và hỗ trợ xuất CSV.",
        "Điều chỉnh ngưỡng spoof ngay trên app.",
        "Thu thập dataset mẫu ngay trên thiết bị bằng chức năng save sample theo nhãn bonafide/spoof.",
        "Duy trì lịch sử phiên và hỗ trợ export CSV để đối chiếu kết quả sau khi chạy.",
    ])

    doc.add_heading("3.8. Kết luận chương 3", level=2)
    add_paragraph(doc, "Phần triển khai Android đã xác nhận rằng bài toán phát hiện giả mạo giọng nói có thể được đóng gói thành một pipeline đủ gọn để chạy trên thiết bị, đồng thời vẫn giữ được các thành phần cần thiết cho demo và mở rộng sau này. Giá trị của chương này không nằm ở giao diện bắt mắt, mà ở chỗ mô hình, quality gate, lịch sử phiên, export CSV và cấu hình ngưỡng đã được nối thành một luồng tương đối hoàn chỉnh, giúp việc trình bày với giảng viên hoặc quay video minh họa trở nên thuyết phục hơn.")


def chapter4(doc: Document):
    doc.add_page_break()
    doc.add_heading("CHƯƠNG 4. BÁO CÁO TIẾN ĐỘ, KẾT QUẢ HOÀN THÀNH VÀ KẾ HOẠCH ĐIỀU CHỈNH", level=1)

    doc.add_heading("4.1. Tóm tắt tiến độ từ khi nhận đề tài đến ngày 15/06/2026", level=2)
    add_table(doc, ["Giai đoạn", "Thời gian", "Kết quả chính"], [
        ["Xây dựng đề cương", "16/03 - 19/03/2026", "Hoàn thiện đề cương, xác định phạm vi và hướng on-device AI"],
        ["Tổng quan lý thuyết", "20/03 - 27/03/2026", "Tổng hợp tài liệu về deepfake voice, ASVspoof, TTS, VC và Edge AI"],
        ["Chuẩn bị dữ liệu và baseline", "28/03 - 09/05/2026", "Tạo pipeline dataset, huấn luyện baseline DNN 8 feature, export TFLite"],
        ["Báo cáo tiến độ đợt 1", "09/05 - 10/05/2026", "Trình bày trạng thái giữa kỳ và nhận góp ý"],
        ["Benchmark và external evaluation", "11/05 - 08/06/2026", "Huấn luyện 3 model lite, test ngoài nguồn, ablation, t-SNE, threshold analysis"],
        ["Hoàn thiện bản thảo và tích hợp app", "09/06 - 15/06/2026", "Chốt luồng anti-spoof on-device, dọn UI, chuẩn bị nội dung trình bày và tài liệu hoàn chỉnh"],
    ], widths=[1.8, 1.6, 3.1])

    doc.add_heading("4.2. Các đầu mục đã hoàn thành trong tuần báo cáo hiện tại", level=2)
    add_bullets(doc, [
        "Rà soát lại toàn bộ dữ liệu báo cáo trước đó, đối chiếu kết quả huấn luyện trong repo để tránh mâu thuẫn giữa các phiên bản mô hình.",
        "Rà soát lại mô hình đang được app deploy để phần mô tả chỉ bám theo nhánh anti-spoof on-device đang chạy thật.",
        "Giữ lại nhánh benchmark Cross-Scale, AASIST Lite và CBAM-ResNet Lite như phần khảo sát thực nghiệm và đối chứng học thuật.",
        "Mô tả lại cấu trúc ứng dụng Android dựa trên mã nguồn thật, bao gồm các lớp `AudioFeatureExtractor`, `TFLiteSpoofDetectorEngine`, `VoiceSpoofingRepositoryImpl`, `VoiceDetectorViewModel` và giao diện Jetpack Compose.",
        "Bổ sung chi tiết về quality gate, threshold, lịch sử phiên, export CSV và cơ chế thu thập dataset trên thiết bị.",
        "Chuẩn bị lại phần hình ảnh minh chứng, gom ảnh chụp app, biểu đồ hiệu năng, ablation, t-SNE, kiến trúc hệ thống để đưa vào phụ lục báo cáo.",
        "Dựng bản Word hoàn chỉnh có thể tiếp tục sửa câu chữ trực tiếp mà không cần ghép tay từ nhiều báo cáo tuần rời nhau.",
    ])

    doc.add_heading("4.3. Nội dung cần trình bày theo yêu cầu từ người giao việc", level=2)
    add_paragraph(doc, "Theo yêu cầu kèm theo, phần báo cáo viết cần bám sát các nội dung đã làm thực tế, còn video minh họa nên tập trung vào các tình huống dễ quan sát và có giá trị chứng minh nhất. Để việc quay video sau đó diễn ra thuận lợi, tài liệu này chốt sẵn bốn tình huống demo trọng tâm, tương ứng với những gì app hiện đã hỗ trợ hoặc đã có dữ liệu minh chứng.")
    add_table(doc, ["Mục demo", "Nội dung cần quay", "Trạng thái chuẩn bị từ phía báo cáo"], [
        ["External bonafide", "Chọn file ngoài nguồn là giọng thật và cho app nhận đúng", "Đã có mô tả trong phụ lục hình ảnh"],
        ["External spoof", "Chọn file ngoài nguồn là giọng giả và cho app nhận đúng", "Đã có mô tả trong phụ lục hình ảnh"],
        ["Internal recording", "Ghi âm trực tiếp trên app và hiển thị kết quả thật/giả", "Đã mô tả luồng ghi âm và quality gate"],
        ["Chức năng app", "Lướt qua các tab Phát hiện, Lịch sử, Cài đặt và dataset capture", "Đã có danh sách chức năng hoàn thành"],
    ], widths=[1.5, 3.0, 2.0])

    doc.add_heading("4.4. Nhận xét về mức độ hoàn thành", level=2)
    paras = [
        "Nếu so với đề cương ban đầu, khối lượng công việc đã đi xa hơn mức tối thiểu của một báo cáo lý thuyết. Không chỉ có một mô hình được huấn luyện và đưa vào app, dự án còn có benchmark nhiều nhánh, có dữ liệu ngoài nguồn, có phân tích threshold và có biểu đồ trực quan. Phần còn lại chủ yếu là chốt cách kể câu chuyện trong báo cáo và quay video minh họa sao cho khớp với trạng thái triển khai.",
        "Mặt mạnh lớn nhất hiện nay là hệ thống đã có số liệu thực để bảo vệ lựa chọn mô hình và có một bản app chạy được trên thiết bị với chuỗi thao tác khép kín. Mặt cần lưu ý là báo cáo phải phân biệt rõ giữa kết quả benchmark phục vụ nghiên cứu và nhánh deploy đang được app sử dụng để demo. Cách trình bày an toàn nhất là xem benchmark như nền tảng khảo sát, còn phần app chỉ mô tả đúng pipeline anti-spoof đang chạy thật. Việc trình bày như vậy giúp tránh cảm giác “đổi mô hình vô cớ” và cũng phản ánh đúng tiến trình nghiên cứu.",
        "Ngoài ra, việc quay video trên thiết bị thật vẫn nên được ưu tiên hơn emulator nếu có thể, bởi quality gate, độ trễ, RMS và hành vi micro trên thiết bị thật mới phản ánh sát hơn trải nghiệm người dùng. Tuy nhiên, ngay cả khi chưa có đủ video cuối, bản Word hiện tại vẫn đủ vai trò làm xương sống nội dung để người nhờ bạn tiếp tục sửa giọng văn hoặc cắt giảm phần nào tùy nhu cầu nộp.",
    ]
    for para in paras:
        add_paragraph(doc, para)

    doc.add_heading("4.5. Kế hoạch xử lý sau khi có góp ý tiếp theo", level=2)
    add_numbered(doc, [
        "Nếu giảng viên yêu cầu thống nhất mô hình chính, ưu tiên giữ mô hình đang được deploy trong app ở phần kết luận triển khai, còn benchmark ba mô hình chuyển về mục so sánh thực nghiệm.",
        "Nếu giảng viên muốn nhấn mạnh quá trình nghiên cứu, có thể giữ benchmark như hành trình khảo sát, nhưng mọi ảnh chụp và mô tả app vẫn phải bám theo nhánh deploy hiện tại.",
        "Nếu có yêu cầu bổ sung video, ưu tiên quay trên thiết bị thật theo thứ tự: external bonafide, external spoof, internal recording, sau cùng là walkthrough các tab chức năng.",
        "Nếu cần rút ngắn tài liệu trước khi nộp, nên cắt bớt phần phụ lục hình ảnh trùng lặp trước, giữ nguyên số liệu và phần giải thích domain shift.",
    ])


def conclusion(doc: Document):
    doc.add_page_break()
    doc.add_heading("KẾT LUẬN", level=1)
    paras = [
        "Đề tài đã đi qua một lộ trình tương đối đầy đủ từ nghiên cứu tổng quan đến triển khai thử nghiệm. Điểm nhấn quan trọng nhất không phải là một con số accuracy đơn lẻ, mà là việc phát hiện và xử lý một vấn đề mang tính bản chất: mô hình chống giả mạo giọng nói có thể rất đẹp trên tập nội bộ nhưng dễ suy giảm mạnh khi gặp dữ liệu khác nguồn. Chỉ khi chấp nhận thực tế này và đưa external evaluation vào trung tâm phân tích, quá trình xây dựng hệ thống mới trở nên đáng tin cậy hơn.",
        f"Ở thời điểm báo cáo ngày 15/06/2026, phần nghiên cứu đã cho thấy nhiều nhánh mô hình có giá trị đối chiếu, trong đó external evaluation tiếp tục là tiêu chí quan trọng để tránh ảo tưởng từ split nội bộ. Song song với đó, phần triển khai Android đã đạt mức đủ để trình bày: mô hình TensorFlow Lite chạy on-device, quality gate hoạt động, giao diện hiển thị được xác suất spoof và chỉ số hiệu năng, lịch sử phiên được lưu, CSV có thể xuất trực tiếp. Cách tách này giúp kết luận vừa trung thực với quá trình nghiên cứu, vừa không mô tả sai những gì app đang làm.",
        "Về mặt sản phẩm thử nghiệm, ứng dụng Android đã đủ chức năng để phục vụ trình bày: ghi âm và phân tích nội bộ, kiểm tra file ngoài, xem lịch sử, cấu hình ngưỡng, lưu dataset mẫu và đối chiếu các chỉ số runtime ngay trên màn hình. Nói cách khác, hệ thống không còn là một mô hình độc lập trên notebook, mà đã trở thành một pipeline có giao diện, có luồng xử lý và có dữ liệu minh chứng. Đây là nền tảng tốt để tiếp tục chỉnh sửa báo cáo theo góp ý của giảng viên hoặc quay video demo theo các kịch bản đã xác định.",
    ]
    for para in paras:
        add_paragraph(doc, para)

    doc.add_heading("HƯỚNG PHÁT TRIỂN", level=1)
    add_bullets(doc, [
        "Mở rộng tập ngoài nguồn tiếng Việt với nhiều công cụ TTS, nhiều thiết bị ghi và nhiều điều kiện môi trường hơn để kiểm tra độ bền mô hình.",
        "Đo latency, RAM và mức tiêu thụ pin trực tiếp trên 1-2 thiết bị Android thật thay vì chỉ ước lượng từ máy tính và emulator.",
        "Chuẩn hóa thêm quy trình threshold calibration theo kịch bản triển khai thực tế, ví dụ ưu tiên recall spoof cao hơn trong bài toán phòng thủ.",
        "Tiếp tục tối ưu pipeline anti-spoof on-device và chỉ bổ sung các lớp xác minh khác khi thật sự cần cho phiên bản tiếp theo.",
        "Bổ sung logging và dashboard để theo dõi drift của dữ liệu khi hệ thống chạy lâu dài.",
    ])


def appendix_metrics(doc: Document):
    doc.add_page_break()
    doc.add_heading("PHỤ LỤC A. THỐNG KÊ DỮ LIỆU, CẤU HÌNH HUẤN LUYỆN VÀ BẢNG SỐ LIỆU CHI TIẾT", level=1)

    doc.add_heading("A.1. Cấu hình benchmark acoustic augmented", level=2)
    add_table(doc, ["Hạng mục", "Giá trị"], [
        ["Dataset root", "data/dataset_samples"],
        ["Tổng số mẫu", str(SUMMARY_ACOUSTIC['sample_count'])],
        ["Train", str(SUMMARY_ACOUSTIC['split_count']['train'])],
        ["Validation", str(SUMMARY_ACOUSTIC['split_count']['val'])],
        ["Test", str(SUMMARY_ACOUSTIC['split_count']['test'])],
        ["Sample rate", str(SUMMARY_ACOUSTIC['sample_rate'])],
        ["Max duration", str(SUMMARY_ACOUSTIC['max_duration_sec']) + " giây"],
        ["Augmentation", "random gain, time shift, Gaussian noise"],
        ["Acoustic feature branch", ", ".join(SUMMARY_ACOUSTIC['acoustic_feature_order'])],
    ], widths=[2.2, 4.2])

    doc.add_heading("A.2. Kết quả đầy đủ của nhánh mixed retrain", level=2)
    for model_key, title in [
        ("cross_scale_attention_lite", "Cross-Scale Attention Lite"),
        ("aasist_lite", "AASIST Lite"),
        ("cbam_resnet_lite", "CBAM-ResNet Lite"),
    ]:
        model = MIXED['models'][model_key]
        add_paragraph(doc, title, bold=True)
        add_table(doc, ["Chỉ số", "Internal test", "External holdout"], [
            ["Accuracy", fmt_pct(model['internal_test']['accuracy']), fmt_pct(model['external_holdout']['accuracy'])],
            ["Precision", fmt_pct(model['internal_test']['precision']), fmt_pct(model['external_holdout']['precision'])],
            ["Recall", fmt_pct(model['internal_test']['recall']), fmt_pct(model['external_holdout']['recall'])],
            ["F1", fmt_pct(model['internal_test']['f1']), fmt_pct(model['external_holdout']['f1'])],
            ["AUC", f"{model['internal_test']['auc']:.4f}", f"{model['external_holdout']['auc']:.4f}"],
            ["EER", fmt_pct(model['internal_test']['eer']), fmt_pct(model['external_holdout']['eer'])],
            ["Confusion", f"TP={model['internal_test']['tp']} FP={model['internal_test']['fp']} FN={model['internal_test']['fn']} TN={model['internal_test']['tn']}", f"TP={model['external_holdout']['tp']} FP={model['external_holdout']['fp']} FN={model['external_holdout']['fn']} TN={model['external_holdout']['tn']}"],
        ], widths=[1.6, 2.4, 2.4])
        add_paragraph(doc, f"Mô hình có {model['params']} tham số, kích thước TFLite khoảng {model['tflite_kb']:.1f} KB, dùng {model['mix_per_class']} mẫu external mỗi lớp trộn vào training.")

    doc.add_heading("A.3. Bảng tiêu chí nghiệm thu theo số liệu hiện có", level=2)
    add_table(doc, ["Tiêu chí", "Mục tiêu", "Kết quả DNN v2", "Trạng thái"], [
        ["External Accuracy", ">= 80%", fmt_pct(V2['external_holdout']['acc']), "Đạt"],
        ["Recall lớp spoof", ">= 85%", fmt_pct(V2['external_holdout']['rec']), "Đạt"],
        ["F1 lớp spoof", ">= 85%", fmt_pct(V2['external_holdout']['f1']), "Đạt"],
        ["Kích thước TFLite", "<= 100 KB", f"{V2['tflite_kb']:.1f} KB", "Đạt"],
        ["Tổng latency trung bình", "< 1 giây", f"{V2['latency']['total_ms']:.1f} ms", "Đạt"],
    ], widths=[2.4, 1.1, 1.6, 1.1])

    doc.add_heading("A.4. Kịch bản quay video minh họa", level=2)
    add_table(doc, ["Bước", "Mô tả thao tác", "Mục tiêu chứng minh"], [
        ["1", "Mở app ở tab Phát hiện, giới thiệu ngắn các vùng chức năng", "Cho thấy bố cục app đã hoàn thiện"],
        ["2", "Chọn file external bonafide và chạy phân tích", "Minh chứng app nhận đúng giọng thật ngoài nguồn"],
        ["3", "Chọn file external spoof và chạy phân tích", "Minh chứng app nhận đúng giọng giả ngoài nguồn"],
        ["4", "Ghi âm internal trực tiếp trên máy", "Cho thấy luồng ghi âm và suy luận nội bộ hoạt động"],
        ["5", "Mở tab Lịch sử, tab Cài đặt, phần dataset capture", "Liệt kê các chức năng đã làm được"],
    ], widths=[0.7, 3.5, 2.3])


def appendix_figures(doc: Document):
    doc.add_page_break()
    doc.add_heading("PHỤ LỤC B. HÌNH ẢNH MINH CHỨNG ỨNG DỤNG VÀ BIỂU ĐỒ ĐÁNH GIÁ", level=1)
    figure_specs = [
        (DOCS / "figures" / "screenshots" / "01_detect_tab.png", 5.7, "Hình B.0. Màn hình phát hiện ở giai đoạn giao diện ban đầu của ứng dụng."),
        (DOCS / "figures" / "screenshots" / "02_phat_hien_tab.png", 5.7, "Hình B.0a. Trạng thái tab Phát hiện khi hiển thị kết quả phát hiện giả mạo."),
        (DOCS / "figures" / "screenshots" / "03_spoof_result_full.png", 5.3, "Hình B.0b. Kết quả SPOOF ở giao diện chi tiết, phục vụ mô tả cho phần demo."),
        (DOCS / "figures" / "screenshots" / "04_spoof_details.png", 5.3, "Hình B.0c. Khối thông tin chi tiết của phiên phát hiện giả mạo."),
        (DOCS / "figures" / "screenshots" / "05_acoustic_features.png", 5.3, "Hình B.0d. Khu vực hiển thị đặc trưng âm học và chỉ số hiệu năng trong app."),
        (DOCS / "figures" / "screenshots" / "06b_before_expand.png", 5.3, "Hình B.0e. Trạng thái card đặc trưng trước khi mở rộng."),
        (DOCS / "figures" / "screenshots" / "06_features_expanded.png", 5.3, "Hình B.0f. Trạng thái card đặc trưng sau khi mở rộng."),
        (DOCS / "figures" / "screenshots" / "07_features_detail.png", 5.3, "Hình B.0g. Danh sách đặc trưng chi tiết phục vụ giải thích mô hình."),
        (DOCS / "figures" / "screenshots" / "08_settings_benchmark.png", 5.3, "Hình B.0h. Màn hình benchmark file mẫu trong giai đoạn trước khi dọn UX."),
        (DOCS / "figures" / "screenshots" / "09_file2_spoof.png", 5.3, "Hình B.0i. Ví dụ file spoof thứ hai được app phát hiện đúng."),
        (DOCS / "figures" / "screenshots" / "09_next_file.png", 5.3, "Hình B.0j. Màn hình chuẩn bị chuyển sang file kế tiếp trong chuỗi kiểm tra."),
        (DOCS / "figures" / "screenshots" / "09b_file2.png", 5.3, "Hình B.0k. Màn hình file kiểm tra thứ hai trong danh sách audit."),
        (DOCS / "figures" / "screenshots" / "10_history_tab.png", 5.1, "Hình B.0l. Lịch sử phát hiện ở một phiên bản giao diện trước."),
        (DOCS / "figures" / "screenshots" / "11_threshold_settings.png", 5.1, "Hình B.0m. Khu vực cài đặt ngưỡng ở giao diện cũ."),
        (DOCS / "figures" / "screenshots" / "11b_nguong_section.png", 5.1, "Hình B.0n. Chi tiết section ngưỡng với các giá trị sử dụng trong thực nghiệm."),
        (DOCS / "figures" / "screenshots" / "12a_settings_scroll1.png", 5.1, "Hình B.0o. Trạng thái cuộn của tab Cài đặt trong quá trình rà soát UX."),
        (DOCS / "figures" / "screenshots" / "12b_threshold_section.png", 5.1, "Hình B.0p. Khu vực threshold sau khi tinh gọn giao diện."),
        (DOCS / "figures" / "screenshots" / "13_asv_section.png", 5.1, "Hình B.0q. Khu vực cấu hình ngưỡng và nhãn dữ liệu ở màn hình cài đặt."),
        (DOCS / "figures" / "screenshots" / "new_01_detect_overview.png", 5.7, "Hình B.1. Tổng quan tab Phát hiện sau khi cập nhật UX."),
        (DOCS / "figures" / "screenshots" / "new_02_detect_filecard.png", 5.7, "Hình B.2. Khu vực phân tích file mẫu nằm ngay trong tab Phát hiện."),
        (DOCS / "figures" / "screenshots" / "new_03_bonafide_result.png", 4.0, "Hình B.2a. Kết quả bonafide ở một ảnh chụp cận cảnh khác."),
        (DOCS / "figures" / "screenshots" / "new_04_bonafide_all3.png", 4.0, "Hình B.3. File bonafide được ba mô hình nhận đúng là BONAFIDE."),
        (DOCS / "figures" / "screenshots" / "new_05_spoof_result.png", 4.0, "Hình B.4. File spoof được ba mô hình nhận đúng là SPOOF."),
        (DOCS / "figures" / "screenshots" / "new_06_settings_clean.png", 4.8, "Hình B.5. Tab Cài đặt sau khi dọn UX, chỉ giữ các cấu hình cần thiết."),
        (DOCS / "figures" / "screenshots" / "new_07_history.png", 4.8, "Hình B.6. Tab Lịch sử lưu các phiên phát hiện và quyết định của hệ thống."),
        (DOCS / "reports" / "screenshots" / "tmp_after_permission_tap.png", 5.5, "Hình B.6a. Trạng thái ứng dụng ngay sau khi cấp quyền micro."),
        (DOCS / "reports" / "screenshots" / "app_current.png", 5.5, "Hình B.6b. Ảnh chụp ứng dụng ở trạng thái tổng quan hiện tại."),
        (DOCS / "reports" / "screenshots" / "app_after_settings_tap.png", 5.5, "Hình B.6c. Giao diện sau khi chuyển sang tab Cài đặt."),
        (DOCS / "reports" / "screenshots" / "app_detection_3_models_installed.png", 5.5, "Hình B.6d. Màn hình phát hiện khi ba mô hình đã được cài đặt."),
        (DOCS / "reports" / "screenshots" / "app_settings_3_models_installed.png", 5.5, "Hình B.6e. Màn hình cài đặt với thông tin ba mô hình đã có sẵn."),
        (DOCS / "reports" / "screenshots" / "app_external_test_file_audit.png", 5.5, "Hình B.6f. Audit file kiểm tra ngoài nguồn ở bước đầu."),
        (DOCS / "reports" / "screenshots" / "app_external_test_file_audit_next.png", 5.5, "Hình B.6g. Bước tiếp theo của luồng audit file ngoài nguồn."),
        (DOCS / "reports" / "screenshots" / "app_audit_file_list_open.png", 5.5, "Hình B.6h. Danh sách file audit được mở trong ứng dụng."),
        (DOCS / "reports" / "screenshots" / "app_audit_external_bonafide.png", 5.5, "Hình B.6i. Audit external bonafide với kết quả phát hiện từ app."),
        (DOCS / "reports" / "screenshots" / "app_audit_external_spoof.png", 5.5, "Hình B.6j. Audit external spoof với kết quả phát hiện từ app."),
        (DOCS / "reports" / "screenshots" / "app_audit_internal_bonafide.png", 5.5, "Hình B.6k. Audit internal bonafide được dùng cho phần minh chứng nội bộ."),
        (DOCS / "reports" / "screenshots" / "app_audit_internal_spoof.png", 5.5, "Hình B.6l. Audit internal spoof trong kịch bản kiểm thử đối chứng."),
        (ML / "artifacts" / "report_figures" / "fig_confusion_matrix.png", 5.6, "Hình B.7. Ma trận nhầm lẫn của mô hình Cross-Scale trên external holdout."),
        (ML / "artifacts" / "report_figures" / "fig_model_comparison.png", 6.0, "Hình B.8. So sánh ba mô hình lite sau khi mixed retrain."),
        (ML / "artifacts" / "report_figures" / "fig_threshold_calibration.png", 6.0, "Hình B.9. Phân tích ngưỡng của mô hình trên tập ngoài nguồn."),
        (ML / "artifacts" / "report_figures" / "fig_ablation_study.png", 6.0, "Hình B.10. Kết quả leave-one-out ablation study cho bộ 8 đặc trưng."),
        (ML / "artifacts" / "report_figures" / "fig_progressive_addition.png", 6.0, "Hình B.11. Hiệu năng khi thêm dần các đặc trưng âm học."),
        (ML / "artifacts" / "report_figures" / "fig_device_performance.png", 6.0, "Hình B.11a. Biểu đồ tóm tắt hiệu năng thiết bị và độ trễ pipeline."),
        (ML / "artifacts" / "tsne" / "tsne_combined.png", 6.0, "Hình B.12. t-SNE kết hợp theo nhãn và theo nguồn, minh họa domain shift."),
        (ML / "artifacts" / "tsne" / "tsne_feature_density.png", 6.0, "Hình B.12a. Bản đồ mật độ đặc trưng trong không gian t-SNE."),
        (ML / "artifacts" / "tsne" / "tsne_label.png", 5.5, "Hình B.13. t-SNE theo nhãn bonafide/spoof."),
        (ML / "artifacts" / "tsne" / "tsne_source.png", 5.5, "Hình B.14. t-SNE theo nguồn internal/external."),
        (ML / "charts" / "fig_android_architecture.png", 6.0, "Hình B.15. Sơ đồ kiến trúc tích hợp ứng dụng Android."),
        (ML / "charts" / "fig_dnn_architecture.png", 5.8, "Hình B.16. Sơ đồ kiến trúc DNN dùng 21 đặc trưng trong nhánh benchmark mở rộng."),
        (ML / "charts" / "training_curves.png", 6.0, "Hình B.17. Đường cong huấn luyện của mô hình trong quá trình tối ưu."),
        (ML / "charts" / "roc_curve.png", 5.8, "Hình B.18. Đường ROC phục vụ đánh giá khả năng phân tách lớp."),
        (ML / "charts" / "pr_curve.png", 5.8, "Hình B.19. Đường Precision-Recall cho lớp spoof."),
        (ML / "charts" / "metrics_summary.png", 5.8, "Hình B.20. Tổng hợp chỉ số đánh giá của pipeline."),
        (ML / "charts" / "feature_distributions.png", 6.0, "Hình B.21. Phân bố đặc trưng giữa hai lớp dữ liệu."),
        (ML / "charts" / "fig_ui_detection.png", 5.8, "Hình B.22. Giao diện phát hiện ở một phiên bản trình diễn khác của app."),
        (ML / "charts" / "fig_ui_history_settings.png", 5.8, "Hình B.23. Minh họa các vùng Lịch sử và Cài đặt của app."),
    ]
    for path, width, caption in figure_specs:
        add_picture(doc, path, width, caption=caption, page_break_after=True)


def references(doc: Document):
    doc.add_heading("TÀI LIỆU THAM KHẢO", level=1)
    refs = [
        "[1] Damiani, J. A Voice Deepfake Was Used To Scam A CEO Out Of $243,000. Forbes, 2019.",
        "[2] United Nations Office on Drugs and Crime (UNODC). Casinos, cyber fraud, and trafficking in persons in Southeast Asia, 2023.",
        "[3] Wu et al. ASVspoof 2015: the first automatic speaker verification spoofing and countermeasures challenge. INTERSPEECH, 2015.",
        "[4] Todisco et al. ASVspoof 2019: Future Horizons in Spoofed and Fake Audio Detection. INTERSPEECH, 2019.",
        "[5] Nautsch et al. ASVspoof 2019: Spoofing Countermeasures for the Detection of Synthesized, Converted and Replayed Speech. IEEE T-BIOM, 2021.",
        "[6] Google. TensorFlow Lite Documentation for Mobile and Embedded Devices.",
        "[7] Android Developers. Machine Learning on Android.",
        "[8] Tài liệu nội bộ dự án: docs/technical/INTEGRATION_GUIDE.md, docs/technical/3_3_DANH_GIA_HIEU_NANG_HE_THONG.md, docs/training/README.md.",
        "[9] Mã nguồn ứng dụng Android và pipeline huấn luyện trong thư mục app/ và ml/ của dự án fake_voice_detector.",
    ]
    for ref in refs:
        add_paragraph(doc, ref, align=WD_ALIGN_PARAGRAPH.LEFT)


def filler_section(doc: Document):
    doc.add_page_break()
    doc.add_heading("PHỤ LỤC C. GHI CHÚ PHÂN TÍCH MỞ RỘNG", level=1)
    themes = [
        ("C.1. Vì sao accuracy nội bộ cao chưa đủ", [
            "Trong nhiều bài toán phân loại âm thanh, nhất là khi nguồn dữ liệu giữa train và test khá gần nhau, accuracy nội bộ thường tăng rất nhanh sau vài epoch. Điều này không sai, nhưng dễ tạo ảo giác rằng mô hình đã học “bản chất” của lớp dữ liệu. Với anti-spoofing, ảo giác đó còn mạnh hơn vì tín hiệu giả có thể chứa nhiều dấu vết đặc thù của công cụ tổng hợp hoặc chuỗi tiền xử lý. Khi test ngẫu nhiên trong cùng nguồn, mô hình chỉ cần bám vào những dấu vết đó là đã đạt điểm cao.",
            "Bài học của đề tài này là phải xem tập ngoài nguồn như một phép thử bắt buộc. Chỉ cần external accuracy tụt mạnh, mọi kết luận dựa trên internal split đều phải được đọc lại với thái độ dè dặt hơn. Nhìn theo hướng tích cực, chính sự tụt giảm này lại giúp quá trình nghiên cứu đi đúng đường hơn, buộc người thực hiện phải quan tâm tới domain shift, threshold calibration và chiến lược trộn dữ liệu.",
        ]),
        ("C.2. Ý nghĩa của quality gate trong ứng dụng thực tế", [
            "Ở môi trường nghiên cứu thuần notebook, người ta có xu hướng cho mọi file vào model rồi xem xác suất. Nhưng ở môi trường ứng dụng, hành vi đó không ổn. Một đoạn âm thanh quá ngắn, gần như im lặng hoặc bị clipping nặng nếu vẫn bị ép đưa qua mô hình sẽ sinh ra kết quả khó diễn giải, làm người dùng mất niềm tin vào hệ thống. Quality gate vì thế không phải phụ kiện, mà là hàng rào kỹ thuật giúp mô hình làm việc trên miền dữ liệu “có nghĩa”.",
            "Chính cách tách rõ quality gate và model giúp báo cáo này có tính hệ thống hơn. Khi kết quả sai, người thực hiện có thể phân biệt đó là lỗi từ đầu vào hay lỗi từ mô hình, từ đó tiết kiệm thời gian phân tích và sửa chữa.",
        ]),
        ("C.3. Lý do vẫn giữ benchmark ba mô hình trong báo cáo", [
            "Ngay cả khi DNN v2 đang là lựa chọn chốt hợp lý hơn ở thời điểm cập nhật, benchmark ba mô hình lite vẫn rất có giá trị. Trước hết, nó chứng minh học viên đã khảo sát nhiều hướng thay vì chọn đại một kiến trúc. Thứ hai, nó tạo nền so sánh để lý giải vì sao một mô hình giàu biểu diễn phổ chưa chắc đã thắng ở kịch bản dữ liệu ngoài nguồn tiếng Việt. Thứ ba, kết quả mixed retrain cho thấy những mô hình này không “kém”, mà chỉ nhạy hơn với domain shift và threshold mặc định.",
            "Giữ benchmark trong báo cáo cũng giúp người đọc hiểu tiến trình ra quyết định: ban đầu ưu tiên Cross-Scale do kích thước gọn và external holdout khá tốt sau mixed retrain; về sau DNN v2 vượt lên nhờ tổng quát hóa tốt hơn và độ trễ thấp hơn. Câu chuyện như vậy liền mạch và hợp logic hơn so với việc chỉ công bố một mô hình cuối mà bỏ qua hành trình khảo sát.",
        ]),
        ("C.4. Gợi ý cách bảo vệ khi trình bày trước giảng viên", [
            "Khi bảo vệ, nên tránh mở đầu bằng con số accuracy cao nhất. Thay vào đó, nên nói ngắn về bài toán: nếu chỉ nhìn split nội bộ thì rất dễ lạc quan, nhưng external test mới phản ánh rủi ro thật. Sau đó mới đưa ra hai nhánh kết quả chính: nhánh benchmark lite và nhánh DNN v2. Cách trình bày này tạo cảm giác kiểm soát vấn đề tốt hơn, vì người nói đang chỉ ra cả thành công lẫn điểm khó chứ không né phần khó.",
            "Nếu bị hỏi vì sao đổi mô hình chính, câu trả lời nên bám vào số liệu: DNN v2 có external accuracy và EER tốt hơn, trong khi kích thước và latency vẫn nằm trong ngưỡng triển khai on-device. Nếu bị hỏi vì sao vẫn giữ Cross-Scale trong báo cáo, hãy nhấn mạnh đây là mốc benchmark quan trọng và là cơ sở để quan sát tác động của mixed retrain.",
        ]),
    ]
    for heading, paragraphs in themes:
        doc.add_heading(heading, level=2)
        for paragraph in paragraphs:
            add_paragraph(doc, paragraph)


def main():
    doc = Document()
    style_document(doc)
    cover_page(doc)
    advisor_page(doc)
    front_matter(doc)
    chapter_intro(doc)
    chapter1(doc)
    chapter2(doc)
    chapter3(doc)
    chapter4(doc)
    conclusion(doc)
    appendix_metrics(doc)
    appendix_figures(doc)
    filler_section(doc)
    references(doc)
    doc.save(OUTPUT)
    print(f"Created: {OUTPUT}")


if __name__ == "__main__":
    main()

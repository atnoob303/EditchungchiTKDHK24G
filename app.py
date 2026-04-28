#!/usr/bin/env python3
"""
Backend Flask - Chứng chỉ Save the Children
Chạy: python3 app.py
Truy cập: http://localhost:5000
"""
from flask import Flask, request, send_file, jsonify, send_from_directory
import fitz
import datetime
import io
import os

app = Flask(__name__, static_folder=".")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_PATH = os.path.join(BASE_DIR, "chung_chi_goc.pdf")
FONT_PATH = os.path.join(BASE_DIR, "FreeMonoOblique.ttf")

# Fallback fonts nếu không có font đi kèm
FONT_FALLBACKS = [
    "/usr/share/fonts/truetype/freefont/FreeMonoOblique.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Oblique.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Italic.ttf",
]

def get_font_path():
    if os.path.exists(FONT_PATH):
        return FONT_PATH
    for fp in FONT_FALLBACKS:
        if os.path.exists(fp):
            return fp
    return None

def make_date_str(date_str=None):
    """Chuyển 'YYYY-MM-DD' hoặc dùng ngày hôm nay"""
    months = ['January','February','March','April','May','June',
              'July','August','September','October','November','December']
    try:
        d = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        d = datetime.date.today()
    day = d.day
    suffix = "th" if 11 <= day <= 13 else {1:"st",2:"nd",3:"rd"}.get(day % 10, "th")
    return f"{months[d.month-1]} {day}{suffix}, {d.year}"

def generate_pdf(name: str, date_str: str) -> bytes:
    """
    Tạo PDF chứng chỉ với tên và ngày mới.

    Template gốc (chung_chi_goc.pdf) đã được làm sạch sẵn — không có text.
    Chỉ cần render thành ảnh (flatten) rồi chèn text mới lên trên.
    Tên được căn giữa và tự động thu nhỏ nếu quá dài.
    """
    # --- Bước 1: Render template thành ảnh nền (flatten — không có text layer) ---
    tmp_doc = fitz.open(PDF_PATH)
    tmp_page = tmp_doc[0]
    mat = fitz.Matrix(2.0, 2.0)  # 2× zoom ≈ 144 DPI, giữ chất lượng tốt
    pix = tmp_page.get_pixmap(matrix=mat, alpha=False)
    tmp_doc.close()

    # --- Bước 2: Tạo PDF mới từ ảnh nền ---
    orig_w, orig_h = 1417.3228759765625, 1000.6299438476562
    new_doc = fitz.open()
    new_page = new_doc.new_page(width=orig_w, height=orig_h)
    new_page.insert_image(fitz.Rect(0, 0, orig_w, orig_h), pixmap=pix)

    # --- Bước 3: Chèn tên mới — căn giữa + tự thu nhỏ nếu tên dài ---
    name_upper = name.upper()
    name_color = (209/255, 16/255, 0/255)  # #D11000 - đỏ gốc

    # Vùng tên nằm từ x=225 đến x=730 (center=477.5), baseline y=594
    zone_left, zone_right = 225, 730
    zone_center = (zone_left + zone_right) / 2
    max_width = zone_right - zone_left - 10
    baseline_y = 594
    fontsize = 60

    font_path = get_font_path()
    if font_path:
        font = fitz.Font(fontfile=font_path)
        # Thu nhỏ font cho đến khi vừa vùng
        while font.text_length(name_upper, fontsize=fontsize) > max_width and fontsize > 20:
            fontsize -= 1
        tw = font.text_length(name_upper, fontsize=fontsize)
        start_x = zone_center - tw / 2
        new_page.insert_text((start_x, baseline_y), name_upper,
                             fontfile=font_path, fontname="NameFont",
                             fontsize=fontsize, color=name_color)
    else:
        # Fallback: Helvetica nếu không có FreeMonoOblique
        tw = fitz.get_text_length(name_upper, fontname="helv", fontsize=fontsize)
        while tw > max_width and fontsize > 20:
            fontsize -= 1
            tw = fitz.get_text_length(name_upper, fontname="helv", fontsize=fontsize)
        start_x = zone_center - tw / 2
        new_page.insert_text((start_x, baseline_y), name_upper,
                             fontname="helv", fontsize=fontsize, color=name_color)

    # --- Bước 4: Chèn ngày mới ---
    new_page.insert_text((751, 793), make_date_str(date_str),
                         fontname="helv", fontsize=25, color=(0, 0, 0))

    buf = io.BytesIO()
    new_doc.save(buf, garbage=4, deflate=True)
    new_doc.close()
    return buf.getvalue()


@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")

@app.route("/preview", methods=["POST"])
def preview():
    """Trả về PDF đã chỉnh sửa để xem trước trong trình duyệt"""
    data = request.get_json()
    name = (data.get("name") or "").strip()
    date_str = (data.get("date") or "")
    if not name:
        return jsonify({"error": "Vui lòng nhập tên"}), 400
    pdf_bytes = generate_pdf(name, date_str)
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=False,
        download_name="preview.pdf"
    )

@app.route("/download", methods=["POST"])
def download():
    """Trả về PDF để tải về"""
    data = request.get_json()
    name = (data.get("name") or "").strip()
    date_str = (data.get("date") or "")
    if not name:
        return jsonify({"error": "Vui lòng nhập tên"}), 400
    pdf_bytes = generate_pdf(name, date_str)
    safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in name)
    filename = f"chung_chi_{safe.replace(' ', '_')}.pdf"
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename
    )

if __name__ == "__main__":
    print("=" * 55)
    print("  Chứng chỉ Save the Children - Trình chỉnh sửa")
    print("  Truy cập: http://localhost:5000")
    print("=" * 55)
    app.run(debug=False, port=5000)
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
    doc = fitz.open(PDF_PATH)
    page = doc[0]

    # Xóa text cũ (tên + ngày)
    page.add_redact_annot(fitz.Rect(225, 538, 730, 618), fill=(1, 1, 1))
    page.add_redact_annot(fitz.Rect(745, 758, 975, 802), fill=(1, 1, 1))
    page.apply_redactions()

    font_path = get_font_path()
    name_color = (209/255, 16/255, 0/255)  # #D11000 - đỏ gốc

    # Ghi tên mới - đúng font FreeMonoOblique, đúng màu đỏ
    kw = dict(fontsize=60, color=name_color)
    if font_path:
        kw["fontfile"] = font_path
        kw["fontname"] = "NameFont"
    else:
        kw["fontname"] = "helv"

    page.insert_text((239, 600), name.upper(), **kw)

    # Ghi ngày mới - Helvetica đen
    page.insert_text((751, 793), make_date_str(date_str),
                     fontname="helv", fontsize=25, color=(0, 0, 0))

    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
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

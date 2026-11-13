import io
import os
import zipfile

import pymupdf as fitz
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def make_pdf(pages: int = 3) -> bytes:
    doc = fitz.open()
    for i in range(pages):
        doc.new_page().insert_text((72, 72), f"Page {i + 1}")
    return doc.tobytes()


def noisy_image_pdf() -> bytes:
    """A PDF with a big photo-like image, so compression has something to shrink."""
    pix = fitz.Pixmap(fitz.csRGB, 800, 800, os.urandom(800 * 800 * 3), False)
    doc = fitz.open()
    page = doc.new_page(width=200, height=200)
    page.insert_image(page.rect, stream=pix.tobytes("png"))
    return doc.tobytes()


def file(name: str, data: bytes):
    return ("files", (name, data))


def pages_of(content: bytes) -> int:
    return len(fitz.open(stream=content, filetype="pdf"))


def test_split_keeps_chosen_pages():
    r = client.post("/api/split", files=[file("a.pdf", make_pdf(5))], data={"pages": "1-2,5"})
    assert r.status_code == 200 and pages_of(r.content) == 3


def test_split_bad_format():
    r = client.post("/api/split", files=[file("a.pdf", make_pdf(2))], data={"pages": "abc"})
    assert r.status_code == 400


def test_split_page_out_of_range():
    r = client.post("/api/split", files=[file("a.pdf", make_pdf(2))], data={"pages": "9"})
    assert r.status_code == 400 and "2 pages" in r.json()["detail"]


def test_rotate():
    r = client.post("/api/rotate", files=[file("a.pdf", make_pdf(2))], data={"angle": "90"})
    assert r.status_code == 200
    assert fitz.open(stream=r.content, filetype="pdf")[0].rotation == 90


def test_rotate_bad_angle():
    r = client.post("/api/rotate", files=[file("a.pdf", make_pdf(1))], data={"angle": "45"})
    assert r.status_code == 400


def test_compress_makes_file_smaller():
    original = noisy_image_pdf()
    r = client.post("/api/compress", files=[file("a.pdf", original)], data={"level": "high"})
    assert r.status_code == 200 and len(r.content) < len(original)


def test_pdf_to_images_zip():
    r = client.post("/api/pdf2img", files=[file("a.pdf", make_pdf(3))], data={"fmt": "png"})
    assert r.status_code == 200
    assert len(zipfile.ZipFile(io.BytesIO(r.content)).namelist()) == 3


def test_images_to_pdf():
    png = fitz.Pixmap(fitz.csRGB, 50, 50, bytes(50 * 50 * 3), False).tobytes("png")
    r = client.post("/api/img2pdf", files=[file("a.png", png), file("b.png", png)])
    assert r.status_code == 200 and pages_of(r.content) == 2


def test_images_to_pdf_rejects_text_file():
    r = client.post("/api/img2pdf", files=[file("a.png", b"hello")])
    assert r.status_code == 400


def test_watermark_ok_and_unsupported_letters():
    ok = client.post("/api/watermark", files=[file("a.pdf", make_pdf(1))], data={"text": "Nexuz"})
    assert ok.status_code == 200
    bad = client.post("/api/watermark", files=[file("a.pdf", make_pdf(1))], data={"text": "Ğ"})
    assert bad.status_code == 400

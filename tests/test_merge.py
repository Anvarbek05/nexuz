import fitz
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def make_pdf(pages: int) -> bytes:
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()
    return doc.tobytes()


def upload(name: str, data: bytes):
    return ("files", (name, data, "application/pdf"))


def test_merge_two_pdfs():
    r = client.post("/api/merge", files=[upload("a.pdf", make_pdf(2)), upload("b.pdf", make_pdf(3))])
    assert r.status_code == 200
    assert len(fitz.open(stream=r.content, filetype="pdf")) == 5


def test_merge_needs_two_files():
    r = client.post("/api/merge", files=[upload("a.pdf", make_pdf(1))])
    assert r.status_code == 400
    assert "at least 2" in r.json()["detail"]


def test_merge_rejects_fake_pdf():
    r = client.post("/api/merge", files=[upload("a.pdf", make_pdf(1)), upload("fake.pdf", b"not a pdf")])
    assert r.status_code == 400
    assert "fake.pdf" in r.json()["detail"]

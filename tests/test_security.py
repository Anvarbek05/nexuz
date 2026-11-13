import pymupdf as fitz
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def make_pdf() -> bytes:
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "secret")
    return doc.tobytes()


def file(data: bytes):
    return ("files", ("a.pdf", data))


def test_protect_then_unlock():
    locked = client.post("/api/protect", files=[file(make_pdf())], data={"password": "pass1234"})
    assert locked.status_code == 200
    doc = fitz.open(stream=locked.content, filetype="pdf")
    assert doc.needs_pass

    opened = client.post("/api/unlock", files=[file(locked.content)], data={"password": "pass1234"})
    assert opened.status_code == 200
    assert not fitz.open(stream=opened.content, filetype="pdf").needs_pass


def test_unlock_wrong_password():
    locked = client.post("/api/protect", files=[file(make_pdf())], data={"password": "pass1234"})
    r = client.post("/api/unlock", files=[file(locked.content)], data={"password": "nope"})
    assert r.status_code == 400 and "Wrong password" in r.json()["detail"]


def test_unlock_pdf_without_password():
    r = client.post("/api/unlock", files=[file(make_pdf())], data={"password": "x"})
    assert r.status_code == 400 and "no password" in r.json()["detail"]


def test_protect_short_password():
    r = client.post("/api/protect", files=[file(make_pdf())], data={"password": "ab"})
    assert r.status_code == 400

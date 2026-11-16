"""Uzbek converter: upload a PDF or TXT file."""
import pymupdf as fitz
import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def pdf_with(text: str | None) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    if text:
        page.insert_text((72, 72), text)
    return doc.tobytes()


def upload(client, name, data, headers=None):
    return client.post("/api/uzbek/convert-file", files={"file": (name, data)}, headers=headers or {})


def test_txt_file_comes_back_in_all_three_alphabets(client):
    r = upload(client, "a.txt", "Салом дунё".encode("utf-8"))
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "cyrillic" and set(body["texts"]) == {"cyrillic", "latin", "latin_new"}
    assert body["texts"]["latin"].lower().startswith("salom dun")
    assert body["texts"]["cyrillic"] == "Салом дунё"


def test_txt_file_in_windows_cyrillic_encoding(client):
    r = upload(client, "a.txt", "Салом дунё".encode("cp1251"))
    assert r.status_code == 200 and r.json()["texts"]["latin"].lower().startswith("salom dun")


def test_pdf_with_text_works(client):
    r = upload(client, "a.pdf", pdf_with("Salom dunyo"))
    assert r.status_code == 200
    body = r.json()
    assert body["pages"] == 1 and body["source"] == "latin"
    assert body["texts"]["cyrillic"].startswith("Салом дун")


def test_scanned_pdf_without_text_gives_a_clear_error(client):
    r = upload(client, "scan.pdf", pdf_with(None), headers={"X-Lang": "en"})
    assert r.status_code == 400 and "scanned" in r.json()["detail"]


def test_wrong_file_type_and_broken_pdf(client):
    assert upload(client, "a.docx", b"hello", headers={"X-Lang": "en"}).status_code == 400
    r = upload(client, "a.pdf", b"%PDF-1.4 broken", headers={"X-Lang": "en"})
    assert r.status_code == 400 and "not a valid PDF" in r.json()["detail"]


def test_a_file_counts_as_one_use_of_the_daily_limit(client, monkeypatch):
    monkeypatch.setitem(config.PLANS["guest"], "per_day", 1)
    assert upload(client, "a.txt", b"salom").status_code == 200
    r = upload(client, "a.txt", b"salom", headers={"X-Lang": "en"})
    assert r.status_code == 429 and "free uses" in r.json()["detail"]
    # typing text on the page is not limited by the daily limit
    assert client.post("/api/uzbek/convert", json={"text": "salom", "target": "cyrillic"}).status_code == 200


def test_too_much_text_is_refused(client, monkeypatch):
    monkeypatch.setattr(config, "UZBEK_FILE_MAX_CHARS", 10)
    r = upload(client, "a.txt", b"salom dunyo, salom", headers={"X-Lang": "en"})
    assert r.status_code == 400 and "too much text" in r.json()["detail"]


def test_converter_page_has_the_upload_button(client):
    html = client.get("/en/uzbek-alphabet-converter").text
    assert 'id="uz-file"' in html and 'id="uz-download"' in html and 'id="theme-toggle"' in html

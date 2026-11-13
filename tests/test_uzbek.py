import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.uzbek import convert, detect_script

client = TestClient(app)


@pytest.mark.parametrize("text, target, expected", [
    # current Latin -> new Latin
    ("O‘zbekiston, G‘alaba, shahar, choy", "latin_new", "Özbekiston, Ğalaba, şahar, çoy"),
    ("O'zbek g`alaba Shahar CHOY", "latin_new", "Özbek ğalaba Şahar ÇOY"),
    ("ma'no, e'lon", "latin_new", "maʼno, eʼlon"),
    # new Latin -> current Latin
    ("Özbekiston, Ğalaba, şahar, çoy", "latin", "Oʻzbekiston, Gʻalaba, shahar, choy"),
    ("ÖZBEK ŞAHAR", "latin", "OʻZBEK SHAHAR"),
    ("Şahar", "latin", "Shahar"),
    # Cyrillic -> Latin
    ("Ўзбекистон, Ғалаба, шаҳар, чой", "latin_new", "Özbekiston, Ğalaba, şahar, çoy"),
    ("Ўзбекистон, Ғалаба, шаҳар, чой", "latin", "Oʻzbekiston, Gʻalaba, shahar, choy"),
    ("ТОШКЕНТ ШАҲРИ", "latin_new", "TOŞKENT ŞAHRI"),
    ("Эълон, ёзув, енгил, республика, станция, рецепт", "latin",
     "Eʼlon, yozuv, yengil, respublika, stansiya, retsept"),
    # Latin -> Cyrillic (old, new, or mixed)
    ("O‘zbekiston, ma'no, ertalab, yengil, yaxshi, ayol, Toshkent", "cyrillic",
     "Ўзбекистон, маъно, эрталаб, енгил, яхши, аёл, Тошкент"),
    ("SHAHAR O'ZBEK CHOY", "cyrillic", "ШАҲАР ЎЗБЕК ЧОЙ"),
    ("Özbekiston Şahar Çoy Ğalaba", "cyrillic", "Ўзбекистон Шаҳар Чой Ғалаба"),
    # quotes must stay quotes, numbers and punctuation untouched
    ("Men 'salom' dedim. 2027-yil!", "cyrillic", "Мен 'салом' дедим. 2027-йил!"),
])
def test_convert(text, target, expected):
    assert convert(text, target) == expected


def test_round_trip_current_latin_to_new_and_back():
    text = "Oʻzbekiston Gʻalaba shahar choy"
    assert convert(convert(text, "latin_new"), "latin") == text


def test_detect_script():
    assert detect_script("Ўзбек") == "cyrillic"
    assert detect_script("Özbek") == "latin_new"
    assert detect_script("O'zbek") == "latin"
    assert detect_script("") == "latin"


def test_api_converts_and_detects():
    r = client.post("/api/uzbek/convert", json={"text": "Шаҳар", "target": "latin_new"})
    assert r.status_code == 200
    assert r.json() == {"text": "Şahar", "source": "cyrillic"}


def test_api_rejects_bad_target_and_huge_text():
    assert client.post("/api/uzbek/convert", json={"text": "a", "target": "greek"}).status_code == 422
    assert client.post("/api/uzbek/convert", json={"text": "a" * 20001, "target": "latin"}).status_code == 422

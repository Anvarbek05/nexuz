import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import LANGS
from app.i18n import get_locale
from app.main import app
from app.tools import TOOLS

client = TestClient(app)
LOCALES = Path(__file__).resolve().parent.parent / "app" / "locales"


def keys(node, prefix=""):
    found = set()
    for k, v in node.items():
        found.add(prefix + k)
        if isinstance(v, dict):
            found |= keys(v, prefix + k + ".")
    return found


def test_all_languages_have_the_same_text_keys():
    en = keys(json.loads((LOCALES / "en.json").read_text(encoding="utf-8")))
    for lang in LANGS:
        other = keys(json.loads((LOCALES / f"{lang}.json").read_text(encoding="utf-8")))
        assert other == en, f"{lang} differs from en: {sorted(other ^ en)}"


@pytest.mark.parametrize("lang", LANGS)
def test_home_page_in_every_language(lang):
    r = client.get(f"/{lang}/")
    assert r.status_code == 200
    ui = get_locale(lang)["ui"]
    assert ui["hero_title"] in r.text
    assert f'<html lang="{lang}">' in r.text
    assert f'rel="canonical" href="https://nexuz-vtcb.onrender.com/{lang}/"' in r.text
    for other in LANGS:                                  # hreflang links to every language
        assert f'hreflang="{other}"' in r.text
    assert r.text.count('class="card"') == len(TOOLS)    # every tool is a real link, visible to Google


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("tool", TOOLS, ids=lambda t: t["slug"])
def test_every_tool_page_exists_in_every_language(lang, tool):
    r = client.get(f"/{lang}/{tool['slug']}")
    assert r.status_code == 200
    text = get_locale(lang)["tools"][tool["id"]]
    assert f"<h1>{text['name']}</h1>" in r.text
    assert f"<title>{text['seo_title']} | Nexuz</title>" in r.text
    assert "application/ld+json" in r.text
    assert text["steps"][0] in r.text                    # the how-to steps are in the HTML itself


def test_unknown_pages_give_404():
    assert client.get("/uz/nope").status_code == 404
    assert client.get("/xx/").status_code == 404
    assert "Sahifa topilmadi" in client.get("/uz/nope").text
    assert client.get("/api/nothing").json() == {"detail": "Not Found"}


def test_sitemap_and_robots():
    sm = client.get("/sitemap.xml")
    assert sm.status_code == 200 and "xml" in sm.headers["content-type"]
    assert sm.text.count("<url>") == len(LANGS) * (len(TOOLS) + 1)
    assert "/ru/merge-pdf" in sm.text
    robots = client.get("/robots.txt").text
    assert "Sitemap: https://nexuz-vtcb.onrender.com/sitemap.xml" in robots


def test_icons_and_static_files():
    assert client.get("/favicon.svg").status_code == 200
    assert client.get("/favicon.ico").status_code == 200
    assert client.get("/static/css/style.css").status_code == 200
    assert client.get("/static/js/app.js").status_code == 200
    assert client.get("/static/img/og-image.png").status_code == 200


def test_uzbek_interface_can_switch_to_the_new_alphabet():
    old = get_locale("uz", False)
    new = get_locale("uz", True)
    assert old["tools"]["merge"]["steps"][0] == "Ikki yoki undan ortiq PDF fayl qoʻshing."
    assert new["tools"]["merge"]["steps"][0] == "Ikki yoki undan ortiq PDF fayl qöşing."
    assert new["ui"]["uz_opt_latin"] == old["ui"]["uz_opt_latin"]       # texts about the old letters stay
    assert "Oʻ, Gʻ, Sh va Ch" in new["ui"]["uz_note_body"]

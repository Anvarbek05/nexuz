"""Accounts, limits, translated errors and the new pages, through the real web app."""
import pymupdf as fitz
import pytest
from fastapi.testclient import TestClient

from app import config
from app.config import LANGS
from app.errors import translate
from app.i18n import get_locale
from app.main import app
from app.routers import pages
from app.services import limits

GOOD = "correct horse battery"


@pytest.fixture
def client():
    return TestClient(app)          # a new browser (empty cookies) for every test


def make_pdf() -> bytes:
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "hello")
    return doc.tobytes()


def merge(client, headers=None):
    files = [("files", ("a.pdf", make_pdf())), ("files", ("b.pdf", make_pdf()))]
    return client.post("/api/merge", files=files, headers=headers or {})


def register(client, email="a@b.cd", password=GOOD, headers=None):
    return client.post("/api/auth/register", json={"email": email, "password": password}, headers=headers or {})


# ---------------------------------------------------------------- accounts
def test_register_signs_you_in(client):
    r = register(client)
    assert r.status_code == 200 and r.json()["user"]["email"] == "a@b.cd"
    cookie = r.headers["set-cookie"].lower()
    assert config.SESSION_COOKIE in cookie and "httponly" in cookie and "samesite=lax" in cookie
    me = client.get("/api/me").json()
    assert me["user"]["email"] == "a@b.cd" and me["user"]["plan"] == "free"
    assert me["quota"]["per_day"] == config.PLANS["free"]["per_day"]


def test_me_without_signing_in(client):
    me = client.get("/api/me").json()
    assert me["user"] is None and me["quota"]["plan"] == "guest"


def test_register_errors_come_back_translated(client):
    r = register(client, email="nope")
    assert r.status_code == 400 and r.json()["code"] == "bad_email"
    assert r.json()["detail"] == translate("en", "bad_email")
    r = register(client, email="a@b.cd", password="short", headers={"X-Lang": "ru"})
    assert r.status_code == 400 and r.json()["detail"] == translate("ru", "password_short", {"min": config.PASSWORD_MIN})
    assert register(client).status_code == 200
    r = register(TestClient(app), headers={"X-Lang": "uz"})
    assert r.status_code == 409 and r.json()["detail"] == translate("uz", "email_taken")


def test_login_logout(client):
    register(client)
    client.post("/api/auth/logout")
    assert client.get("/api/me").json()["user"] is None
    bad = client.post("/api/auth/login", json={"email": "a@b.cd", "password": "wrong password"})
    assert bad.status_code == 401 and bad.json()["code"] == "wrong_login"
    good = client.post("/api/auth/login", json={"email": "A@B.cd", "password": GOOD})
    assert good.status_code == 200
    assert client.get("/api/me").json()["user"]["email"] == "a@b.cd"


def test_too_many_wrong_passwords_are_stopped(client):
    register(client)
    codes = [client.post("/api/auth/login", json={"email": "a@b.cd", "password": "wrong password"}).status_code
             for _ in range(12)]
    assert codes[:10] == [401] * 10 and codes[10] == 429


def test_delete_account_needs_the_password(client):
    register(client)
    assert client.post("/api/auth/delete", json={"password": "wrong password"}).status_code == 401
    assert client.post("/api/auth/delete", json={"password": GOOD}).status_code == 200
    assert client.get("/api/me").json()["user"] is None
    assert client.post("/api/auth/login", json={"email": "a@b.cd", "password": GOOD}).status_code == 401


def test_delete_account_when_not_signed_in(client):
    assert client.post("/api/auth/delete", json={"password": GOOD}).status_code == 401


def test_other_websites_cannot_act_for_you(client):
    r = client.post("/api/auth/login", json={"email": "a@b.cd", "password": GOOD}, headers={"Origin": "https://evil.example"})
    assert r.status_code == 403 and r.json()["code"] == "forbidden"
    r = client.post("/api/auth/login", json={"email": "a@b.cd", "password": GOOD}, headers={"Origin": "http://testserver"})
    assert r.status_code == 401        # allowed through; the login itself fails because there is no such user


# ---------------------------------------------------------------- limits
def test_guest_limit_then_account_gives_more(client, monkeypatch):
    monkeypatch.setitem(config.PLANS["guest"], "per_day", 2)
    assert merge(client).status_code == 200
    assert merge(client).status_code == 200
    blocked = merge(client, {"X-Lang": "en"})
    assert blocked.status_code == 429 and blocked.json()["code"] == "daily_limit_guest"
    assert client.get("/api/me").json()["quota"]["left"] == 0
    register(client)                                   # a free account has its own, bigger limit
    assert merge(client).status_code == 200
    assert client.get("/api/me").json()["quota"]["used"] == 1


def test_failed_operations_do_not_use_up_the_limit(client, monkeypatch):
    monkeypatch.setitem(config.PLANS["guest"], "per_day", 2)
    bad = client.post("/api/merge", files=[("files", ("x.pdf", b"nope")), ("files", ("y.pdf", b"nope"))])
    assert bad.status_code == 400
    assert client.get("/api/me").json()["quota"]["used"] == 0


def test_file_size_limit_message(client, monkeypatch):
    monkeypatch.setitem(config.PLANS["guest"], "max_mb", 0)
    r = merge(client)
    assert r.status_code == 413 and r.json()["code"] == "file_too_big_guest" and "a.pdf" in r.json()["detail"]


def test_speed_limit(client):
    for _ in range(60):
        limits.speed.hit("api", "testclient", 60, 60)
    r = merge(client)
    assert r.status_code == 429 and r.json()["code"] == "slow_down"


def test_premium_by_admin_address(client, monkeypatch):
    register(client)
    body = {"email": "a@b.cd", "days": 30}
    monkeypatch.setattr(config, "ADMIN_TOKEN", "")
    assert client.post("/api/admin/premium", json=body).status_code == 404          # switched off
    monkeypatch.setattr(config, "ADMIN_TOKEN", "secret-word")
    assert client.post("/api/admin/premium", json=body, headers={"X-Admin-Token": "wrong"}).status_code == 403
    r = client.post("/api/admin/premium", json=body, headers={"X-Admin-Token": "secret-word"})
    assert r.status_code == 200 and r.json()["premium_until"]
    quota = client.get("/api/me").json()["quota"]
    assert quota["plan"] == "premium" and quota["per_day"] is None
    r = client.post("/api/admin/premium", json={**body, "days": 0}, headers={"X-Admin-Token": "secret-word"})
    assert client.get("/api/me").json()["quota"]["plan"] == "free"


def test_client_ip_is_counted_from_the_right_side(client, monkeypatch):
    monkeypatch.setattr(config, "ADMIN_TOKEN", "secret-word")
    headers = {"X-Admin-Token": "secret-word", "X-Forwarded-For": "6.6.6.6, 9.9.9.9, 8.8.8.8, 7.7.7.7"}
    assert client.get("/api/admin/ip", headers=headers).json()["client_ip"] == "testclient"     # no proxies by default
    monkeypatch.setattr(config, "PROXY_HOPS", 3)
    assert client.get("/api/admin/ip", headers=headers).json()["client_ip"] == "9.9.9.9"       # a fake "6.6.6.6" is ignored
    monkeypatch.setattr(config, "PROXY_HOPS", 9)
    assert client.get("/api/admin/ip", headers=headers).json()["client_ip"] == "testclient"     # header too short: ignore it


# ---------------------------------------------------------------- translated tool errors
def test_pdf_errors_are_translated(client):
    files = [("files", ("fake.pdf", b"nope")), ("files", ("b.pdf", b"nope"))]
    english = client.post("/api/merge", files=files)
    assert english.json()["detail"] == "fake.pdf is not a valid PDF file."
    for lang in ("uz", "ru"):
        r = client.post("/api/merge", files=files, headers={"X-Lang": lang})
        assert r.status_code == 400 and r.json()["detail"] == translate(lang, "invalid_pdf", {"name": "fake.pdf"})
        assert r.json()["code"] == "invalid_pdf"


# ---------------------------------------------------------------- pages
@pytest.mark.parametrize("lang", LANGS)
def test_login_and_register_pages(client, lang):
    ui = get_locale(lang)["ui"]
    for mode in ("login", "register"):
        r = client.get(f"/{lang}/{mode}")
        assert r.status_code == 200 and "noindex" in r.text
        assert ui[f"acc_{mode}_title"] in r.text and f'data-mode="{mode}"' in r.text
        assert ui["nav_login"] in r.text            # the header shows "Sign in" for a guest


def test_account_page_needs_sign_in_and_shows_your_data(client):
    r = client.get("/uz/account", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "/uz/login"
    register(client)
    r = client.get("/uz/account")
    assert r.status_code == 200 and "a@b.cd" in r.text and "noindex" in r.text
    assert get_locale("uz")["ui"]["nav_account"] in r.text
    r = client.get("/uz/login", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "/uz/account"


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("slug", ["pricing", "privacy", "terms"])
def test_public_info_pages(client, lang, slug):
    r = client.get(f"/{lang}/{slug}")
    assert r.status_code == 200 and "noindex" not in r.text
    assert f'rel="canonical" href="https://nexuz-vtcb.onrender.com/{lang}/{slug}"' in r.text
    for other in LANGS:
        assert f'hreflang="{other}"' in r.text
    if slug == "pricing":
        assert get_locale(lang)["pricing"]["title"] in r.text
    else:
        assert get_locale(lang)["legal"][slug]["title"] in r.text


def test_sitemap_lists_public_pages_but_not_private_ones(client):
    text = client.get("/sitemap.xml").text
    assert "/en/privacy" in text and "/ru/terms" in text and "/uz/pricing" in text
    assert "/login" not in text and "/register" not in text and "/account" not in text


def test_contact_email_appears_only_when_set(client, monkeypatch):
    assert "mailto:" not in client.get("/en/privacy").text
    monkeypatch.setattr(pages, "CONTACT_EMAIL", "hello@example.com")
    assert 'href="mailto:hello@example.com"' in client.get("/en/privacy").text


def test_google_search_console_code(client, monkeypatch):
    assert "google-site-verification" not in client.get("/en/").text
    monkeypatch.setattr(pages, "GOOGLE_SITE_VERIFICATION", "abc123")
    assert '<meta name="google-site-verification" content="abc123">' in client.get("/en/").text


def test_tool_page_knows_the_visitors_limits(client):
    page = client.get("/en/merge-pdf").text
    assert 'id="quota"' in page and '"plan": "guest"' in page and '"lang": "en"' in page
    register(client)
    assert '"plan": "free"' in client.get("/en/merge-pdf").text


def test_footer_links_on_every_page(client):
    html = client.get("/ru/").text
    for slug in ("pricing", "privacy", "terms"):
        assert f'href="/ru/{slug}"' in html


def test_register_is_refused_on_render_without_a_database(client, monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    r = register(client, headers={"X-Lang": "en"})
    assert r.status_code == 503 and "not available" in r.json()["detail"]

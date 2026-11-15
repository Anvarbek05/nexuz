"""Payment routes through the real web app (Click and Payme calling our server, and the "Pay" button)."""
import base64

import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app
from app.services import accounts, payments

GOOD = "correct horse battery"


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def providers_on(monkeypatch):
    monkeypatch.setattr(config, "CLICK_SERVICE_ID", "111")
    monkeypatch.setattr(config, "CLICK_MERCHANT_ID", "222")
    monkeypatch.setattr(config, "CLICK_SECRET_KEY", "cs")
    monkeypatch.setattr(config, "PAYME_MERCHANT_ID", "m1")
    monkeypatch.setattr(config, "PAYME_KEY", "pk")


def sign_in(client, email="a@b.cd"):
    assert client.post("/api/auth/register", json={"email": email, "password": GOOD}).status_code == 200


def test_pay_button_needs_sign_in_and_gives_a_link(client):
    r = client.post("/api/pay/create", json={"provider": "payme"}, headers={"X-Lang": "uz"})
    assert r.status_code == 401 and "kiring" in r.json()["detail"].lower()
    sign_in(client)
    r = client.post("/api/pay/create", json={"provider": "payme"})
    assert r.status_code == 200 and r.json()["url"].startswith("https://checkout.paycom.uz/")
    assert client.post("/api/pay/create", json={"provider": "visa"}).status_code == 422


def test_pay_button_is_off_when_provider_has_no_keys(client, monkeypatch):
    sign_in(client)
    monkeypatch.setattr(config, "PAYME_KEY", "")
    r = client.post("/api/pay/create", json={"provider": "payme"}, headers={"X-Lang": "en"})
    assert r.status_code == 400 and "not available" in r.json()["detail"]


def test_click_calls_reach_our_server_without_cookies(client):
    sign_in(client)
    order = payments.create_order(accounts.get_user_by_email("a@b.cd"), "click")

    def form(action, **extra):
        data = {"click_trans_id": "55", "service_id": "111", "click_paydoc_id": "1", "merchant_trans_id": order["id"],
                "amount": "29000", "action": str(action), "error": "0", "sign_time": "2026-11-14 10:00:00"}
        if action == 1:
            data["merchant_prepare_id"] = str(int(order["id"][:7], 16))
        data.update(extra)
        data["sign_string"] = extra.get("sign_string") or payments.click_sign(data, "cs")
        return data

    server = TestClient(app)                     # Click's server has no cookies
    assert server.post("/api/pay/click/prepare", data=form(0)).json()["error"] == 0
    assert server.post("/api/pay/click/complete", data=form(1)).json()["error"] == 0
    assert accounts.is_premium(accounts.get_user_by_email("a@b.cd"))
    assert server.post("/api/pay/click/prepare", data=form(0, sign_string="bad")).json()["error"] == -1


def test_payme_calls_always_get_http_200(client):
    server = TestClient(app)
    r = server.post("/api/pay/payme", json={"id": 1, "method": "CheckTransaction", "params": {"id": "x"}})
    assert r.status_code == 200 and r.json()["error"]["code"] == -32504          # no key
    header = {"Authorization": "Basic " + base64.b64encode(b"Paycom:pk").decode()}
    r = server.post("/api/pay/payme", content=b"not json", headers=header)
    assert r.status_code == 200 and r.json()["error"]["code"] == -32600
    r = server.post("/api/pay/payme", json={"id": 1, "method": "CheckTransaction", "params": {"id": "x"}}, headers=header)
    assert r.status_code == 200 and r.json()["error"]["code"] == -31003


def test_pricing_page_shows_pay_buttons_only_when_signed_in(client):
    assert 'data-pay="' not in client.get("/en/pricing").text
    sign_in(client)
    html = client.get("/en/pricing").text
    assert 'data-pay="click"' in html and 'data-pay="payme"' in html and "29 000" in html


def test_pricing_page_without_keys_says_coming_soon(client, monkeypatch):
    monkeypatch.setattr(config, "CLICK_SECRET_KEY", "")
    monkeypatch.setattr(config, "PAYME_KEY", "")
    html = client.get("/en/pricing").text
    assert "data-pay=" not in html and "Coming soon" in html

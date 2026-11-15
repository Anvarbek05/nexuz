"""Tests for the payment logic (Click and Payme). They do not need the web server.
They check our code against the providers' documented rules. They do NOT replace testing in the providers' sandbox."""
import base64
import hashlib

import pytest

from app import config, db
from app.services import accounts, payments

KEY = "secret-key"


@pytest.fixture(autouse=True)
def providers_on(monkeypatch):
    monkeypatch.setattr(config, "CLICK_SERVICE_ID", "111")
    monkeypatch.setattr(config, "CLICK_MERCHANT_ID", "222")
    monkeypatch.setattr(config, "CLICK_SECRET_KEY", "click-secret")
    monkeypatch.setattr(config, "PAYME_MERCHANT_ID", "merchant-1")
    monkeypatch.setattr(config, "PAYME_KEY", KEY)
    monkeypatch.setattr(config, "PREMIUM_PRICE_SUM", 29000)


@pytest.fixture
def user():
    return accounts.create_user("buyer@example.com", "correct horse battery")


def premium(email="buyer@example.com"):
    return accounts.is_premium(accounts.get_user_by_email(email))


def test_providers_are_off_without_all_keys(monkeypatch):
    assert config.payment_providers() == ["click", "payme"]
    monkeypatch.setattr(config, "CLICK_SECRET_KEY", "")
    monkeypatch.setattr(config, "PAYME_KEY", "")
    assert config.payment_providers() == []


def test_cannot_create_order_for_a_provider_that_is_off(user, monkeypatch):
    monkeypatch.setattr(config, "PAYME_KEY", "")
    with pytest.raises(Exception) as err:
        payments.create_order(user, "payme")
    assert err.value.code == "pay_provider_off"


def test_checkout_urls(user):
    order = payments.create_order(user, "payme")
    assert order["amount"] == 2900000 and order["state"] == 0
    url = payments.checkout_url(order, "uz")
    assert url.startswith("https://checkout.paycom.uz/")
    raw = base64.b64decode(url.rsplit("/", 1)[1]).decode()
    assert f"m=merchant-1;ac.order_id={order['id']};a=2900000" in raw
    click = payments.checkout_url(payments.create_order(user, "click"), "en")
    assert click.startswith("https://my.click.uz/services/pay?") and "amount=29000.00" in click


# ================================================================ Click
def click_form(order, action, **over):
    form = {"click_trans_id": "9001", "service_id": "111", "click_paydoc_id": "5", "merchant_trans_id": order["id"],
            "amount": "29000.0", "action": str(action), "error": "0", "error_note": "Success",
            "sign_time": "2026-11-14 10:00:00"}
    if action == 1:
        form["merchant_prepare_id"] = str(int(order["id"][:7], 16))
    form.update(over)
    form["sign_string"] = over.get("sign_string") or payments.click_sign(form, "click-secret")
    return form


def test_click_sign_matches_the_documented_formula(user):
    order = payments.create_order(user, "click")
    form = click_form(order, 0)
    expected = hashlib.md5(
        f"9001111click-secret{order['id']}29000.0" "0" "2026-11-14 10:00:00".encode()).hexdigest()
    assert form["sign_string"] == expected
    done = click_form(order, 1)
    expected = hashlib.md5(
        f"9001111click-secret{order['id']}{done['merchant_prepare_id']}29000.0" "1" "2026-11-14 10:00:00".encode()).hexdigest()
    assert done["sign_string"] == expected


def test_click_full_payment_gives_premium_once(user):
    order = payments.create_order(user, "click")
    prepared = payments.click_handle(0, click_form(order, 0))
    assert prepared["error"] == 0 and prepared["merchant_prepare_id"] == int(order["id"][:7], 16)
    assert not premium()
    done = payments.click_handle(1, click_form(order, 1))
    assert done["error"] == 0 and premium()
    until = accounts.get_user_by_email("buyer@example.com")["premium_until"]
    again = payments.click_handle(1, click_form(order, 1))             # Click repeats the call
    assert again["error"] == -4
    assert accounts.get_user_by_email("buyer@example.com")["premium_until"] == until   # no second gift


def test_click_wrong_signature_amount_and_order(user):
    order = payments.create_order(user, "click")
    assert payments.click_handle(0, click_form(order, 0, sign_string="0" * 32))["error"] == -1
    assert payments.click_handle(0, click_form(order, 0, amount="100"))["error"] == -2
    assert payments.click_handle(0, click_form(order, 0, merchant_trans_id="nope"))["error"] == -5
    assert payments.click_handle(1, click_form(order, 0))["error"] == -3        # prepare sent to /complete
    assert payments.click_handle(0, click_form(order, 0, service_id="999"))["error"] in (-1, -8)


def test_click_complete_without_prepare_and_cancel(user):
    order = payments.create_order(user, "click")
    assert payments.click_handle(1, click_form(order, 1))["error"] == -6
    payments.click_handle(0, click_form(order, 0))
    cancelled = payments.click_handle(1, click_form(order, 1, error="-5017"))
    assert cancelled["error"] == -9 and not premium()
    assert payments.click_handle(0, click_form(order, 0))["error"] == -9   # a cancelled order cannot be reused


def test_click_order_of_another_provider_is_refused(user):
    order = payments.create_order(user, "payme")
    assert payments.click_handle(0, click_form(order, 0))["error"] == -5


# ================================================================ Payme
def auth(key=KEY):
    return "Basic " + base64.b64encode(f"Paycom:{key}".encode()).decode()


def rpc(method, params, header="default"):
    return payments.payme_handle({"jsonrpc": "2.0", "id": 7, "method": method, "params": params},
                                 auth() if header == "default" else header)


def test_payme_needs_the_right_key(user):
    order = payments.create_order(user, "payme")
    params = {"amount": order["amount"], "account": {"order_id": order["id"]}}
    for header in (None, "", "Basic abc", auth("wrong"), "Bearer x"):
        assert rpc("CheckPerformTransaction", params, header=header)["error"]["code"] == -32504
    assert rpc("CheckPerformTransaction", params)["result"] == {"allow": True}


def test_payme_check_errors(user):
    order = payments.create_order(user, "payme")
    good = {"order_id": order["id"]}
    assert rpc("CheckPerformTransaction", {"amount": 1, "account": good})["error"]["code"] == -31001
    assert rpc("CheckPerformTransaction", {"amount": order["amount"], "account": {"order_id": "x"}})["error"]["code"] == -31050
    assert rpc("CheckPerformTransaction", {"amount": order["amount"]})["error"]["code"] == -31050
    assert rpc("Nope", {})["error"]["code"] == -32601
    assert payments.payme_handle([], auth())["error"]["code"] == -32600
    error = rpc("CheckPerformTransaction", {"amount": 1, "account": good})["error"]
    assert set(error["message"]) == {"ru", "uz", "en"}


def test_payme_full_flow_gives_premium_once(user):
    order = payments.create_order(user, "payme")
    params = {"id": "tx-1", "time": 1, "amount": order["amount"], "account": {"order_id": order["id"]}}
    created = rpc("CreateTransaction", params)["result"]
    assert created["state"] == 1 and created["transaction"] == order["id"]
    assert rpc("CreateTransaction", params)["result"]["create_time"] == created["create_time"]   # same answer again
    assert not premium()
    done = rpc("PerformTransaction", {"id": "tx-1"})["result"]
    assert done["state"] == 2 and done["perform_time"] > 0 and premium()
    until = accounts.get_user_by_email("buyer@example.com")["premium_until"]
    assert rpc("PerformTransaction", {"id": "tx-1"})["result"]["perform_time"] == done["perform_time"]
    assert accounts.get_user_by_email("buyer@example.com")["premium_until"] == until
    check = rpc("CheckTransaction", {"id": "tx-1"})["result"]
    assert check["state"] == 2 and check["reason"] is None and check["cancel_time"] == 0
    # a paid order cannot start a new transaction, and a paid transaction cannot be cancelled
    other = dict(params, id="tx-2")
    assert rpc("CreateTransaction", other)["error"]["code"] == -31051
    assert rpc("CancelTransaction", {"id": "tx-1", "reason": 5})["error"]["code"] == -31007


def test_payme_second_transaction_for_a_busy_order_is_refused(user):
    order = payments.create_order(user, "payme")
    params = {"id": "tx-1", "time": 1, "amount": order["amount"], "account": {"order_id": order["id"]}}
    rpc("CreateTransaction", params)
    assert rpc("CreateTransaction", dict(params, id="tx-2"))["error"]["code"] == -31008


def test_payme_cancel_before_payment(user):
    order = payments.create_order(user, "payme")
    rpc("CreateTransaction", {"id": "tx-1", "time": 1, "amount": order["amount"], "account": {"order_id": order["id"]}})
    result = rpc("CancelTransaction", {"id": "tx-1", "reason": 3})["result"]
    assert result["state"] == -1 and result["cancel_time"] > 0
    assert rpc("CheckTransaction", {"id": "tx-1"})["result"]["reason"] == 3
    assert rpc("PerformTransaction", {"id": "tx-1"})["error"]["code"] == -31008
    assert not premium()
    assert rpc("CheckTransaction", {"id": "unknown"})["error"]["code"] == -31003


def test_payme_transaction_expires_after_12_hours(user, monkeypatch):
    order = payments.create_order(user, "payme")
    rpc("CreateTransaction", {"id": "tx-1", "time": 1, "amount": order["amount"], "account": {"order_id": order["id"]}})
    real = payments.now_ms()
    monkeypatch.setattr(payments, "now_ms", lambda: real + payments.PAYME_TIMEOUT_MS + 1000)
    assert rpc("PerformTransaction", {"id": "tx-1"})["error"]["code"] == -31008
    state = rpc("CheckTransaction", {"id": "tx-1"})["result"]
    assert state["state"] == -1 and state["reason"] == 4 and not premium()


def test_payme_statement_lists_transactions(user):
    order = payments.create_order(user, "payme")
    rpc("CreateTransaction", {"id": "tx-1", "time": 1, "amount": order["amount"], "account": {"order_id": order["id"]}})
    rows = rpc("GetStatement", {"from": 0, "to": payments.now_ms() + 1000})["result"]["transactions"]
    assert len(rows) == 1 and rows[0]["id"] == "tx-1" and rows[0]["account"] == {"order_id": order["id"]}
    assert rpc("GetStatement", {"from": "a", "to": 1})["error"]["code"] == -32600


def test_paid_order_for_a_deleted_user_does_not_crash(user):
    order = payments.create_order(user, "click")
    payments.click_handle(0, click_form(order, 0))
    accounts.delete_user(user)
    assert payments.click_handle(1, click_form(order, 1))["error"] == 0
    assert db.query_one("SELECT state FROM orders WHERE id = ?", (order["id"],))["state"] == 2

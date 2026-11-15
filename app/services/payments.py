"""Premium payments with Click and Payme. No web framework code here, so it is easy to test.

HOW IT WORKS
 1. A signed-in user presses "Pay". We create an ORDER (a row in `orders`) and send the user to the provider's page.
 2. The provider's server then calls OUR server (Click: prepare + complete; Payme: JSON-RPC methods).
 3. When the provider says "money received", we give the user Premium (accounts.set_premium) exactly once.

Order states:  0 new   1 started (provider reserved it)   2 paid   -1 cancelled   -2 cancelled after paid.
Money is stored in tiyin (1 soum = 100 tiyin), like Payme does.

IMPORTANT: written from the providers' public documentation, but NOT yet tested against their real test
servers. Test every step in the Click / Payme sandbox before you accept real money (see HOW_TO_UPDATE.md).
"""
import base64
import hashlib
import hmac
import time
import uuid
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from app import config, db
from app.errors import ApiError
from app.services import accounts

PAYME_TIMEOUT_MS = 12 * 60 * 60 * 1000   # Payme: a started transaction must finish within 12 hours


def now_ms() -> int:
    return int(time.time() * 1000)


# ---------------------------------------------------------------- orders
def amount_tiyin() -> int:
    return config.PREMIUM_PRICE_SUM * 100


def create_order(user: dict, provider: str) -> dict:
    if provider not in config.payment_providers():
        raise ApiError(400, "pay_provider_off")
    order_id = uuid.uuid4().hex
    db.execute(
        "INSERT INTO orders (id, user_id, provider, days, amount, state, created_at) VALUES (?, ?, ?, ?, ?, 0, ?)",
        (order_id, user["id"], provider, config.PREMIUM_DAYS, amount_tiyin(), accounts.iso(accounts.now())))
    return get_order(order_id)


def get_order(order_id) -> dict | None:
    if not isinstance(order_id, str) or not order_id:
        return None
    return db.query_one("SELECT * FROM orders WHERE id = ?", (order_id,))


def _get_by_ptx(provider: str, ptx_id: str) -> dict | None:
    return db.query_one("SELECT * FROM orders WHERE provider = ? AND ptx_id = ?", (provider, str(ptx_id)))


def _give_premium(order: dict) -> None:
    user = db.query_one("SELECT email FROM users WHERE id = ?", (order["user_id"],))
    if user:    # the user may have deleted the account after paying: nothing to give then
        accounts.set_premium(user["email"], order["days"])


def _mark_paid(order: dict) -> bool:
    """started -> paid, exactly once (the WHERE state = 1 protects against two calls at the same moment)."""
    changed = db.execute("UPDATE orders SET state = 2, perform_time = ? WHERE id = ? AND state = 1",
                         (now_ms(), order["id"]))
    if changed:
        _give_premium(order)
    return bool(changed)


def checkout_url(order: dict, lang: str) -> str:
    """Where we send the user to pay."""
    back = config.SITE_URL.rstrip("/") + f"/{lang}/account"
    if order["provider"] == "payme":
        raw = f"m={config.PAYME_MERCHANT_ID};ac.order_id={order['id']};a={order['amount']};l={lang};c={back}"
        host = "checkout.test.paycom.uz" if config.PAYME_TEST else "checkout.paycom.uz"
        return f"https://{host}/" + base64.b64encode(raw.encode()).decode()
    query = urlencode({
        "service_id": config.CLICK_SERVICE_ID, "merchant_id": config.CLICK_MERCHANT_ID,
        "amount": f"{order['amount'] / 100:.2f}", "transaction_param": order["id"], "return_url": back})
    return "https://my.click.uz/services/pay?" + query


# ================================================================ Click (SHOP-API)
CLICK_NOTES = {0: "Success", -1: "SIGN CHECK FAILED!", -2: "Incorrect parameter amount", -3: "Action not found",
               -4: "Already paid", -5: "User does not exist", -6: "Transaction does not exist",
               -7: "Failed to update user", -8: "Error in request from click", -9: "Transaction cancelled"}


def _click_int(order: dict) -> int:
    """Click wants a whole-number id from us (merchant_prepare_id). We make one from the order id."""
    return int(order["id"][:7], 16)


def click_sign(form: dict, secret: str) -> str:
    """md5 of the values glued together, in Click's documented order. Complete has one extra value."""
    parts = [form.get("click_trans_id", ""), form.get("service_id", ""), secret, form.get("merchant_trans_id", "")]
    if str(form.get("action")) == "1":
        parts.append(form.get("merchant_prepare_id", ""))
    parts += [form.get("amount", ""), form.get("action", ""), form.get("sign_time", "")]
    return hashlib.md5("".join(str(p) for p in parts).encode()).hexdigest()


def _click_answer(form: dict, error: int, **extra) -> dict:
    answer = {"click_trans_id": form.get("click_trans_id"), "merchant_trans_id": form.get("merchant_trans_id"),
              "error": error, "error_note": CLICK_NOTES[error]}
    answer.update(extra)
    return answer


def click_handle(expected_action: int, form: dict) -> dict:
    """Handle one request from Click. `expected_action` is 0 for /prepare and 1 for /complete."""
    form = {k: (v if isinstance(v, str) else str(v)) for k, v in form.items()}
    secret = config.CLICK_SECRET_KEY
    if not secret or "click" not in config.payment_providers():
        return _click_answer(form, -8)
    given = form.get("sign_string", "")
    if not hmac.compare_digest(given.encode(), click_sign(form, secret).encode()):
        return _click_answer(form, -1)
    if form.get("service_id") != str(config.CLICK_SERVICE_ID):
        return _click_answer(form, -8)
    if form.get("action") != str(expected_action):
        return _click_answer(form, -3)

    order = get_order(form.get("merchant_trans_id"))
    if order is None or order["provider"] != "click":
        return _click_answer(form, -5)
    try:
        if Decimal(form.get("amount", "")) * 100 != order["amount"]:
            return _click_answer(form, -2)
    except InvalidOperation:
        return _click_answer(form, -8)
    if order["state"] == 2:
        return _click_answer(form, -4)
    if order["state"] < 0:
        return _click_answer(form, -9)

    if expected_action == 0:                                   # ---- prepare: reserve the order
        if order["state"] == 1 and order["ptx_id"] != form["click_trans_id"]:
            return _click_answer(form, -4)                     # another payment attempt is already running
        db.execute("UPDATE orders SET state = 1, ptx_id = ?, create_time = ? WHERE id = ?",
                   (form["click_trans_id"], now_ms(), order["id"]))
        return _click_answer(form, 0, merchant_prepare_id=_click_int(order))

    # ---- complete: Click says the money moved (error 0) or the payment failed (error below 0)
    if order["state"] != 1 or order["ptx_id"] != form["click_trans_id"]:
        return _click_answer(form, -6)
    if form.get("merchant_prepare_id") != str(_click_int(order)):
        return _click_answer(form, -6)
    try:
        failed = int(form.get("error", "0")) < 0
    except ValueError:
        return _click_answer(form, -8)
    if failed:
        db.execute("UPDATE orders SET state = -1, cancel_time = ?, reason = ? WHERE id = ? AND state = 1",
                   (now_ms(), int(form["error"]), order["id"]))
        return _click_answer(form, -9)
    _mark_paid(order)
    return _click_answer(form, 0, merchant_confirm_id=_click_int(order))


# ================================================================ Payme (Merchant API, JSON-RPC 2.0)
class PaymeError(Exception):
    def __init__(self, code: int, ru: str, uz: str, en: str, data=None):
        super().__init__(en)
        self.code, self.message, self.data = code, {"ru": ru, "uz": uz, "en": en}, data


def _no_order():
    return PaymeError(-31050, "Заказ не найден", "Buyurtma topilmadi", "Order not found", "order_id")


def _order_closed():
    return PaymeError(-31051, "Заказ уже оплачен или отменён", "Buyurtma toʻlangan yoki bekor qilingan",
                      "Order is already paid or cancelled", "order_id")


def _wrong_amount():
    return PaymeError(-31001, "Неверная сумма", "Notoʻgʻri summa", "Wrong amount")


def _cannot():
    return PaymeError(-31008, "Невозможно выполнить операцию", "Amalni bajarib boʻlmaydi", "Cannot perform this operation")


def _no_transaction():
    return PaymeError(-31003, "Транзакция не найдена", "Tranzaksiya topilmadi", "Transaction not found")


def _payme_order(params: dict) -> dict:
    account = params.get("account")
    order = get_order(account.get("order_id")) if isinstance(account, dict) else None
    if order is None or order["provider"] != "payme":
        raise _no_order()
    return order


def _payme_check(params: dict) -> dict:
    order = _payme_order(params)
    if order["state"] not in (0, 1):
        raise _order_closed()
    if params.get("amount") != order["amount"]:
        raise _wrong_amount()
    return order


def _payme_expired(order: dict) -> bool:
    return now_ms() - order["create_time"] > PAYME_TIMEOUT_MS


def _payme_cancel_expired(order: dict) -> None:
    db.execute("UPDATE orders SET state = -1, cancel_time = ?, reason = 4 WHERE id = ? AND state = 1",
               (now_ms(), order["id"]))


def _payme_find(params: dict) -> dict:
    order = _get_by_ptx("payme", params.get("id"))
    if order is None:
        raise _no_transaction()
    return order


def _payme_state(order: dict) -> dict:
    return {"create_time": order["create_time"], "perform_time": order["perform_time"],
            "cancel_time": order["cancel_time"], "transaction": order["id"], "state": order["state"],
            "reason": order["reason"]}


def _m_check_perform(params):
    _payme_check(params)
    return {"allow": True}


def _m_create(params):
    existing = _get_by_ptx("payme", params.get("id"))
    if existing is not None:                                   # Payme asks again: answer the same
        if existing["state"] != 1:
            raise _cannot()
        if _payme_expired(existing):
            _payme_cancel_expired(existing)
            raise _cannot()
        return {"create_time": existing["create_time"], "transaction": existing["id"], "state": 1}
    order = _payme_check(params)
    if order["state"] == 1:                                    # another Payme transaction already holds this order
        raise _cannot()
    started = now_ms()
    changed = db.execute("UPDATE orders SET state = 1, ptx_id = ?, create_time = ? WHERE id = ? AND state = 0",
                         (str(params.get("id")), started, order["id"]))
    if not changed:
        raise _cannot()
    return {"create_time": started, "transaction": order["id"], "state": 1}


def _m_perform(params):
    order = _payme_find(params)
    if order["state"] == 2:
        return {"transaction": order["id"], "perform_time": order["perform_time"], "state": 2}
    if order["state"] != 1:
        raise _cannot()
    if _payme_expired(order):
        _payme_cancel_expired(order)
        raise _cannot()
    _mark_paid(order)
    order = get_order(order["id"])
    return {"transaction": order["id"], "perform_time": order["perform_time"], "state": order["state"]}


def _m_cancel(params):
    order = _payme_find(params)
    if order["state"] == 1:
        db.execute("UPDATE orders SET state = -1, cancel_time = ?, reason = ? WHERE id = ? AND state = 1",
                   (now_ms(), params.get("reason"), order["id"]))
    elif order["state"] == 2:
        # Money was already taken and Premium given. Refunds are done by hand (see HOW_TO_UPDATE.md).
        raise PaymeError(-31007, "Заказ выполнен. Невозможно откатить транзакцию",
                         "Buyurtma bajarilgan. Tranzaksiyani qaytarib boʻlmaydi",
                         "Order is completed. The transaction cannot be cancelled")
    order = get_order(order["id"])
    return {"transaction": order["id"], "cancel_time": order["cancel_time"], "state": order["state"]}


def _m_check(params):
    return _payme_state(_payme_find(params))


def _m_statement(params):
    start, end = params.get("from"), params.get("to")
    if not isinstance(start, int) or not isinstance(end, int):
        raise PaymeError(-32600, "Неверный запрос", "Notoʻgʻri soʻrov", "Invalid request")
    rows = db.query_all("SELECT * FROM orders WHERE provider = 'payme' AND ptx_id IS NOT NULL "
                        "AND create_time >= ? AND create_time <= ? ORDER BY create_time", (start, end))
    return {"transactions": [dict(_payme_state(r), id=r["ptx_id"], time=r["create_time"], amount=r["amount"],
                                  account={"order_id": r["id"]}) for r in rows]}


PAYME_METHODS = {"CheckPerformTransaction": _m_check_perform, "CreateTransaction": _m_create,
                 "PerformTransaction": _m_perform, "CancelTransaction": _m_cancel,
                 "CheckTransaction": _m_check, "GetStatement": _m_statement}


def _payme_authorised(header: str | None) -> bool:
    if not config.PAYME_KEY or not header or not header.startswith("Basic "):
        return False
    try:
        login, _, password = base64.b64decode(header[6:], validate=True).decode().partition(":")
    except Exception:
        return False
    return hmac.compare_digest(login.encode(), b"Paycom") and hmac.compare_digest(password.encode(), config.PAYME_KEY.encode())


def payme_handle(payload, auth_header: str | None) -> dict:
    """Handle one JSON-RPC request from Payme. Always returns a dict; the HTTP status must be 200 (Payme's rule)."""
    request_id = payload.get("id") if isinstance(payload, dict) else None

    def fail(error: PaymeError) -> dict:
        body = {"code": error.code, "message": error.message}
        if error.data is not None:
            body["data"] = error.data
        return {"jsonrpc": "2.0", "id": request_id, "error": body}

    if "payme" not in config.payment_providers() or not _payme_authorised(auth_header):
        return fail(PaymeError(-32504, "Недостаточно привилегий для выполнения метода",
                               "Amalni bajarish uchun huquq yetarli emas", "Insufficient privilege to perform this method"))
    if not isinstance(payload, dict) or not isinstance(payload.get("params"), dict):
        return fail(PaymeError(-32600, "Неверный запрос", "Notoʻgʻri soʻrov", "Invalid request"))
    method = PAYME_METHODS.get(payload.get("method"))
    if method is None:
        return fail(PaymeError(-32601, "Метод не найден", "Metod topilmadi", "Method not found", payload.get("method")))
    try:
        return {"jsonrpc": "2.0", "id": request_id, "result": method(payload["params"])}
    except PaymeError as error:
        return fail(error)

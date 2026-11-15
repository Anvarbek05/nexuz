"""Accounts: users, passwords, sign-in sessions and Premium. No web code here, so it is easy to test.

Passwords are never stored. We store a scrypt hash (scrypt is built into Python, nothing to install).
The sign-in cookie holds a random token; the database holds only a SHA-256 of it, so a stolen
database cannot be used to sign in.
"""
import hashlib
import hmac
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from app import config, db
from app.errors import ApiError

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_SCRYPT = {"n": 2 ** 14, "r": 8, "p": 1}
_DUMMY_HASH = None


def now() -> datetime:
    return datetime.now(timezone.utc)


def iso(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


# ---------------------------------------------------------------- passwords
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, maxmem=64 * 1024 * 1024, dklen=32, **_SCRYPT)
    return f"scrypt${_SCRYPT['n']}${_SCRYPT['r']}${_SCRYPT['p']}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, n, r, p, salt_hex, digest_hex = stored.split("$")
        digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=int(n), r=int(r), p=int(p),
                                maxmem=64 * 1024 * 1024, dklen=len(digest_hex) // 2)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


def _dummy_hash() -> str:
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = hash_password("nexuz-dummy-password")
    return _DUMMY_HASH


# ---------------------------------------------------------------- checks
def clean_email(raw: str) -> str:
    email = (raw or "").strip().lower()
    if len(email) > 254 or not _EMAIL.match(email):
        raise ApiError(400, "bad_email")
    return email


def check_password(password: str, email: str = "") -> None:
    if not isinstance(password, str) or len(password) < config.PASSWORD_MIN:
        raise ApiError(400, "password_short", min=config.PASSWORD_MIN)
    if len(password) > config.PASSWORD_MAX:
        raise ApiError(400, "password_long", max=config.PASSWORD_MAX)
    if email and password.lower() == email:
        raise ApiError(400, "password_is_email")


# ---------------------------------------------------------------- users
def get_user_by_email(email: str) -> dict | None:
    return db.query_one("SELECT * FROM users WHERE email = ?", (email,))


def create_user(email: str, password: str) -> dict:
    email = clean_email(email)
    check_password(password, email)
    if get_user_by_email(email):
        raise ApiError(409, "email_taken")
    user_id = str(uuid.uuid4())
    try:
        db.execute("INSERT INTO users (id, email, password_hash, premium_until, created_at) VALUES (?, ?, ?, ?, ?)",
                   (user_id, email, hash_password(password), None, iso(now())))
    except Exception:
        # Two people registering the same email at the same moment: the UNIQUE rule of the database stops one.
        if get_user_by_email(email):
            raise ApiError(409, "email_taken")
        raise
    return db.query_one("SELECT * FROM users WHERE id = ?", (user_id,))


def authenticate(email: str, password: str) -> dict:
    """Return the user, or raise the same error for a wrong email and a wrong password."""
    user = get_user_by_email((email or "").strip().lower())
    stored = user["password_hash"] if user else _dummy_hash()   # same work either way (hides which emails exist)
    ok = verify_password(password or "", stored)
    if not user or not ok:
        raise ApiError(401, "wrong_login")
    return user


def delete_user(user: dict) -> None:
    db.execute("DELETE FROM sessions WHERE user_id = ?", (user["id"],))
    db.execute("DELETE FROM usage WHERE subject = ?", (user_subject(user),))
    db.execute("DELETE FROM users WHERE id = ?", (user["id"],))


def user_subject(user: dict) -> str:
    return "u:" + user["id"]


# ---------------------------------------------------------------- sessions
def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    created = now()
    db.execute("INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
               (_token_hash(token), user_id, iso(created), iso(created + timedelta(days=config.SESSION_DAYS))))
    return token


def user_for_token(token: str | None) -> dict | None:
    if not token:
        return None
    row = db.query_one(
        "SELECT u.*, s.expires_at AS session_expires FROM sessions s JOIN users u ON u.id = s.user_id "
        "WHERE s.token_hash = ?", (_token_hash(token),))
    if row is None:
        return None
    if row["session_expires"] <= iso(now()):
        end_session(token)
        return None
    row.pop("session_expires", None)
    return row


def end_session(token: str | None) -> None:
    if token:
        db.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))


def cleanup() -> None:
    """Remove old data. Called now and then (at sign-in), so no scheduler is needed."""
    db.execute("DELETE FROM sessions WHERE expires_at <= ?", (iso(now()),))
    oldest = (now() + timedelta(hours=config.DAY_UTC_OFFSET_HOURS) - timedelta(days=3)).date().isoformat()
    db.execute("DELETE FROM usage WHERE day < ?", (oldest,))


# ---------------------------------------------------------------- Premium
def is_premium(user: dict | None) -> bool:
    until = (user or {}).get("premium_until")
    return bool(until) and until > iso(now())


def plan_of(user: dict | None) -> str:
    if user is None:
        return "guest"
    return "premium" if is_premium(user) else "free"


def set_premium(email: str, days: int) -> dict:
    """Give `days` more days of Premium (added after the current end, if still active). days=0 removes Premium."""
    user = get_user_by_email((email or "").strip().lower())
    if user is None:
        raise ApiError(404, "user_not_found")
    if days <= 0:
        db.execute("UPDATE users SET premium_until = NULL WHERE id = ?", (user["id"],))
    else:
        start = max(now(), datetime.fromisoformat(user["premium_until"])) if is_premium(user) else now()
        db.execute("UPDATE users SET premium_until = ? WHERE id = ?", (iso(start + timedelta(days=days)), user["id"]))
    return db.query_one("SELECT * FROM users WHERE id = ?", (user["id"],))

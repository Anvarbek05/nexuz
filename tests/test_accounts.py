"""Accounts, sessions, Premium and limits. These tests talk to the code directly (no web server)."""
from datetime import timedelta

import pytest

from app import config, db
from app.errors import ApiError, pick_language
from app.services import accounts, limits

GOOD = "correct horse battery"


def code_of(call, *args):
    with pytest.raises(ApiError) as caught:
        call(*args)
    return caught.value.code


# ---------------------------------------------------------------- passwords
def test_password_hash_is_not_the_password_and_verifies():
    stored = accounts.hash_password(GOOD)
    assert GOOD not in stored
    assert accounts.verify_password(GOOD, stored)
    assert not accounts.verify_password("wrong", stored)
    assert accounts.hash_password(GOOD) != stored          # new random salt every time


def test_verify_password_survives_garbage():
    assert accounts.verify_password("x", "not a hash") is False
    assert accounts.verify_password("x", "scrypt$a$b$c$zz$yy") is False


# ---------------------------------------------------------------- users
def test_create_user_cleans_the_email():
    user = accounts.create_user("  Person@Example.COM ", GOOD)
    assert user["email"] == "person@example.com"
    assert user["premium_until"] is None
    assert accounts.get_user_by_email("person@example.com")["id"] == user["id"]


@pytest.mark.parametrize("email", ["", "no-at-sign", "a@b", "a b@c.de", "x" * 250 + "@a.bc"])
def test_bad_emails_are_refused(email):
    assert code_of(accounts.create_user, email, GOOD) == "bad_email"


def test_bad_passwords_are_refused():
    assert code_of(accounts.create_user, "a@b.cd", "short") == "password_short"
    assert code_of(accounts.create_user, "a@b.cd", "x" * (config.PASSWORD_MAX + 1)) == "password_long"
    assert code_of(accounts.create_user, "longer@example.com", "longer@example.com") == "password_is_email"


def test_same_email_cannot_register_twice():
    accounts.create_user("a@b.cd", GOOD)
    assert code_of(accounts.create_user, "A@B.CD", GOOD) == "email_taken"


def test_login_checks_the_password_and_hides_which_part_was_wrong():
    accounts.create_user("a@b.cd", GOOD)
    assert accounts.authenticate("A@b.cd ", GOOD)["email"] == "a@b.cd"
    assert code_of(accounts.authenticate, "a@b.cd", "wrong password") == "wrong_login"
    assert code_of(accounts.authenticate, "nobody@b.cd", GOOD) == "wrong_login"   # same error: no email guessing


# ---------------------------------------------------------------- sessions
def test_session_token_finds_the_user_and_is_stored_hashed():
    user = accounts.create_user("a@b.cd", GOOD)
    token = accounts.create_session(user["id"])
    assert accounts.user_for_token(token)["id"] == user["id"]
    assert accounts.user_for_token("some other token") is None
    assert accounts.user_for_token(None) is None
    assert token not in str(db.query_all("SELECT * FROM sessions"))      # only a hash is stored


def test_logout_and_expiry():
    user = accounts.create_user("a@b.cd", GOOD)
    token = accounts.create_session(user["id"])
    accounts.end_session(token)
    assert accounts.user_for_token(token) is None

    token = accounts.create_session(user["id"])
    old = accounts.iso(accounts.now() - timedelta(minutes=1))
    db.execute("UPDATE sessions SET expires_at = ?", (old,))
    assert accounts.user_for_token(token) is None


def test_cleanup_removes_expired_sessions_and_old_counters():
    user = accounts.create_user("a@b.cd", GOOD)
    accounts.create_session(user["id"])
    db.execute("UPDATE sessions SET expires_at = ?", (accounts.iso(accounts.now() - timedelta(days=1)),))
    db.execute("INSERT INTO usage (day, subject, uses) VALUES ('2000-01-01', 'ip:x', 3)")
    limits.Ticket(user, "1.1.1.1").done()
    accounts.cleanup()
    assert db.query_all("SELECT * FROM sessions") == []
    assert [r["day"] for r in db.query_all("SELECT day FROM usage")] == [limits.today()]


def test_delete_user_removes_everything_about_them():
    user = accounts.create_user("a@b.cd", GOOD)
    accounts.create_session(user["id"])
    limits.Ticket(user, "1.1.1.1").done()
    accounts.delete_user(user)
    assert db.query_all("SELECT * FROM users") == []
    assert db.query_all("SELECT * FROM sessions") == []
    assert db.query_all("SELECT * FROM usage") == []


# ---------------------------------------------------------------- Premium
def test_premium_can_be_given_extended_and_removed():
    accounts.create_user("a@b.cd", GOOD)
    assert accounts.plan_of(None) == "guest"
    assert accounts.plan_of(accounts.get_user_by_email("a@b.cd")) == "free"

    first = accounts.set_premium("a@b.cd", 30)
    assert accounts.plan_of(first) == "premium"
    second = accounts.set_premium("a@b.cd", 30)                # added AFTER the first 30 days
    gap = accounts.datetime.fromisoformat(second["premium_until"]) - accounts.datetime.fromisoformat(first["premium_until"])
    assert gap == timedelta(days=30)

    assert accounts.plan_of(accounts.set_premium("a@b.cd", 0)) == "free"
    assert code_of(accounts.set_premium, "nobody@b.cd", 5) == "user_not_found"


def test_expired_premium_is_just_a_free_account():
    user = accounts.create_user("a@b.cd", GOOD)
    db.execute("UPDATE users SET premium_until = ?", (accounts.iso(accounts.now() - timedelta(days=1)),))
    assert accounts.plan_of(accounts.get_user_by_email(user["email"])) == "free"


# ---------------------------------------------------------------- limits
def test_daily_limit_counts_only_what_is_done_and_is_per_person(monkeypatch):
    monkeypatch.setitem(config.PLANS["guest"], "per_day", 2)
    me, other = limits.Ticket(None, "1.1.1.1"), limits.Ticket(None, "2.2.2.2")
    me.check()
    me.check()                                    # checking does not use anything up
    me.done()
    me.done()
    with pytest.raises(ApiError) as caught:
        me.check()
    assert caught.value.status == 429 and caught.value.code == "daily_limit_guest"
    other.check()                                 # another IP has its own counter
    assert me.summary()["left"] == 0 and other.summary()["left"] == 2


def test_guests_are_stored_without_their_ip_address():
    limits.Ticket(None, "203.0.113.77").done()
    assert "203.0.113.77" not in str(db.query_all("SELECT * FROM usage"))


def test_free_and_premium_plans():
    free = accounts.create_user("a@b.cd", GOOD)
    t = limits.Ticket(free, "1.1.1.1")
    assert t.plan == "free" and t.per_day == config.PLANS["free"]["per_day"]
    premium = limits.Ticket(accounts.set_premium("a@b.cd", 5), "1.1.1.1")
    assert premium.plan == "premium" and premium.per_day is None and premium.summary()["left"] is None
    premium.check()


def test_file_size_limit_depends_on_the_plan():
    guest = limits.Ticket(None, "1.1.1.1")
    guest.check_size("a.pdf", guest.max_bytes)                    # exactly the limit is fine
    with pytest.raises(ApiError) as caught:
        guest.check_size("a.pdf", guest.max_bytes + 1)
    assert caught.value.status == 413 and caught.value.code == "file_too_big_guest"
    assert caught.value.params["name"] == "a.pdf"


def test_speed_limit_blocks_and_forgets():
    box = limits.SpeedLimit()
    for _ in range(3):
        box.hit("x", "me", 3, 60)
    with pytest.raises(ApiError) as caught:
        box.hit("x", "me", 3, 60)
    assert caught.value.status == 429 and caught.value.code == "slow_down"
    box.hit("x", "someone else", 3, 60)                           # others are not affected
    box.hit("y", "me", 3, 60)                                     # other names are separate
    box.clear()
    box.hit("x", "me", 3, 60)


# ---------------------------------------------------------------- language of API answers
def test_api_language_choice():
    assert pick_language({"x-lang": "ru"}) == "ru"
    assert pick_language({"x-lang": "xx", "accept-language": "uz-UZ,uz;q=0.9"}) == "uz"
    assert pick_language({"accept-language": "de, ru;q=0.5"}) == "ru"
    assert pick_language({}) == "en"          # nothing known: English, like before Step 6


def test_database_helpers():
    from app import db as database
    assert database.to_postgres_sql("SELECT * FROM t WHERE a = ? AND b = ?") == "SELECT * FROM t WHERE a = %s AND b = %s"
    assert database.is_postgres("postgresql://u:p@host/db") and database.is_postgres("postgres://u:p@host/db")
    assert not database.is_postgres("sqlite:///x.db")


def test_accounts_are_refused_on_render_without_a_real_database(monkeypatch):
    from app import config
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setattr(config, "DATABASE_URL", "sqlite:///data/nexuz.db")
    assert config.accounts_storage_ok() is False
    monkeypatch.setattr(config, "DATABASE_URL", "postgresql://user:pw@host/db")
    assert config.accounts_storage_ok() is True
    monkeypatch.delenv("RENDER")
    monkeypatch.setattr(config, "DATABASE_URL", "sqlite:///data/nexuz.db")
    assert config.accounts_storage_ok() is True          # your own computer is fine

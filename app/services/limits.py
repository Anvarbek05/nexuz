"""Daily limits per plan, and a simple speed limit against abuse. No web framework code here.

Two different things:
  * Daily limit (stored in the database): "5 PDF operations per day for guests". Only SUCCESSFUL operations count.
  * Speed limit (kept in memory): "no more than 60 requests per minute from one IP". Resets when the server restarts.
"""
import hashlib
import threading
import time
from collections import defaultdict, deque
from datetime import timedelta

from app import config, db
from app.errors import ApiError
from app.services import accounts


# ---------------------------------------------------------------- speed limit (memory)
class SpeedLimit:
    def __init__(self):
        self._events: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, name: str, who: str, limit: int, seconds: int, code: str = "slow_down") -> None:
        """Count one event. Raises ApiError(429) when `who` did more than `limit` events in the last `seconds`."""
        key, now = f"{name}:{who}", time.monotonic()
        with self._lock:
            events = self._events[key]
            while events and events[0] <= now - seconds:
                events.popleft()
            if len(events) >= limit:
                raise ApiError(429, code)
            events.append(now)
            if len(self._events) > 20000:   # keep memory small: forget keys that are empty
                for k in [k for k, v in self._events.items() if not v]:
                    del self._events[k]

    def clear(self) -> None:
        with self._lock:
            self._events.clear()


speed = SpeedLimit()


# ---------------------------------------------------------------- daily limit (database)
def today() -> str:
    return (accounts.now() + timedelta(hours=config.DAY_UTC_OFFSET_HOURS)).date().isoformat()


def ip_subject(ip: str) -> str:
    """Guests are counted by IP address. We store only a one-way code, never the address itself."""
    return "ip:" + hashlib.sha256(("nexuz-ip:" + ip).encode()).hexdigest()[:32]


def used_today(subject: str) -> int:
    row = db.query_one("SELECT uses FROM usage WHERE day = ? AND subject = ?", (today(), subject))
    return row["uses"] if row else 0


class Ticket:
    """What one visitor may do right now. Create it with start(), call done() after a successful operation."""

    def __init__(self, user: dict | None, ip: str):
        self.user = user
        self.plan = accounts.plan_of(user)
        self.rules = config.PLANS[self.plan]
        self.subject = accounts.user_subject(user) if user else ip_subject(ip)

    @property
    def max_bytes(self) -> int:
        return self.rules["max_mb"] * 1024 * 1024

    @property
    def per_day(self):
        return self.rules["per_day"]

    def used(self) -> int:
        return used_today(self.subject)

    def check(self) -> None:
        if self.per_day is not None and self.used() >= self.per_day:
            raise ApiError(429, f"daily_limit_{self.plan}", limit=self.per_day, free=config.PLANS["free"]["per_day"])

    def check_size(self, name: str, size: int) -> None:
        if size > self.max_bytes:
            raise ApiError(413, f"file_too_big_{self.plan}", name=name, max=self.rules["max_mb"],
                           free=config.PLANS["free"]["max_mb"], premium=config.PLANS["premium"]["max_mb"])

    def done(self) -> None:
        db.execute(
            "INSERT INTO usage (day, subject, uses) VALUES (?, ?, 1) "
            "ON CONFLICT (day, subject) DO UPDATE SET uses = usage.uses + 1",
            (today(), self.subject))

    def summary(self) -> dict:
        used = self.used()
        left = None if self.per_day is None else max(0, self.per_day - used)
        return {"plan": self.plan, "per_day": self.per_day, "max_mb": self.rules["max_mb"], "used": used, "left": left}


def start(user: dict | None, ip: str) -> Ticket:
    """Call at the beginning of every PDF operation. Raises ApiError if the visitor must wait or slow down."""
    speed.hit("api", ip, 60, 60)
    ticket = Ticket(user, ip)
    ticket.check()
    return ticket

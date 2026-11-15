"""Errors that the website shows to people, in their own language.

Code raises ApiError(status, "code", name="a.pdf"). The error handler in main.py looks up the text
"errors.<code>" in app/locales/<lang>.json and fills in {name}. No visible text lives in Python.
"""
import re

from app.config import LANGS
from app.i18n import get_locale


class ApiError(Exception):
    def __init__(self, status: int, code: str, **params):
        super().__init__(code)
        self.status = status
        self.code = code
        self.params = params


def pick_language(headers, default: str = "en") -> str:
    """Language for an API answer: the X-Lang header (sent by our JavaScript), else Accept-Language, else English."""
    wanted = (headers.get("x-lang") or "").strip().lower()
    if wanted in LANGS:
        return wanted
    for part in (headers.get("accept-language") or "").split(","):
        code = part.split(";")[0].strip().lower()[:2]
        if code in LANGS:
            return code
    return default


def translate(lang: str, code: str, params: dict | None = None, fallback: str | None = None) -> str:
    """Text for an error code. If the code has no text, use `fallback` (English) or the generic text."""
    texts = get_locale(lang)["errors"]
    template = texts.get(code)
    if template is None:
        if fallback:
            return fallback
        template = texts["generic"]
    values = params or {}
    return re.sub(r"\{(\w+)\}", lambda m: str(values.get(m.group(1), "")), template)

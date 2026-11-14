"""Loads the texts of the site from app/locales/<lang>.json."""
import json
from functools import lru_cache
from pathlib import Path

from app.config import LANGS, UZBEK_NEW_ALPHABET
from app.services.uzbek import latin_to_new

LOCALES_DIR = Path(__file__).parent / "locales"

# These texts talk ABOUT the old letters, so they must never be converted.
_KEEP_AS_IS = {"uz_opt_latin", "uz_opt_latin_new", "uz_opt_cyrillic", "uz_note_body", "uz_example_text"}


def _to_new_alphabet(value, key=None):
    if isinstance(value, dict):
        return {k: _to_new_alphabet(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_new_alphabet(v, key) for v in value]
    if isinstance(value, str) and key not in _KEEP_AS_IS:
        return latin_to_new(value)
    return value


@lru_cache(maxsize=None)
def get_locale(lang: str, new_alphabet: bool | None = None) -> dict:
    if lang not in LANGS:
        raise KeyError(lang)
    data = json.loads((LOCALES_DIR / f"{lang}.json").read_text(encoding="utf-8"))
    if new_alphabet is None:
        new_alphabet = UZBEK_NEW_ALPHABET
    if lang == "uz" and new_alphabet:
        data = _to_new_alphabet(data)
    return data

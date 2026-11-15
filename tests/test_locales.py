"""Checks on the text files and on the error codes. These tests do not need the web server."""
import ast
import json
import re
from pathlib import Path

import pytest

from app.config import LANGS
from app.errors import translate

ROOT = Path(__file__).resolve().parent.parent
LOCALES = ROOT / "app" / "locales"


def load(lang):
    return json.loads((LOCALES / f"{lang}.json").read_text(encoding="utf-8"))


def placeholders(text):
    return set(re.findall(r"\{(\w+)\}", text))


def error_codes_in_code():
    """Find every error code written in the Python files: ApiError(400, "code") and PdfToolError("msg", "code", ...)."""
    found = {}
    for path in (ROOT / "app").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
                continue
            index = {"ApiError": 1, "PdfToolError": 1}.get(node.func.id)
            if index is None or len(node.args) <= index:
                continue
            arg = node.args[index]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                found[arg.value] = {kw.arg for kw in node.keywords}
    return found


def test_every_error_code_in_the_code_has_a_text_in_every_language():
    codes = error_codes_in_code()
    assert len(codes) > 20
    for lang in LANGS:
        missing = [c for c in codes if c not in load(lang)["errors"]]
        assert not missing, f"{lang} has no text for: {missing}"


def test_error_texts_only_use_values_the_code_provides():
    for code, given in error_codes_in_code().items():
        wanted = placeholders(load("en")["errors"][code])
        assert wanted <= given, f"{code}: text needs {wanted - given}"


def test_limit_error_codes_exist():     # these two are built from the plan name, so the scan above cannot see them
    for plan in ("guest", "free"):
        for lang in LANGS:
            assert f"daily_limit_{plan}" in load(lang)["errors"]
    for plan in ("guest", "free", "premium"):
        for lang in LANGS:
            assert f"file_too_big_{plan}" in load(lang)["errors"]


@pytest.mark.parametrize("section", ["ui", "errors"])
def test_placeholders_are_the_same_in_all_languages(section):
    en = load("en")[section]
    for lang in ("uz", "ru"):
        other = load(lang)[section]
        for key, text in en.items():
            if isinstance(text, str):
                assert placeholders(other[key]) == placeholders(text), f"{lang}.{section}.{key}"


def test_legal_pages_have_the_same_structure_everywhere():
    en = load("en")["legal"]
    for lang in ("uz", "ru"):
        other = load(lang)["legal"]
        for doc in ("privacy", "terms"):
            assert len(other[doc]["sections"]) == len(en[doc]["sections"])
            for a, b in zip(en[doc]["sections"], other[doc]["sections"]):
                assert len(a["p"]) == len(b["p"])


def test_translate_fills_in_values_and_falls_back():
    assert translate("en", "invalid_pdf", {"name": "a.pdf"}) == "a.pdf is not a valid PDF file."
    assert "a.pdf" in translate("ru", "invalid_pdf", {"name": "a.pdf"})
    assert translate("uz", "no_such_code") == load("uz")["errors"]["generic"]
    assert translate("en", "no_such_code", fallback="English text") == "English text"

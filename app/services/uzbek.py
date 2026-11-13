"""Uzbek alphabet converter: Cyrillic, current Latin (Oʻ Gʻ Sh Ch) and the new Latin (Ö Ğ Ş Ç).

The law signed on 21 October 2026 replaces Oʻ, Gʻ, Sh, Ch with Ö, Ğ, Ş, Ç.
"ng" stops being a separate letter and the apostrophe (tutuq belgisi) stays.
Pure text logic, no web code.
"""
import re

SCRIPTS = ("cyrillic", "latin", "latin_new")

APOSTROPHES = "'`ʻʼ‘’´ʹ′"   # every apostrophe people type or paste
O_MARK = "ʻ"                 # U+02BB, used in oʻ and gʻ (current Latin)
TUTUQ = "ʼ"                  # U+02BC, tutuq belgisi (ma'no, e'lon)
_APOS = re.escape(APOSTROPHES)

# ---- Cyrillic -> Latin ----
_CYR_PLAIN = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "ж": "j", "з": "z", "и": "i",
    "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "x", "э": "e", "ю": "yu", "я": "ya",
    "ё": "yo", "қ": "q", "ҳ": "h", "ы": "i", "щ": "shch", "ъ": TUTUQ, "ь": "",
}
# (current Latin, new Latin)
_CYR_FORMS = {
    "ч": ("ch", "ç"),
    "ш": ("sh", "ş"),
    "ғ": ("g" + O_MARK, "ğ"),
    "ў": ("o" + O_MARK, "ö"),
}
_CYR_VOWELS = set("аоуиэеёюяыў")

# ---- Latin -> Cyrillic ----
_LAT_PLAIN = {
    "a": "а", "b": "б", "d": "д", "f": "ф", "g": "г", "h": "ҳ", "i": "и", "j": "ж",
    "k": "к", "l": "л", "m": "м", "n": "н", "o": "о", "p": "п", "q": "қ", "r": "р",
    "s": "с", "t": "т", "u": "у", "v": "в", "x": "х", "y": "й", "z": "з", "e": "е",
    "ö": "ў", "ğ": "ғ", "ş": "ш", "ç": "ч",
}
_LAT_DIGRAPHS = {"sh": "ш", "ch": "ч", "yo": "ё", "yu": "ю", "ya": "я", "ye": "е"}
_LAT_TOKEN = re.compile(
    rf"sh|ch|yo|yu|ya|ye|[oOgG][{_APOS}]|[{_APOS}]|.", re.IGNORECASE | re.DOTALL
)

# ---- Latin <-> Latin ----
_OLD_FORMS = re.compile(rf"sh|ch|[og][{_APOS}]", re.IGNORECASE)
_TO_NEW = {"sh": "ş", "ch": "ç", "o": "ö", "g": "ğ"}
_NEW_FORMS = re.compile("[öğşçÖĞŞÇ]")
_TO_OLD = {"ö": "o" + O_MARK, "ğ": "g" + O_MARK, "ş": "sh", "ç": "ch"}
_TUTUQ_BETWEEN_LETTERS = re.compile(rf"(?<=\w)[{_APOS}](?=\w)")


def _apply_case(source: str, result: str, prev: str, nxt: str) -> str:
    """Give `result` the capital letters of `source`. Handles Sh / SH / sh."""
    if not result or not source.isupper():
        return result
    if sum(c.isalpha() for c in result) == 1:
        return result.upper()
    if prev.isupper() or nxt.isupper():   # inside an ALL-CAPS word
        return result.upper()
    return result[0].upper() + result[1:]


def detect_script(text: str) -> str:
    if any("\u0400" <= c <= "\u04ff" for c in text):
        return "cyrillic"
    if any(c in "ÖöĞğŞşÇç" for c in text):
        return "latin_new"
    return "latin"


def cyrillic_to_latin(text: str, new: bool = False) -> str:
    out = []
    for i, ch in enumerate(text):
        low = ch.lower()
        prev = text[i - 1] if i else ""
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if low == "е":
            result = "ye" if (not prev.isalpha() or prev.lower() in _CYR_VOWELS) else "e"
        elif low == "ц":
            result = "ts" if prev.lower() in _CYR_VOWELS else "s"
        elif low in _CYR_FORMS:
            result = _CYR_FORMS[low][1 if new else 0]
        elif low in _CYR_PLAIN:
            result = _CYR_PLAIN[low]
        else:
            out.append(ch)
            continue
        out.append(_apply_case(ch, result, prev, nxt))
    return "".join(out)


def latin_to_cyrillic(text: str) -> str:
    """Accepts the current Latin, the new Latin, or a mix of both."""
    def repl(m: re.Match) -> str:
        token = m.group(0)
        low = token.lower()
        start, end = m.start(), m.end()
        prev = text[start - 1] if start else ""
        nxt = text[end] if end < len(text) else ""
        if low in _LAT_DIGRAPHS:
            result = _LAT_DIGRAPHS[low]
        elif len(low) == 2 and low[1] in APOSTROPHES:
            result = "ў" if low[0] == "o" else "ғ"
        elif low in APOSTROPHES:
            # only a tutuq belgisi between two letters; keep quotes as they are
            return "ъ" if prev.isalpha() and nxt.isalpha() else token
        elif low == "e" and not prev.isalpha():
            result = "э"          # word-initial e is э (ertalab -> эрталаб)
        elif low in _LAT_PLAIN:
            result = _LAT_PLAIN[low]
        else:
            return token
        return result.upper() if token[0].isupper() else result
    return _LAT_TOKEN.sub(repl, text)


def latin_to_new(text: str) -> str:
    """Oʻ Gʻ Sh Ch -> Ö Ğ Ş Ç, and tidy every apostrophe."""
    def repl(m: re.Match) -> str:
        token = m.group(0)
        result = _TO_NEW["sh" if token.lower() == "sh" else "ch" if token.lower() == "ch" else token[0].lower()]
        return result.upper() if token[0].isupper() else result
    text = _OLD_FORMS.sub(repl, text)
    return _TUTUQ_BETWEEN_LETTERS.sub(TUTUQ, text)


def latin_new_to_old(text: str) -> str:
    """Ö Ğ Ş Ç -> Oʻ Gʻ Sh Ch. (convert() runs latin_to_new first, which tidies the apostrophes.)"""
    def repl(m: re.Match) -> str:
        ch = m.group(0)
        start, end = m.start(), m.end()
        prev = text[start - 1] if start else ""
        nxt = text[end] if end < len(text) else ""
        return _apply_case(ch, _TO_OLD[ch.lower()], prev, nxt)
    return _NEW_FORMS.sub(repl, text)


def convert(text: str, target: str, source: str = "auto") -> str:
    if target not in SCRIPTS:
        raise ValueError("unknown target script")
    if source == "auto":
        source = detect_script(text)
    if target == "cyrillic":
        return text if source == "cyrillic" else latin_to_cyrillic(text)
    if source == "cyrillic":
        return cyrillic_to_latin(text, new=(target == "latin_new"))
    if target == "latin_new":
        return latin_to_new(text)
    return latin_new_to_old(latin_to_new(text))   # normalises o' -> oʻ too

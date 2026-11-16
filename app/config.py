"""Central settings for Nexuz. Change values here, not inside other files."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

APP_NAME = "Nexuz"
APP_VERSION = "0.7.0"

# Public address of the site. Used in canonical links, sitemap.xml and social previews.
# When you buy a domain, set the SITE_URL environment variable on Render.
SITE_URL = os.getenv("SITE_URL", "https://nexuz-vtcb.onrender.com")

# Interface languages. The first one is the default for visitors we cannot detect.
LANGS = ("uz", "ru", "en")
DEFAULT_LANG = "uz"
LANG_LABELS = {"uz": "Oʻzbekcha", "ru": "Русский", "en": "English"}
LANG_LOCALES = {"uz": "uz_UZ", "ru": "ru_RU", "en": "en_US"}

# From 22 April 2027 the Uzbek interface can switch to the new alphabet (Ö Ğ Ş Ç).
# Set the environment variable UZBEK_NEW_ALPHABET=1 on Render on that day.
UZBEK_NEW_ALPHABET = os.getenv("UZBEK_NEW_ALPHABET", "0") == "1"

# ---------------------------------------------------------------- Step 6: accounts and limits
# Where users are stored. Locally this is a small file (SQLite, nothing to install).
# On Render set DATABASE_URL to a PostgreSQL address, because Render's free disk is erased on every deploy.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///" + (BASE_DIR / "data" / "nexuz.db").as_posix())

def accounts_storage_ok() -> bool:
    """Render's free disk is erased on every restart, so a SQLite file there would silently delete all accounts.
    On Render (it sets RENDER=true) we refuse new accounts until DATABASE_URL points to a real PostgreSQL database."""
    on_render = os.getenv("RENDER", "").lower() == "true"
    return not on_render or DATABASE_URL.startswith(("postgres://", "postgresql://"))


# What each kind of visitor may do. Change the numbers here to change the rules.
#   per_day: how many successful PDF operations per day (None = no limit)
#   max_mb:  biggest single file. Render free has 512 MB RAM, so keep Premium modest.
PLANS = {
    "guest":   {"per_day": 1,    "max_mb": 10},   # not signed in (counted by IP address)
    "free":    {"per_day": 5,    "max_mb": 25},   # free account
    "premium": {"per_day": None, "max_mb": 50},   # paid account
}
MAX_UPLOAD_MB = max(p["max_mb"] for p in PLANS.values())   # absolute ceiling

SESSION_COOKIE = "nexuz_session"
SESSION_DAYS = 30
PASSWORD_MIN = 8
PASSWORD_MAX = 128
DAY_UTC_OFFSET_HOURS = 5   # "a day" ends at midnight in Tashkent (UTC+5)

# How many proxy servers sit between the visitor and Nexuz. We need it to learn the visitor's real IP address
# (for the guest limit). 0 = none (your own computer). On Render check it with /api/admin/ip and set PROXY_HOPS.
PROXY_HOPS = int(os.getenv("PROXY_HOPS", "0") or 0)

# Secret word for the admin address (/api/admin/premium). Leave empty to switch the admin address off.
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

# Shown on the Privacy and Terms pages. Set it on Render, for example CONTACT_EMAIL=hello@yourdomain.uz
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "")

# ---------------------------------------------------------------- Premium and payments (switched OFF until you add keys)
# Premium costs PREMIUM_PRICE_SUM soums for PREMIUM_DAYS days. Change the price on Render with the env var.
PREMIUM_PRICE_SUM = int(os.getenv("PREMIUM_PRICE_SUM", "29000") or 29000)
PREMIUM_DAYS = 30
# Payme Business (cashbox keys). PAYME_TEST=1 uses Payme's test checkout page.
PAYME_MERCHANT_ID = os.getenv("PAYME_MERCHANT_ID", "")
PAYME_KEY = os.getenv("PAYME_KEY", "")
PAYME_TEST = os.getenv("PAYME_TEST", "0") == "1"
# Click (SHOP-API)
CLICK_SERVICE_ID = os.getenv("CLICK_SERVICE_ID", "")
CLICK_MERCHANT_ID = os.getenv("CLICK_MERCHANT_ID", "")
CLICK_SECRET_KEY = os.getenv("CLICK_SECRET_KEY", "")


def payment_providers() -> list[str]:
    """Which payment buttons exist. A provider is on only when ALL its keys are set."""
    found = []
    if CLICK_SERVICE_ID and CLICK_MERCHANT_ID and CLICK_SECRET_KEY:
        found.append("click")
    if PAYME_MERCHANT_ID and PAYME_KEY:
        found.append("payme")
    return found


# Google Search Console: the code from the "HTML tag" verification method (only the content="..." part).
GOOGLE_SITE_VERIFICATION = os.getenv("GOOGLE_SITE_VERIFICATION", "")

LEGAL_UPDATED = {"uz": "14-noyabr 2026", "ru": "14 ноября 2026", "en": "14 November 2026"}

# Uzbek converter: reading text out of an uploaded file
UZBEK_FILE_MAX_PAGES = 100        # PDF pages we read
UZBEK_FILE_MAX_CHARS = 200_000    # characters we convert

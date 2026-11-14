"""Central settings for Nexuz. Change values here, not inside other files."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

APP_NAME = "Nexuz"
APP_VERSION = "0.5.0"
MAX_UPLOAD_MB = 25  # Render free plan has only 512 MB RAM

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

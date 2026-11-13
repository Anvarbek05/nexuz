"""Central settings for Nexuz. Change values here, not inside other files."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

APP_NAME = "Nexuz"
APP_VERSION = "0.2.0"
MAX_UPLOAD_MB = 25  # Render free plan has only 512 MB RAM

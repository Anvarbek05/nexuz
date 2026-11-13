"""Nexuz entry point. Run with:  uvicorn app.main:app --reload"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import APP_NAME, APP_VERSION, STATIC_DIR

app = FastAPI(title=APP_NAME, version=APP_VERSION)


@app.get("/health")
def health():
    """Render uses this address to check that the site is alive."""
    return {"status": "ok", "app": APP_NAME, "version": APP_VERSION}


# The website itself (HTML/CSS/JS). Must stay LAST so /health and /api/* work first.
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

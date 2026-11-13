"""Nexuz entry point. Run with:  uvicorn app.main:app --reload"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import APP_NAME, APP_VERSION, STATIC_DIR
from app.routers import pdf
from app.services.pdf_tools import PdfToolError

app = FastAPI(title=APP_NAME, version=APP_VERSION)


@app.exception_handler(PdfToolError)
async def pdf_tool_error_handler(request: Request, exc: PdfToolError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/health")
def health():
    """Render uses this address to check that the site is alive."""
    return {"status": "ok", "app": APP_NAME, "version": APP_VERSION}


app.include_router(pdf.router)

# The website itself (HTML/CSS/JS). Must stay LAST so /health and /api/* work first.
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

"""Nexuz entry point. Run with:  uvicorn app.main:app --reload"""
from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import APP_NAME, APP_VERSION, STATIC_DIR
from app.routers import pages, pdf, uzbek
from app.services.pdf_tools import PdfToolError

app = FastAPI(title=APP_NAME, version=APP_VERSION)


@app.exception_handler(PdfToolError)
async def pdf_tool_error_handler(request: Request, exc: PdfToolError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    """Unknown website addresses get a friendly page; API errors stay JSON."""
    if exc.status_code == 404 and not request.url.path.startswith("/api/"):
        return pages.not_found(request)
    return await http_exception_handler(request, exc)


@app.get("/health")
def health():
    """Render uses this address to check that the site is alive."""
    return {"status": "ok", "app": APP_NAME, "version": APP_VERSION}


app.include_router(pdf.router)
app.include_router(uzbek.router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(pages.router)   # last: its /{lang}/ routes must not hide the ones above

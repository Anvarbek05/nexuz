"""Nexuz entry point. Run with:  uvicorn app.main:app --reload"""
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import APP_NAME, APP_VERSION, STATIC_DIR
from app.errors import ApiError, pick_language, translate
from app.routers import admin, auth, pages, payments, pdf, uzbek
from app.services.pdf_tools import PdfToolError

app = FastAPI(title=APP_NAME, version=APP_VERSION)


def error_response(request: Request, status: int, code: str, params: dict, english: str | None = None):
    lang = pick_language(request.headers)
    return JSONResponse(status_code=status, content={"detail": translate(lang, code, params, english), "code": code})


@app.exception_handler(PdfToolError)
async def pdf_tool_error_handler(request: Request, exc: PdfToolError):
    return error_response(request, 400, exc.code, exc.params, str(exc))


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    return error_response(request, exc.status, exc.code, exc.params)


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    """Unknown website addresses get a friendly page; API errors stay JSON."""
    if exc.status_code == 404 and not request.url.path.startswith("/api/"):
        return pages.not_found(request)
    return await http_exception_handler(request, exc)


@app.middleware("http")
async def same_site_only(request: Request, call_next):
    """Safety: a form on another website must not be able to act for a signed-in user (CSRF).
    Browsers add an Origin header to such requests; if it names another site, we refuse."""
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        origin = request.headers.get("origin")
        if origin and urlparse(origin).netloc != request.headers.get("host", ""):
            return error_response(request, 403, "forbidden", {})
    return await call_next(request)


@app.get("/health")
def health():
    """Render uses this address to check that the site is alive."""
    return {"status": "ok", "app": APP_NAME, "version": APP_VERSION}


app.include_router(pdf.router)
app.include_router(uzbek.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(payments.router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(pages.router)   # last: its /{lang}/ routes must not hide the ones above

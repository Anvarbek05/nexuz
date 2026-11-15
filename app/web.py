"""Small helpers that connect the web (requests, cookies) with the accounts code."""
from fastapi import Request, Response

from app import config
from app.services import accounts


def client_ip(request: Request) -> str:
    """The visitor's IP address. Behind proxies (Render) the real address is in X-Forwarded-For, counted from the
    RIGHT side, because a visitor can write anything on the left. PROXY_HOPS says how far from the right."""
    socket_ip = request.client.host if request.client else "unknown"
    if config.PROXY_HOPS > 0:
        parts = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
        if len(parts) >= config.PROXY_HOPS:
            return parts[-config.PROXY_HOPS]
    return socket_ip


def _is_https(request: Request) -> bool:
    return request.url.scheme == "https" or request.headers.get("x-forwarded-proto", "").lower() == "https"


def current_user(request: Request) -> dict | None:
    """The signed-in user, or None. Never raises: if the database has a problem, the page still opens."""
    token = request.cookies.get(config.SESSION_COOKIE)
    if not token:
        return None
    try:
        return accounts.user_for_token(token)
    except Exception:
        return None


def set_session_cookie(request: Request, response: Response, token: str) -> None:
    response.set_cookie(
        config.SESSION_COOKIE, token, max_age=config.SESSION_DAYS * 86400,
        httponly=True, samesite="lax", secure=_is_https(request), path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(config.SESSION_COOKIE, path="/")

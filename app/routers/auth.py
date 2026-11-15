"""Sign up, sign in, sign out, delete account, and "who am I" (used by the pages)."""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app import config
from app.errors import ApiError
from app.services import accounts, limits
from app.web import clear_session_cookie, client_ip, current_user, set_session_cookie

router = APIRouter(prefix="/api", tags=["account"])


class Credentials(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=config.PASSWORD_MAX)


class PasswordOnly(BaseModel):
    password: str = Field(max_length=config.PASSWORD_MAX)


def public_user(user: dict | None) -> dict | None:
    if user is None:
        return None
    return {"email": user["email"], "plan": accounts.plan_of(user),
            "premium_until": user["premium_until"] if accounts.is_premium(user) else None}


def signed_in_response(request: Request, user: dict) -> JSONResponse:
    response = JSONResponse({"ok": True, "user": public_user(user)})
    set_session_cookie(request, response, accounts.create_session(user["id"]))
    return response


@router.post("/auth/register")
def register(request: Request, body: Credentials):
    if not config.accounts_storage_ok():
        raise ApiError(503, "accounts_unavailable")
    limits.speed.hit("register", client_ip(request), 10, 3600, "too_many_attempts")
    user = accounts.create_user(body.email, body.password)
    accounts.cleanup()
    return signed_in_response(request, user)


@router.post("/auth/login")
def login(request: Request, body: Credentials):
    ip = client_ip(request)
    limits.speed.hit("login-ip", ip, 30, 900, "too_many_attempts")
    limits.speed.hit("login-email", body.email.strip().lower(), 10, 900, "too_many_attempts")
    user = accounts.authenticate(body.email, body.password)
    accounts.cleanup()
    return signed_in_response(request, user)


@router.post("/auth/logout")
def logout(request: Request):
    accounts.end_session(request.cookies.get(config.SESSION_COOKIE))
    response = JSONResponse({"ok": True})
    clear_session_cookie(response)
    return response


@router.post("/auth/delete")
def delete_account(request: Request, body: PasswordOnly):
    user = current_user(request)
    if user is None:
        raise ApiError(401, "not_signed_in")
    limits.speed.hit("delete", client_ip(request), 10, 900, "too_many_attempts")
    accounts.authenticate(user["email"], body.password)     # ask for the password again
    accounts.delete_user(user)
    response = JSONResponse({"ok": True})
    clear_session_cookie(response)
    return response


@router.get("/me")
def me(request: Request):
    user = current_user(request)
    ticket = limits.Ticket(user, client_ip(request))
    return {"user": public_user(user), "quota": ticket.summary()}

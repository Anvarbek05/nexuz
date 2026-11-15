"""Payment web routes.

  POST /api/pay/create          the browser asks for a payment link (user must be signed in)
  POST /api/pay/click/prepare   Click's server calls this (form data)
  POST /api/pay/click/complete  Click's server calls this (form data)
  POST /api/pay/payme           Payme's server calls this (JSON-RPC)
Everything is off until the provider keys are set in the environment (see config.py).
"""
from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.errors import ApiError, pick_language
from app.services import limits, payments
from app.web import client_ip, current_user

router = APIRouter(prefix="/api/pay", tags=["payments"])


class CreateIn(BaseModel):
    provider: Literal["click", "payme"]


@router.post("/create")
def create(request: Request, body: CreateIn):
    user = current_user(request)
    if user is None:
        raise ApiError(401, "not_signed_in")
    limits.speed.hit("pay-create", client_ip(request), 10, 3600, "too_many_attempts")
    order = payments.create_order(user, body.provider)
    return {"url": payments.checkout_url(order, pick_language(request.headers))}


@router.post("/click/prepare")
async def click_prepare(request: Request):
    return JSONResponse(payments.click_handle(0, dict(await request.form())))


@router.post("/click/complete")
async def click_complete(request: Request):
    return JSONResponse(payments.click_handle(1, dict(await request.form())))


@router.post("/payme")
async def payme(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = None
    return JSONResponse(payments.payme_handle(payload, request.headers.get("authorization")))   # always HTTP 200

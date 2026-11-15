"""Give or remove Premium by hand. Works only if you set the ADMIN_TOKEN environment variable.

Example (PowerShell):
  Invoke-RestMethod -Method Post -Uri https://YOUR-SITE/api/admin/premium `
    -Headers @{ "X-Admin-Token" = "YOUR_TOKEN" } -ContentType "application/json" `
    -Body '{"email": "person@example.com", "days": 30}'
days = 0 removes Premium.
"""
import hmac

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app import config
from app.errors import ApiError
from app.services import accounts, limits
from app.web import client_ip

router = APIRouter(prefix="/api/admin", include_in_schema=False)


class PremiumIn(BaseModel):
    email: str = Field(max_length=254)
    days: int = Field(ge=0, le=3660)


def check_admin(request: Request) -> None:
    if not config.ADMIN_TOKEN:
        raise HTTPException(404)                      # switched off: the address looks like it does not exist
    limits.speed.hit("admin", client_ip(request), 20, 60, "too_many_attempts")
    given = request.headers.get("x-admin-token", "")
    if not hmac.compare_digest(given.encode(), config.ADMIN_TOKEN.encode()):
        raise ApiError(403, "forbidden")


@router.post("/premium")
def premium(request: Request, body: PremiumIn):
    check_admin(request)
    user = accounts.set_premium(body.email, body.days)
    return {"email": user["email"], "premium_until": user["premium_until"]}


@router.get("/ip")
def which_ip(request: Request):
    """Shows which IP address Nexuz thinks you have. After deploying, compare it with your real IP address
    (search "what is my ip"). If it is wrong, change PROXY_HOPS."""
    check_admin(request)
    return {"client_ip": client_ip(request), "socket": request.client.host if request.client else None,
            "x_forwarded_for": request.headers.get("x-forwarded-for"), "proxy_hops": config.PROXY_HOPS}

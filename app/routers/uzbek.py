"""Web route for the Uzbek alphabet converter (text in, text out)."""
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.services import limits
from app.services.uzbek import convert, detect_script
from app.web import client_ip

router = APIRouter(prefix="/api/uzbek", tags=["uzbek"])

MAX_CHARS = 20000


class ConvertIn(BaseModel):
    text: str = Field(max_length=MAX_CHARS)
    target: Literal["cyrillic", "latin", "latin_new"]
    source: Literal["auto", "cyrillic", "latin", "latin_new"] = "auto"


@router.post("/convert")
def convert_text(request: Request, body: ConvertIn):
    limits.speed.hit("uzbek", client_ip(request), 300, 60)   # generous: the page converts while you type
    source = detect_script(body.text) if body.source == "auto" else body.source
    return {"text": convert(body.text, body.target, source), "source": source}

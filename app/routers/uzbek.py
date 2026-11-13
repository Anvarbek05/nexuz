"""Web route for the Uzbek alphabet converter (text in, text out)."""
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.uzbek import convert, detect_script

router = APIRouter(prefix="/api/uzbek", tags=["uzbek"])

MAX_CHARS = 20000


class ConvertIn(BaseModel):
    text: str = Field(max_length=MAX_CHARS)
    target: Literal["cyrillic", "latin", "latin_new"]
    source: Literal["auto", "cyrillic", "latin", "latin_new"] = "auto"


@router.post("/convert")
def convert_text(body: ConvertIn):
    source = detect_script(body.text) if body.source == "auto" else body.source
    return {"text": convert(body.text, body.target, source), "source": source}

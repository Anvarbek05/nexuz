"""Web route for the Uzbek alphabet converter (text in, text out)."""
from typing import Literal

from fastapi import APIRouter, File, Request, UploadFile
from pydantic import BaseModel, Field

from app import config
from app.errors import ApiError
from app.services import limits, pdf_tools
from app.services.uzbek import convert, detect_script
from app.web import client_ip, current_user

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


def read_text_file(data: bytes) -> str:
    """Plain text file: UTF-8 (with or without BOM), UTF-16 with BOM, or Windows Cyrillic (cp1251) as a last try."""
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16", errors="replace")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1251", errors="replace")


@router.post("/convert-file")
async def convert_file(request: Request, file: UploadFile = File(...)):
    """Upload a PDF or TXT file; get its text in ALL three alphabets (the page then switches without asking again).
    Counts as one operation of the daily limit."""
    ticket = limits.start(current_user(request), client_ip(request))
    name = file.filename or "file"
    data = await file.read()
    ticket.check_size(name, len(data))
    pages = None
    if data[:5] == b"%PDF-":
        text, pages = pdf_tools.extract_text(data, name, config.UZBEK_FILE_MAX_PAGES)
        if not text.strip():
            raise ApiError(400, "pdf_no_text", name=name)       # a scanned PDF: only pictures, no text
    elif name.lower().endswith(".txt"):
        text = read_text_file(data)
    else:
        raise ApiError(400, "uz_file_type")
    if len(text) > config.UZBEK_FILE_MAX_CHARS:
        raise ApiError(400, "uz_text_too_long", max=config.UZBEK_FILE_MAX_CHARS)
    source = detect_script(text)
    texts = {target: convert(text, target, source) for target in ("cyrillic", "latin", "latin_new")}
    ticket.done()
    return {"texts": texts, "source": source, "pages": pages, "chars": len(text)}

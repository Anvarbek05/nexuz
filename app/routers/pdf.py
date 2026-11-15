"""Web routes for PDF tools. They check the visitor's limits, receive files, call a service, send the result back."""
import io

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import StreamingResponse

from app.errors import ApiError
from app.services import limits, pdf_tools
from app.web import client_ip, current_user

router = APIRouter(prefix="/api", tags=["pdf"])


def begin(request: Request) -> limits.Ticket:
    """Who is this, and may they do one more operation today? (Raises a translated error if not.)"""
    return limits.start(current_user(request), client_ip(request))


async def read_uploads(files: list[UploadFile], ticket: limits.Ticket) -> list[tuple[str, bytes]]:
    uploads = []
    for f in files:
        data = await f.read()
        ticket.check_size(f.filename or "file", len(data))
        uploads.append((f.filename or "file", data))
    if not uploads:
        raise ApiError(400, "no_file")
    return uploads


async def read_one(files: list[UploadFile], ticket: limits.Ticket) -> bytes:
    return (await read_uploads(files, ticket))[0][1]


def file_response(ticket: limits.Ticket, data: bytes, filename: str, mime: str = "application/pdf") -> StreamingResponse:
    """Count the operation (it worked), then send the file."""
    ticket.done()
    return StreamingResponse(
        io.BytesIO(data),
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/merge")
async def merge(request: Request, files: list[UploadFile] = File(...)):
    ticket = begin(request)
    return file_response(ticket, pdf_tools.merge_pdfs(await read_uploads(files, ticket)), "merged.pdf")


@router.post("/split")
async def split(request: Request, files: list[UploadFile] = File(...), pages: str = Form("1")):
    ticket = begin(request)
    return file_response(ticket, pdf_tools.extract_pages(await read_one(files, ticket), pages), "pages.pdf")


@router.post("/rotate")
async def rotate(request: Request, files: list[UploadFile] = File(...), angle: int = Form(90)):
    ticket = begin(request)
    return file_response(ticket, pdf_tools.rotate_pdf(await read_one(files, ticket), angle), "rotated.pdf")


@router.post("/compress")
async def compress(request: Request, files: list[UploadFile] = File(...), level: str = Form("medium")):
    ticket = begin(request)
    return file_response(ticket, pdf_tools.compress_pdf(await read_one(files, ticket), level), "compressed.pdf")


@router.post("/pdf2img")
async def pdf_to_images(request: Request, files: list[UploadFile] = File(...), fmt: str = Form("png")):
    ticket = begin(request)
    data = pdf_tools.pdf_to_images(await read_one(files, ticket), fmt)
    return file_response(ticket, data, "pages.zip", "application/zip")


@router.post("/img2pdf")
async def images_to_pdf(request: Request, files: list[UploadFile] = File(...)):
    ticket = begin(request)
    return file_response(ticket, pdf_tools.images_to_pdf(await read_uploads(files, ticket)), "images.pdf")


@router.post("/watermark")
async def watermark(request: Request, files: list[UploadFile] = File(...), text: str = Form("Nexuz")):
    ticket = begin(request)
    return file_response(ticket, pdf_tools.add_watermark(await read_one(files, ticket), text), "watermarked.pdf")


@router.post("/protect")
async def protect(request: Request, files: list[UploadFile] = File(...), password: str = Form("")):
    ticket = begin(request)
    return file_response(ticket, pdf_tools.protect_pdf(await read_one(files, ticket), password), "protected.pdf")


@router.post("/unlock")
async def unlock(request: Request, files: list[UploadFile] = File(...), password: str = Form("")):
    ticket = begin(request)
    return file_response(ticket, pdf_tools.unlock_pdf(await read_one(files, ticket), password), "unlocked.pdf")

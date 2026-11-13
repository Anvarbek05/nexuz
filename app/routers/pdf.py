"""Web routes for PDF tools. They only receive files, call a service, and send the result back."""
import io

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.config import MAX_UPLOAD_MB
from app.services import pdf_tools

router = APIRouter(prefix="/api", tags=["pdf"])


async def read_uploads(files: list[UploadFile]) -> list[tuple[str, bytes]]:
    uploads = []
    for f in files:
        data = await f.read()
        if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
            raise HTTPException(413, f"{f.filename} is larger than {MAX_UPLOAD_MB} MB")
        uploads.append((f.filename or "file", data))
    if not uploads:
        raise HTTPException(400, "No file uploaded")
    return uploads


async def read_one(files: list[UploadFile]) -> bytes:
    return (await read_uploads(files))[0][1]


def file_response(data: bytes, filename: str, mime: str = "application/pdf") -> StreamingResponse:
    return StreamingResponse(
        io.BytesIO(data),
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/merge")
async def merge(files: list[UploadFile] = File(...)):
    return file_response(pdf_tools.merge_pdfs(await read_uploads(files)), "merged.pdf")


@router.post("/split")
async def split(files: list[UploadFile] = File(...), pages: str = Form("1")):
    return file_response(pdf_tools.extract_pages(await read_one(files), pages), "pages.pdf")


@router.post("/rotate")
async def rotate(files: list[UploadFile] = File(...), angle: int = Form(90)):
    return file_response(pdf_tools.rotate_pdf(await read_one(files), angle), "rotated.pdf")


@router.post("/compress")
async def compress(files: list[UploadFile] = File(...), level: str = Form("medium")):
    return file_response(pdf_tools.compress_pdf(await read_one(files), level), "compressed.pdf")


@router.post("/pdf2img")
async def pdf_to_images(files: list[UploadFile] = File(...), fmt: str = Form("png")):
    data = pdf_tools.pdf_to_images(await read_one(files), fmt)
    return file_response(data, "pages.zip", "application/zip")


@router.post("/img2pdf")
async def images_to_pdf(files: list[UploadFile] = File(...)):
    return file_response(pdf_tools.images_to_pdf(await read_uploads(files)), "images.pdf")


@router.post("/watermark")
async def watermark(files: list[UploadFile] = File(...), text: str = Form("Nexuz")):
    return file_response(pdf_tools.add_watermark(await read_one(files), text), "watermarked.pdf")


@router.post("/protect")
async def protect(files: list[UploadFile] = File(...), password: str = Form("")):
    return file_response(pdf_tools.protect_pdf(await read_one(files), password), "protected.pdf")


@router.post("/unlock")
async def unlock(files: list[UploadFile] = File(...), password: str = Form("")):
    return file_response(pdf_tools.unlock_pdf(await read_one(files), password), "unlocked.pdf")

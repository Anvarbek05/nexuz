"""Web routes for PDF tools. They only receive files, call a service, and send the result back."""
import io

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.config import MAX_UPLOAD_MB
from app.services.pdf_tools import merge_pdfs

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


def pdf_response(data: bytes, filename: str) -> StreamingResponse:
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/merge")
async def merge(files: list[UploadFile] = File(...)):
    uploads = await read_uploads(files)
    return pdf_response(merge_pdfs(uploads), "merged.pdf")

"""PDF logic only. No web code here, so it is easy to test and reuse."""
import fitz  # PyMuPDF


class PdfToolError(Exception):
    """A problem the user can fix (bad file, wrong input). The message is shown on the site."""


def open_pdf(data: bytes, name: str = "file") -> fitz.Document:
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception:
        raise PdfToolError(f"{name} is not a valid PDF file")
    if doc.needs_pass:
        raise PdfToolError(f"{name} is password protected")
    return doc


def merge_pdfs(files: list[tuple[str, bytes]]) -> bytes:
    """Join PDFs in the given order. `files` is a list of (filename, bytes)."""
    if len(files) < 2:
        raise PdfToolError("Select at least 2 PDF files")
    result = fitz.open()
    for name, data in files:
        result.insert_pdf(open_pdf(data, name))
    return result.tobytes(garbage=3, deflate=True)

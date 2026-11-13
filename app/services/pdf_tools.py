"""PDF logic only. No web code here, so it is easy to test and reuse."""
import io
import zipfile

import pymupdf as fitz  # PyMuPDF

MAX_IMAGE_PAGES = 50  # PDF -> images limit (free server has little memory)

# (dpi above which images are shrunk, target dpi, JPEG quality)
COMPRESS_LEVELS = {
    "low": (200, 150, 85),
    "medium": (150, 110, 70),
    "high": (120, 72, 50),
}


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


def _save(doc: fitz.Document) -> bytes:
    return doc.tobytes(garbage=3, deflate=True)


def merge_pdfs(files: list[tuple[str, bytes]]) -> bytes:
    """Join PDFs in the given order. `files` is a list of (filename, bytes)."""
    if len(files) < 2:
        raise PdfToolError("Select at least 2 PDF files")
    result = fitz.open()
    for name, data in files:
        result.insert_pdf(open_pdf(data, name))
    return _save(result)


def parse_page_ranges(text: str, total: int) -> list[int]:
    """'1-3,5' -> [0, 1, 2, 4] (zero-based page numbers)."""
    pages: list[int] = []
    try:
        for part in text.replace(" ", "").split(","):
            if not part:
                continue
            if "-" in part:
                start, end = part.split("-", 1)
                pages.extend(range(int(start), int(end) + 1))
            else:
                pages.append(int(part))
    except ValueError:
        raise PdfToolError("Write pages like this: 1-3,5")
    pages = [p - 1 for p in pages if 1 <= p <= total]
    if not pages:
        raise PdfToolError(f"No valid pages. This PDF has {total} pages")
    return pages


def extract_pages(data: bytes, pages_text: str) -> bytes:
    doc = open_pdf(data)
    doc.select(parse_page_ranges(pages_text, len(doc)))
    return _save(doc)


def rotate_pdf(data: bytes, angle: int) -> bytes:
    if angle not in (90, 180, 270):
        raise PdfToolError("Rotation must be 90, 180 or 270 degrees")
    doc = open_pdf(data)
    for page in doc:
        page.set_rotation((page.rotation + angle) % 360)
    return _save(doc)


def compress_pdf(data: bytes, level: str = "medium") -> bytes:
    """Shrink images and clean the file. Never returns a file bigger than the original."""
    if level not in COMPRESS_LEVELS:
        raise PdfToolError("Unknown compression level")
    dpi_threshold, dpi_target, quality = COMPRESS_LEVELS[level]
    doc = open_pdf(data)
    if hasattr(doc, "rewrite_images"):
        doc.rewrite_images(dpi_threshold=dpi_threshold, dpi_target=dpi_target, quality=quality)
    result = doc.tobytes(garbage=4, deflate=True, clean=True)
    return result if len(result) < len(data) else data


def pdf_to_images(data: bytes, fmt: str = "png", dpi: int = 150) -> bytes:
    """Every page as an image, returned as a ZIP file."""
    if fmt not in ("png", "jpg"):
        raise PdfToolError("Image format must be png or jpg")
    doc = open_pdf(data)
    if len(doc) > MAX_IMAGE_PAGES:
        raise PdfToolError(f"This tool supports up to {MAX_IMAGE_PAGES} pages. This PDF has {len(doc)}")
    zoom = fitz.Matrix(dpi / 72, dpi / 72)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for number, page in enumerate(doc, 1):
            pix = page.get_pixmap(matrix=zoom, alpha=False)
            z.writestr(f"page-{number}.{fmt}", pix.tobytes("jpeg" if fmt == "jpg" else "png"))
    return buf.getvalue()


def images_to_pdf(files: list[tuple[str, bytes]]) -> bytes:
    """One PDF page per image (JPG or PNG), in the given order."""
    result = fitz.open()
    for name, data in files:
        if data.startswith(b"\x89PNG"):
            kind = "png"
        elif data.startswith(b"\xff\xd8"):
            kind = "jpeg"
        else:
            raise PdfToolError(f"{name} is not a JPG or PNG image")
        try:
            image = fitz.open(stream=data, filetype=kind)
            result.insert_pdf(fitz.open("pdf", image.convert_to_pdf()))
        except Exception:
            raise PdfToolError(f"{name} could not be read as an image")
    return _save(result)


def add_watermark(data: bytes, text: str) -> bytes:
    text = text.strip()[:40]
    if not text:
        raise PdfToolError("Write the watermark text")
    try:
        text.encode("cp1252")
    except UnicodeEncodeError:
        raise PdfToolError("Watermark text supports Latin letters without marks like ğ or ş for now")
    doc = open_pdf(data)
    for page in doc:
        rect = page.rect
        size = max(24, min(rect.width, rect.height) / 8)
        length = fitz.get_text_length(text, fontname="helv", fontsize=size)
        center = fitz.Point(rect.width / 2, rect.height / 2)
        page.insert_text(
            fitz.Point(center.x - length / 2, center.y),
            text, fontname="helv", fontsize=size,
            color=(0.5, 0.5, 0.5), fill_opacity=0.3,
            morph=(center, fitz.Matrix(45)),
        )
    return _save(doc)

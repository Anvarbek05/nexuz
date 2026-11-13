# Nexuz

Free online PDF tools. Python (FastAPI + PyMuPDF) backend, plain HTML/CSS/JS frontend. Files are processed in memory and never stored.

**Version 0.3.0** | Live: https://nexuz-vtcb.onrender.com

## Tools
| Tool | Page | API route | Options |
|---|---|---|---|
| Merge PDF | `/#merge` | `POST /api/merge` | files in order (2+) |
| Extract pages | `/#split` | `POST /api/split` | `pages` like `1-3,5` |
| Rotate PDF | `/#rotate` | `POST /api/rotate` | `angle` 90 / 180 / 270 |
| Compress PDF | `/#compress` | `POST /api/compress` | `level` low / medium / high |
| PDF to images | `/#pdf2img` | `POST /api/pdf2img` | `fmt` png / jpg (max 50 pages, ZIP) |
| Images to PDF | `/#img2pdf` | `POST /api/img2pdf` | JPG/PNG files in order |
| Add watermark | `/#watermark` | `POST /api/watermark` | `text` (Latin letters only for now) |

Limits: 25 MB per file (free Render server has 512 MB RAM). First visit after idle can take up to a minute.

## Run locally (Windows PowerShell)
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000

## Run tests (15 tests)
```powershell
pytest
```

## Deploy (Render, free)
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Environment variable: `PYTHON_VERSION` = `3.11.9`
- Every `git push` to `main` redeploys automatically.

## Project structure
```
app/
  main.py          entry point, error handler, serves the website
  config.py        settings (name, version, upload limit)
  routers/pdf.py   web routes: receive files, call a service, return the result
  services/
    pdf_tools.py   all PDF logic (no web code)
static/
  index.html       home page + tool page
  css/style.css    design
  js/app.js        tool list, home grid, tool page logic
tests/             automatic tests
requirements.txt   libraries for the server (pymupdf>=1.26.3 needed for Compress)
render.yaml        Render config
```

## How to add a new tool (3 places)
1. `app/services/pdf_tools.py`: write the function.
2. `app/routers/pdf.py`: add a `@router.post("/mytool")` route.
3. `static/js/app.js`: add an `api` object to the tool in `TOOLS` (or a new tool).
Then add a test in `tests/` and push.

## Progress
- [x] Step 1: project skeleton
- [x] Step 2: new design, home page, Merge PDF
- [x] Step 3: Extract pages, Rotate, Compress, PDF to images, Images to PDF, Watermark
- [ ] Step 4: Uzbek alphabet converter, Protect PDF, Unlock PDF
- [ ] Step 5: Uzbek / Russian / English interface, logo, SEO pages for each tool
- [ ] Step 6: accounts, usage limits, payments
- [ ] Step 7: Word / Excel conversion (Docker + LibreOffice), OCR

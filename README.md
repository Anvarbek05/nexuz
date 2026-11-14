# Nexuz

Free online PDF tools. Python (FastAPI + PyMuPDF) backend, plain HTML/CSS/JS frontend. Files are processed in memory and never stored.

**Version 0.5.0** | Live: https://nexuz-vtcb.onrender.com

## Languages and addresses
Three interface languages: Uzbek (`/uz/`), Russian (`/ru/`), English (`/en/`). `/` redirects by the browser language.
Every tool has its own address in every language, for example `/uz/merge-pdf`, `/ru/compress-pdf`, `/en/uzbek-alphabet-converter`.
Each page has its own title, description, canonical link, hreflang links and structured data, plus `/sitemap.xml` and `/robots.txt`.

## Tools
| Tool | Page (address ending) | API route | Options |
|---|---|---|---|
| Merge PDF | `merge-pdf` | `POST /api/merge` | files in order (2+) |
| Extract pages | `extract-pdf-pages` | `POST /api/split` | `pages` like `1-3,5` |
| Rotate PDF | `rotate-pdf` | `POST /api/rotate` | `angle` 90 / 180 / 270 |
| Compress PDF | `compress-pdf` | `POST /api/compress` | `level` low / medium / high |
| PDF to images | `pdf-to-images` | `POST /api/pdf2img` | `fmt` png / jpg (max 50 pages, ZIP) |
| Images to PDF | `images-to-pdf` | `POST /api/img2pdf` | JPG/PNG files in order |
| Add watermark | `watermark-pdf` | `POST /api/watermark` | `text` (Latin letters only for now) |
| Protect PDF | `protect-pdf` | `POST /api/protect` | `password` (4 to 64 characters, AES-256) |
| Unlock PDF | `unlock-pdf` | `POST /api/unlock` | `password` (you must know it) |
| Uzbek alphabet converter | `uzbek-alphabet-converter` | `POST /api/uzbek/convert` | JSON `{text, target}`; target `cyrillic`, `latin` or `latin_new`; source is auto-detected |

Limits: 25 MB per file (free Render server has 512 MB RAM). First visit after idle can take up to a minute.

## Run locally (Windows PowerShell)
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000

## Run tests (75 tests)
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
  main.py            entry point, error pages, serves static files
  config.py          settings: site address, languages, upload limit
  tools.py           the list of tools (addresses, API settings, icons)
  i18n.py            loads texts from app/locales
  locales/           uz.json, ru.json, en.json  <- ALL visible texts live here
  templates/         HTML pages (Jinja2): base, home, tool, uzbek, 404
  routers/
    pages.py         website pages, sitemap.xml, robots.txt
    pdf.py           PDF API routes
    uzbek.py         converter API route
  services/
    pdf_tools.py     PDF logic (no web code)
    uzbek.py         alphabet converter logic (no web code)
static/
  css/style.css      design
  js/app.js          behaviour only (texts come from the page)
  img/               logo, favicon, social preview image
tests/               75 automatic tests
render.yaml          Render configuration
```

## How to add a new tool
1. `app/services/pdf_tools.py`: write the function.
2. `app/routers/pdf.py`: add a `@router.post("/mytool")` route.
3. `app/tools.py`: add the tool (id, slug, group, icon, API settings).
4. `app/locales/en.json`, `uz.json`, `ru.json`: add its texts under `tools` (the test checks that all three files have the same keys).
5. Add a test in `tests/` and push.

## Settings (environment variables on Render)
- `SITE_URL`: the public address, used in canonical links and the sitemap. Change it when you buy a domain.
- `UZBEK_NEW_ALPHABET=1`: switches the Uzbek interface to the new alphabet (Ö Ğ Ş Ç). Set it on 22 April 2027.

## Progress
- [x] Step 1: project skeleton
- [x] Step 2: new design, home page, Merge PDF
- [x] Step 3: Extract pages, Rotate, Compress, PDF to images, Images to PDF, Watermark
- [x] Step 4: Uzbek alphabet converter (Cyrillic / current Latin / new Latin), Protect PDF, Unlock PDF
- [x] Step 5: Uzbek / Russian / English interface, logo, one SEO page per tool and language, sitemap
- [ ] Step 6: accounts, usage limits, payments (also: translate server error messages)
- [ ] Step 7: Word / Excel conversion (Docker + LibreOffice), OCR

## Uzbek alphabet rules used by the converter
Law signed 21 October 2026, in force from 22 April 2027: Oʻ → Ö, Gʻ → Ğ, Sh → Ş, Ch → Ç.
"ng" is no longer a separate letter; the apostrophe (tutuq belgisi) stays.
Known limits: a few Cyrillic rules (e.g. ц, е after vowels) follow the common spelling rules but
foreign words and names should always be checked by a person.

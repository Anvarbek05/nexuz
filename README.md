# Nexuz

Free online PDF tools. Python (FastAPI + PyMuPDF) backend, plain HTML/CSS/JS frontend. Files are processed in memory and never stored.

**Version 0.6.0** | Live: https://nexuz-vtcb.onrender.com

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

Limits depend on the plan (set in `PLANS` in `app/config.py`): guest 5 operations/day and 10 MB (counted by IP address),
free account 25/day and 25 MB, Premium no daily limit and 50 MB. A day ends at midnight in Tashkent.
First visit after idle can take up to a minute (Render free).

## Run locally (Windows PowerShell)
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000

## Run tests
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
  main.py            entry point, error handlers (translated), CSRF check, serves static files
  config.py          settings: site address, languages, plans and limits, payment keys
  db.py              tiny database layer (SQLite on your computer, PostgreSQL on Render)
  errors.py          translated error messages (ApiError)
  web.py             helpers: visitor IP address, session cookie
  admin.py           `python -m app.admin` (list users, give Premium) on your own computer
  tools.py           the list of tools (addresses, API settings, icons)
  i18n.py            loads texts from app/locales
  locales/           uz.json, ru.json, en.json  <- ALL visible texts live here
  templates/         HTML pages (Jinja2): base, home, tool, uzbek, 404
  routers/
    pages.py         website pages, sitemap.xml, robots.txt
    pdf.py           PDF API routes (check the visitor's limits first)
    uzbek.py         converter API route
    auth.py          register, sign in, sign out, delete account, /api/me
    payments.py      "Pay" button, Click and Payme callbacks
    admin.py         give Premium by hand (needs ADMIN_TOKEN)
  services/
    accounts.py      users, scrypt password hashes, sessions, Premium
    limits.py        daily limits (database) and speed limits (memory)
    payments.py      orders, Click and Payme protocol logic
    pdf_tools.py     PDF logic (no web code)
    uzbek.py         alphabet converter logic (no web code)
static/
  css/style.css      design
  js/app.js          behaviour only (texts come from the page)
  img/               logo, favicon, social preview image
tests/               automatic tests (pytest)
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
- `DATABASE_URL`: PostgreSQL address. Required on Render (without it new accounts are refused). Not needed on your computer.
- `ADMIN_TOKEN`: secret for `/api/admin/*` (give Premium by hand). Empty = switched off.
- `CONTACT_EMAIL`: shown on the Privacy and Terms pages.
- `PROXY_HOPS`: how many proxies are in front of the site (to find the visitor's IP). See HOW_TO_UPDATE.md.
- `GOOGLE_SITE_VERIFICATION`: code for Google Search Console.
- `PREMIUM_PRICE_SUM`, `CLICK_SERVICE_ID`, `CLICK_MERCHANT_ID`, `CLICK_SECRET_KEY`, `PAYME_MERCHANT_ID`, `PAYME_KEY`, `PAYME_TEST`: payments (off until set).
- `UZBEK_NEW_ALPHABET=1`: switches the Uzbek interface to the new alphabet (Ö Ğ Ş Ç). Set it on 22 April 2027.

## Progress
- [x] Step 1: project skeleton
- [x] Step 2: new design, home page, Merge PDF
- [x] Step 3: Extract pages, Rotate, Compress, PDF to images, Images to PDF, Watermark
- [x] Step 4: Uzbek alphabet converter (Cyrillic / current Latin / new Latin), Protect PDF, Unlock PDF
- [x] Step 5: Uzbek / Russian / English interface, logo, one SEO page per tool and language, sitemap
- [x] Step 6: accounts, daily limits, translated server errors, Privacy and Terms pages, Search Console tag, Click and Payme (built, switched off, not tested with the providers)
- [ ] Step 7: Word / Excel conversion (Docker + LibreOffice), OCR. Also: password reset by email, Uzum payments

## Uzbek alphabet rules used by the converter
Law signed 21 October 2026, in force from 22 April 2027: Oʻ → Ö, Gʻ → Ğ, Sh → Ş, Ch → Ç.
"ng" is no longer a separate letter; the apostrophe (tutuq belgisi) stays.
Known limits: a few Cyrillic rules (e.g. ц, е after vowels) follow the common spelling rules but
foreign words and names should always be checked by a person.

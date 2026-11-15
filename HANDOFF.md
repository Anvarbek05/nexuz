# NEXUZ: HANDOFF DOCUMENT (state after Step 6)

Give this whole file to the new Claude chat as your FIRST message, and also upload the project zip
(or the repo files), because Claude cannot open GitHub links.

---

## 1. What this project is
Nexuz is a free online PDF tools website, like ilovepdf, with one special feature: an Uzbek alphabet
converter (Cyrillic, current Latin, and the new Latin with Ö Ğ Ş Ç).

- Live site: https://nexuz-vtcb.onrender.com  (Render free plan)
- GitHub repo: https://github.com/Anvarbek05/nexuz
- Owner: Anvarbek (Uzbekistan). Wants to grow Nexuz into a professional site, then add accounts/payments.
- Current version: 0.6.0. Steps 1 to 5 are done and live. Step 6 is built and tested in a sandbox (see section 12); he still has to install it, create the database and test it.

## 2. The person you are helping (important for how to answer)
- Windows PC, VS Code, PowerShell terminal, project folder `D:\nexuz-pro`, virtual environment `venv`.
- His computer has Python 3.15 (a very new preview). He does NOT want to install an older Python.
  That is why `requirements.txt` uses `pymupdf>=1.26.3` and no Pillow.
- Python: beginner to intermediate. JavaScript: some. Data background.
- His English is simple and has mistakes. Use simple English, short sentences, numbered steps.
- He wants: "tell me exactly what to do, step by step". Give exact commands for Windows PowerShell.
- Things that went wrong before (avoid them):
  1. He copied folders INTO existing folders, creating `tests\tests`. Always tell him to DELETE the old
     `app`, `static`, `tests` folders first, then copy the new ones. Never use example paths like
     `C:\Users\YourName\...` (he cannot guess the real path); give a method that finds the path itself.
  2. pip could not build old PyMuPDF on Python 3.15. Keep `pymupdf>=...` (not `==`).
  3. He cannot run a Python backend by opening index.html. Everything must run through uvicorn.
- Delivery method that works: build the whole project in the sandbox, run the tests, test in a real browser
  (Playwright), give a ZIP + short instructions. Do not give half-files to paste.

## 3. Tech stack
- Python backend: FastAPI 0.115, uvicorn, python-multipart, jinja2 (pages), PyMuPDF >= 1.26.3 (all PDF work).
  Compress needs `Document.rewrite_images` (first available in PyMuPDF 1.26.3).
- Frontend: server-rendered Jinja2 pages + one plain JavaScript file (no framework, no build step).
- Hosting: Render free web service. Limits: 512 MB RAM, sleeps after ~15 min idle (first visit up to ~1 minute),
  no LibreOffice. Python 3.11.9 on Render (env var PYTHON_VERSION).
  Build: `pip install -r requirements.txt`. Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- Files are processed in memory and never stored. Upload limit 25 MB per file.
- Tests: pytest (`pip install -r requirements-dev.txt`, then `pytest`). Ask him for the number he sees; it is more than 75 now.
- Database: SQLite file `data/nexuz.db` on his computer; PostgreSQL (env var DATABASE_URL) on Render. `psycopg[binary]` is installed only for Python < 3.14 (his 3.15 uses SQLite).

## 4. Project structure
```
app/
  main.py            entry point; error handlers; mounts /static; includes routers (pages router LAST)
  config.py          SITE_URL, LANGS, DEFAULT_LANG, upload limit, UZBEK_NEW_ALPHABET flag
  tools.py           registry of tools: id, slug, group, icon, API settings (NO visible texts)
  i18n.py            loads app/locales/<lang>.json (can convert Uzbek texts to the new alphabet)
  locales/           uz.json, ru.json, en.json  <- ALL visible texts. A test checks the keys are identical.
  templates/         base.html, home.html, tool.html, uzbek.html, 404.html, _cards.html, _more.html
  db.py              small DB layer: SQL written with ? placeholders for both SQLite and PostgreSQL; tables users, sessions, usage, orders
  errors.py          ApiError(status, code, **params) + translate(); texts are in locales under `errors`
  web.py             client_ip (PROXY_HOPS), current_user, session cookie helpers
  admin.py           CLI: python -m app.admin users | grant EMAIL DAYS | revoke EMAIL
  routers/
    pages.py         HTML pages: /{lang}/, tools, login, register, account, pricing, privacy, terms; sitemap.xml, robots.txt, favicons
    pdf.py           POST /api/merge split rotate compress pdf2img img2pdf watermark protect unlock (each starts with limits.start)
    uzbek.py         POST /api/uzbek/convert  (JSON: text, target[, source]); rate limited, no daily limit
    auth.py          POST /api/auth/register|login|logout|delete, GET /api/me
    payments.py      POST /api/pay/create, /api/pay/click/prepare|complete, /api/pay/payme
    admin.py         POST /api/admin/premium, GET /api/admin/ip (need header X-Admin-Token = ADMIN_TOKEN)
  services/
    accounts.py      scrypt password hashes, sessions (cookie holds a random token, DB holds its SHA-256), Premium
    limits.py        Ticket (plan, daily count, file size) + in-memory speed limit
    payments.py      orders + Click (md5 sign) + Payme (JSON-RPC, Basic auth) logic
    pdf_tools.py     all PDF logic, raises PdfToolError(message, code, **params) (shown as HTTP 400 {"detail": translated text})
    uzbek.py         alphabet converter logic
static/  css/style.css, js/app.js, img/ (logo.svg, favicon.svg, favicon.ico, apple-touch-icon.png, og-image.png)
tests/   test_health, test_merge, test_tools, test_security, test_uzbek, test_pages
render.yaml, requirements.txt, requirements-dev.txt, README.md, HOW_TO_UPDATE.md, HANDOFF.md
```

## 5. How it works
- `/` redirects to `/uz/`, `/ru/` or `/en/` using the browser language (default `uz`).
- Every tool has a page per language: `/{lang}/{slug}`, e.g. `/uz/merge-pdf`, `/ru/compress-pdf`,
  `/en/uzbek-alphabet-converter`. Slugs: merge-pdf, extract-pdf-pages, rotate-pdf, compress-pdf,
  pdf-to-images, images-to-pdf, watermark-pdf, protect-pdf, unlock-pdf, uzbek-alphabet-converter.
- Each page has its own title, meta description, canonical, hreflang (uz, ru, en, x-default), Open Graph,
  JSON-LD (WebApplication / WebSite), how-to steps in the HTML, links to related tools.
- The server puts `window.NEXUZ = {page, ui, tool}` into every page. `static/js/app.js` only adds behaviour
  (file list, reorder, options, upload with fetch, download, converter). No texts are hard-coded in JS.
- Uzbek interface text is stored in the CURRENT Latin (Oʻ Gʻ Sh Ch). Setting env var `UZBEK_NEW_ALPHABET=1`
  converts it to the new alphabet automatically (texts about the old letters are excluded; see `_KEEP_AS_IS`
  in `app/i18n.py`). Plan: set it on 22 April 2027.
- API errors are translated: code raised in Python -> text in `locales/<lang>.json` under `errors`. The browser sends header `X-Lang`.
  A test checks that every code used in Python has a text in all three languages.
- Plans (config.PLANS): guest 5/day, 10 MB (counted by hashed IP); free 25/day, 25 MB; premium unlimited, 50 MB. Only successful operations count. Day ends at midnight Tashkent.
- Accounts: email + password (min 8). No email verification and NO password reset yet (needs an email service).
- Safety: HttpOnly SameSite=Lax cookie, Origin check on POST (main.py), login/register speed limits.
- On Render (env RENDER=true) registration is refused unless DATABASE_URL is PostgreSQL (Render free disk is erased on restart).

### Add a new tool
1. function in `app/services/pdf_tools.py`  2. route in `app/routers/pdf.py`  3. entry in `app/tools.py`
4. texts in all three locale files under `tools.<id>` (name, desc, seo_title, seo_desc, button, need,
   options, steps)  5. test in `tests/`.

## 6. Tools that exist
Merge, Extract pages, Rotate, Compress (low/medium/high), PDF to images (PNG/JPG, max 50 pages, ZIP),
Images to PDF (JPG/PNG), Watermark (Latin letters only: Helvetica cannot draw ğ ş), Protect (AES-256,
password 4 to 64 chars), Unlock (needs the password), Uzbek alphabet converter.

## 7. Uzbek alphabet facts used
Law signed 21 October 2026, in force from 22 April 2027 (sources: dunyo.info, gov.uz, Times of Central Asia).
Oʻ -> Ö, Gʻ -> Ğ, Sh -> Ş, Ch -> Ç. "ng" is no longer a separate letter. The apostrophe (tutuq belgisi) stays.
Converter rules in `app/services/uzbek.py`:
- Cyrillic -> Latin: е = ye at word start or after a vowel, else e; ц = ts after a vowel, else s; ъ = ʼ (U+02BC);
  ь dropped; щ = shch; ё/ю/я = yo/yu/ya.
- Latin -> Cyrillic accepts old, new or mixed Latin. Word-initial e = э. ʻ after o/g makes ў/ғ.
  An apostrophe between two letters = ъ; quotation marks are left alone.
- Current Latin output uses ʻ (U+02BB) in oʻ gʻ. Tutuq output is ʼ (U+02BC).
- Known limits: "sh"/"ch" written across a word boundary (e.g. "Ishhona") is converted wrongly; foreign
  words and names must be checked by a person. The first version was written from scratch; his old
  `uzbek-converter` repo code was never shared. Ask him for test words if he wants to compare.

## 8. Rules for the next assistant
1. Keep the three locale files in sync (the test `test_all_languages_have_the_same_text_keys` enforces it).
2. Never hard-code visible text in templates or JS. Use locale files.
3. Run `pytest` and a Playwright browser test before giving a ZIP. Report test counts honestly.
4. Keep `pymupdf>=1.26.3`, avoid Pillow and any package that needs compiling on Python 3.15.
5. Keep memory use low (Render free = 512 MB). No files saved on the server.
6. Give Windows PowerShell commands. Tell him to delete `app`, `static`, `tests` before copying a new version.
7. Do not break existing URLs (they are in the sitemap).

## 9. Roadmap (what to do next)
- **Step 6 leftovers (do these first with him):** create the database and set DATABASE_URL on Render; set CONTACT_EMAIL,
  ADMIN_TOKEN; check PROXY_HOPS with /api/admin/ip; Google Search Console (HTML tag -> GOOGLE_SITE_VERIFICATION, submit sitemap.xml);
  lawyer check of Privacy/Terms and of Uzbek personal-data storage rules; test Click/Payme in their sandboxes once he has a contract
  (Payme works only with legal entities); Uzum (needs its technical docs); password reset by email; analytics.
- **Step 7: bigger features.** Word/Excel/PowerPoint to PDF and back (needs Docker + LibreOffice, so
  paid Render or another host), OCR (Tesseract, supports Uzbek), visual editor (add text, images,
  signature), page reorder/delete with thumbnails, Uzbek letters in watermark (add a font file),
  convert Cyrillic <-> Latin INSIDE PDF/Word files (his unique feature), a custom domain.
- Also on his idea list: Android/web teaching platform about the new alphabet (separate project).

## 10. Commands cheat sheet (PowerShell, in `D:\nexuz-pro`)
```
venv\Scripts\activate
pip install -r requirements-dev.txt
pytest
uvicorn app.main:app --reload          # open http://127.0.0.1:8000
git add .
git commit -m "message"
git push
```

## 11. Honest status of Step 6 (read this)
- The Step 6 build sandbox had NO FastAPI and NO PyMuPDF and no network, so the full test suite (TestClient tests, PDF tests) was NOT run there.
  What was run: all logic tests (accounts, limits, payments, locales: 48 passed), a template render check in 3 languages, and a smoke script
  that calls the route functions directly. The TestClient tests (test_api_accounts.py, test_api_payments.py, test_pages.py) are written but
  were run only on his computer, if at all. If he reports failures, fix those first.
- Payments (Click, Payme) follow the public docs but were never run against the providers' test servers. Uzum is not built.
- PostgreSQL code path (psycopg) was not run; SQL is the same as for SQLite except `?` -> `%s`.

## 12. Suggested first message in the new chat
"I am continuing my project Nexuz. Read HANDOFF.md (attached) and the project files. Steps 1 to 6 are done.
First help me finish the Step 6 leftovers (section 9), then start Step 7. Explain every step simply, like before: build it, test it, give me a ZIP, and tell me exactly
what to do on Windows."

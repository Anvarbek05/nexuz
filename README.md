# Nexuz

Free online PDF tools (merge, split, rotate, compress, convert). Built with Python (FastAPI) and plain HTML/CSS/JS.

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

## Project structure
```
app/
  main.py        entry point
  config.py      settings
  routers/       API routes (one file per group of tools)
  services/      PDF logic (no web code here)
static/          website: index.html, css/, js/
tests/           automatic tests
render.yaml      Render deployment config
```

## Progress
- [x] Step 1: project skeleton
- [x] Step 2: new design, home page with tool cards, working Merge PDF tool

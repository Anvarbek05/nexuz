# How to put this version into your existing project (Windows)

Use the simplest, safest way: replace three folders and the files in the project root.

1. Close `uvicorn` in the VS Code terminal (press Ctrl+C).
2. Extract the zip. You get a folder named `nexuz-pro`. Open it: you must see `app`, `static`, `tests`, `requirements.txt` directly inside.
3. Open your project folder (`D:\nexuz-pro`) in File Explorer.
4. DELETE these three folders from your project: `app`, `static`, `tests`.
   (Do NOT delete `venv` or `.git`.)
5. COPY into your project, from the extracted folder: `app`, `static`, `tests`, and the files
   `requirements.txt`, `requirements-dev.txt`, `render.yaml`, `README.md`, `.gitignore`.
   Choose "Replace the files" if asked.
6. Check that `D:\nexuz-pro\tests\test_tools.py` exists, and that there is NO `tests\tests` folder.
7. In the VS Code terminal:
   venv\Scripts\activate
   pip install -r requirements-dev.txt
   pytest                      (expect: 37 passed)
   uvicorn app.main:app --reload
8. Open http://127.0.0.1:8000 and try the tools.
9. Save to GitHub (Render redeploys by itself):
   git add .
   git commit -m "Step 4: Uzbek converter, protect and unlock"
   git push

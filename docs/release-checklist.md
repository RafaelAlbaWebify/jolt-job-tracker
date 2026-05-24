# JOLT Release Checklist

Use this before publishing, sharing, or recording a portfolio walkthrough.

## Verification Commands

Backend:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
uvicorn app.main:app --reload --no-use-colors
```

Frontend:

```powershell
cd frontend
npm install
npm run build
npm run dev
```

## Local Demo Check

- Start the backend at `http://127.0.0.1:8000`.
- Start the frontend at `http://localhost:5173`.
- Confirm the backend health badge is online.
- Load demo jobs on the Capture page.
- Run capture review.
- Confirm decision cards appear with reasons, warnings, missing information, parser confidence, and capture notes.
- Export XLSX and confirm the UI shows a generated local path under `backend/data/exports/`.
- Save the run to history.
- Open History / Tracker and update one application status.
- Open About and confirm the current milestone and demo safety copy are visible.
- Capture screenshots using `docs/screenshots/README.md` if preparing a public post or README update.
- Optionally run `Clean local demo data`.

## Page Text / HTML Check

- Switch Capture to `Page text / HTML`.
- Paste synthetic multi-job text from `docs/demo-checklist.md`.
- Click `Extract and review`.
- Confirm multiple jobs are extracted when labels/separators are clear.
- Confirm browser automation remains disabled and no external website is accessed.

## Repository Hygiene Check

```powershell
git status --short
git ls-files backend/data
git ls-files *.xlsx
git ls-files *.csv
git ls-files *.jsonl
git ls-files *.log
```

Expected:

- No generated export/history data is staged.
- No real XLSX, CSV, JSONL, log, or raw captured job data is tracked.
- `backend/data/exports/` and `backend/data/history/` remain ignored generated-data locations.
- Only source, docs, tests, package files, and portfolio-safe demo/default config are tracked.

## Release Notes

- Current milestone: local portfolio demo.
- Working capture modes are manual jobs and user-provided page text / HTML.
- Browser-assisted capture is an explicit disabled/experimental placeholder.
- No Playwright, Selenium, scraping, auto-apply, credential storage, database, or authentication is implemented.

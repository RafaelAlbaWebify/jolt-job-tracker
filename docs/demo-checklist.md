# LinkAut Demo Checklist

Use this checklist for a GitHub, LinkedIn, or portfolio walkthrough of the current safe local demo.

## Start The Backend

From the repository root:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pytest
uvicorn app.main:app --reload --no-use-colors
```

Expected result:

- Backend starts at `http://127.0.0.1:8000`.
- `GET /api/health` returns a running backend response.

## Start The Frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm run build
npm run dev
```

Expected result:

- Frontend starts at `http://localhost:5173`.
- Production build passes before the demo server starts.

## Demo Click Path

1. Open `http://localhost:5173`.
2. Confirm the backend badge says the backend is online.
3. Stay on the Capture page.
4. Confirm the capture health panel says browser automation is disabled.
5. Select `Rafael Default` or another available profile.
6. Click `Load demo jobs`.
7. Confirm several staged raw jobs appear.
8. Click `Run capture review`.
9. Review the dashboard counts for Apply, Maybe, Discard, Manual Review, Duplicate, and Errors.
10. Use the decision filters to show Apply, Discard, Manual Review, and Errors.
11. Open expandable card sections for warnings, missing information, matched keywords, and raw staged preview.
12. Click `Export JSON`, `Export CSV`, or `Export XLSX`.
13. Confirm the UI shows generated paths under `data/exports/`.
14. Click `Save to history`.
15. Open History / Tracker.
16. Confirm saved jobs appear with decision, score, parser confidence, saved date, and application status.
17. Change one status to `Applied`, `Interview`, `Watchlist`, or `Archived`.
18. Open About.
19. Confirm the page explains local-only demo safety and intentionally disabled automation.
20. Optionally check the cleanup confirmation and click `Clean local demo data`.
21. Confirm deleted export/history file counts are shown.
22. Open the Rule Profiles page.
23. Confirm Rafael Default is labeled as a demo/default preset, not global hardcoded behavior.

## Page Text / HTML Capture Demo

1. Return to the Capture page.
2. Select `Page text / HTML`.
3. Paste synthetic page text with two job blocks, each using `Title:`, `Company:`, and `Location:` labels.
4. Add an optional source URL.
5. Click `Extract and review`.
6. Confirm the same parser, decision engine, review cards, export, and history controls are used.
7. Explain that this mode uses user-provided pasted content and does not automate a browser.

## Suggested Short Demo Flow

1. Start backend and frontend.
2. Load demo jobs.
3. Run capture review.
4. Export XLSX.
5. Save to history.
6. Update one status.
7. Optionally clean local demo data from About.

## Expected Visible Results

- A good remote support-style role should produce an Apply-style result.
- A mandatory unsupported language role should be discarded under Rafael Default.
- A far-away hybrid/onsite role should be discarded when distance/location rules apply.
- A low-information job should produce Manual Review or Maybe-style uncertainty.
- Decision cards should show score, priority, parser confidence, reasons, warnings, missing information, and matched keywords.
- Export controls should generate local JSON, CSV, and XLSX files under ignored `backend/data/exports/`.
- Save to history should persist reviewed jobs under ignored `backend/data/history/`.
- History / Tracker should allow local application status updates across page visits.
- About should explain demo safety and allow manual cleanup of generated local demo exports/history.
- Page text / HTML capture should split clear synthetic job blocks and fall back to one reviewed item when structure is unclear.

## Useful Screenshots

For GitHub or LinkedIn, capture:

- Capture page before running demo jobs, showing the safe boundary note and capture health.
- Staged demo jobs after clicking `Load demo jobs`.
- Review dashboard after `Run capture review`, showing decision counts.
- One Apply decision card with reasons and positive keywords.
- One Discard decision card showing a hard discard reason.
- One Manual Review / uncertain result showing parser confidence or missing information.
- Export package controls showing generated local file paths.
- History / Tracker showing saved jobs and the application status selector.
- About page showing local-only privacy notes and cleanup confirmation.
- Rule Profiles page showing Rafael Default as a demo/default profile.

## What To Say During The Demo

- LinkAut is a local job-offer decision assistant.
- The current demo uses manual raw job text and simulated capture runs.
- Browser automation and LinkedIn scraping are intentionally disabled in this safe boundary.
- Page text / HTML capture is local, user-controlled, and based on content the user supplies.
- The real backend parser, configurable profiles, and decision engine are used.
- Export files are local generated artifacts and are ignored by Git.
- History is local generated data and is ignored by Git.
- The cleanup button only removes generated local exports/history and does not touch source code.
- The project is designed to make uncertainty visible rather than hide it.

## Do Not Demo As Implemented Yet

These are future phases:

- real browser automation;
- LinkedIn scraping;
- database-backed or cloud-synced history/tracker;
- downloadable export streaming;
- full multi-sheet application tracker workflow;
- profile editing UI;
- authentication;
- production deployment.

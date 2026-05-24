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
12. Open the Rule Profiles page.
13. Confirm Rafael Default is labeled as a demo/default preset, not global hardcoded behavior.

## Expected Visible Results

- A good remote support-style role should produce an Apply-style result.
- A mandatory unsupported language role should be discarded under Rafael Default.
- A far-away hybrid/onsite role should be discarded when distance/location rules apply.
- A low-information job should produce Manual Review or Maybe-style uncertainty.
- Decision cards should show score, priority, parser confidence, reasons, warnings, missing information, and matched keywords.

## Useful Screenshots

For GitHub or LinkedIn, capture:

- Capture page before running demo jobs, showing the safe boundary note and capture health.
- Staged demo jobs after clicking `Load demo jobs`.
- Review dashboard after `Run capture review`, showing decision counts.
- One Apply decision card with reasons and positive keywords.
- One Discard decision card showing a hard discard reason.
- One Manual Review / uncertain result showing parser confidence or missing information.
- Rule Profiles page showing Rafael Default as a demo/default profile.

## What To Say During The Demo

- LinkAut is a local job-offer decision assistant.
- The current demo uses manual raw job text and simulated capture runs.
- Browser automation and LinkedIn scraping are intentionally disabled in this safe boundary.
- The real backend parser, configurable profiles, and decision engine are used.
- The project is designed to make uncertainty visible rather than hide it.

## Do Not Demo As Implemented Yet

These are future phases:

- real browser automation;
- LinkedIn scraping;
- persistent history/tracker;
- XLSX/export package;
- profile editing UI;
- authentication;
- production deployment.

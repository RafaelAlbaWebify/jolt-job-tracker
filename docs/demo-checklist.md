# JOLT Demo Checklist

Use this checklist for a GitHub, LinkedIn, or portfolio walkthrough of the current safe local demo.

Current milestone: local portfolio demo. For pre-release verification, also see `docs/release-checklist.md`.

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
17. Use the queue cards for `Apply Today`, `Manual Review`, `Waiting`, `Follow Up`, and `Duplicates / Reviewed`.
18. Change one status to `Apply Today`, `Waiting`, `Follow Up`, `Applied`, or `Archived`.
19. Open About.
20. Confirm the page explains local-only demo safety and intentionally disabled automation.
21. Optionally check the cleanup confirmation and click `Clean local demo data`.
22. Confirm deleted export/history file counts are shown.
23. Open the Rule Profiles page.
24. Confirm Rafael Default is labeled as a demo/default preset, not global hardcoded behavior.

## Page Text / HTML Capture Demo

1. Return to the Capture page.
2. Select `Page text`.
3. Paste synthetic page text with two job blocks, each using `Title:`, `Company:`, and `Location:` labels.
4. Add an optional source URL.
5. Click `Extract page text and review`.
6. Confirm the same parser, decision engine, review cards, export, and history controls are used.
7. Try a second synthetic sample using `---`, `Job Card`, or compact title/company/location blocks to show cleaner multi-job extraction.
8. Try copied card-style text with `Company logo`, title, company, location, and state lines such as `Viewed` or `Applied` to show safe legacy-inspired extraction.
9. Open capture diagnostics to show candidate cards, accepted/rejected counts, source URL notes, and capture confidence.
10. Open a result card's capture notes to show extraction hints and source URL inference.
11. Explain that this mode uses user-provided pasted content and does not automate a browser.

Example synthetic multi-job text:

```text
Title: Microsoft 365 Support Specialist
Company: Example SaaS
Location: Remote, Spain
Work mode: Remote
URL: https://example.test/jobs/123
English required.
---
Job Card
Role: IT Support Engineer
Employer: Example Desk
Location: Vigo, Spain
Work mode: Onsite
English required.
```

For HTML fragment capture:

1. Select `HTML fragment`.
2. Paste a synthetic `<article>` or copied card fragment with an `<a href="https://example.test/jobs/123">` job link.
3. Click `Extract HTML and review`.
4. Confirm JOLT extracts the job locally and preserves the anchor URL.

## Suggested Short Demo Flow

1. Start backend and frontend.
2. Load demo jobs.
3. Run capture review.
4. Export XLSX.
5. Save to history.
6. Review queue cards and update one status.
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
- Page text / HTML capture should split clear synthetic job blocks, reject tiny/noisy fragments, and fall back to one reviewed item when structure is unclear.
- Capture diagnostics should show input size, candidate cards, accepted/rejected cards, source URL notes, and capture confidence.
- If the same synthetic job is saved to history and captured again, the result should show a duplicate preview warning.

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
- History / Tracker page showing queue cards and statuses without hiding duplicates.

## What To Say During The Demo

- JOLT is a local job-offer decision assistant.
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

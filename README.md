# JOLT — Job Opportunity Logic Tracker

Local job-search decision assistant built with React and FastAPI.

JOLT helps review job opportunities faster by parsing user-provided job text, applying configurable fit rules, explaining Apply / Maybe / Discard / Manual Review decisions, exporting results, and tracking reviewed jobs locally.

Current milestone: local portfolio demo.

JOLT is not a LinkedIn scraper, not a mass-apply bot, and not a black-box recommender. Browser automation is represented as an explicit disabled/experimental placeholder; the working capture modes use user-provided content, including an optional manual bookmarklet/helper that the user clicks to copy visible page content into JOLT.

## What It Does

- Reviews batches of job-offer text through one local workflow.
- Parses title, company, location, work mode, languages, risk signals, parser confidence, and notes.
- Applies reusable rule profiles instead of hardcoding one person's preferences globally.
- Produces explainable decisions with score, priority, reasons, warnings, missing information, parser confidence, and matched keywords.
- Exports reviewed results as JSON, CSV, or a workflow-oriented multi-sheet XLSX.
- Saves new reviewed jobs into a local history/tracker, skips duplicates by default, and supports application status updates.
- Provides a local demo cleanup action for generated export/history files.

## Current Workflow

```text
manual jobs or pasted page text/HTML
-> parser
-> configurable rule profile
-> decision engine
-> review dashboard
-> Apply Today / Manual Review / Waiting / Follow Up queues
-> JSON / CSV / XLSX export
-> local history / tracker
-> optional demo cleanup
```

The Capture page is the primary workflow. Manual paste exists as a fallback/debug mode, and page text / HTML capture is a safe local bridge for content the user supplies.

## Implemented Features

- React + Vite local frontend.
- FastAPI local backend.
- Backend health check at `GET /api/health`.
- Configurable rule profiles loaded from backend JSON.
- Rafael Default as one demo/default profile, not global frontend logic.
- Rule Profiles page for inspecting available profiles and profile details.
- Rule-based parser with parser confidence and parser notes.
- Decision engine with explainable scoring and hard-discard rules.
- Capture runner for manual `raw_jobs`, pasted page text, HTML fragments, uploaded/copied HTML content, and pasted `JOLT_CAPTURE_V1` manual browser helper payloads.
- Conservative page text/HTML extractor for labelled blocks, `Job Card` sections, copied left-panel-style card text, compact job-board-like text, copied HTML cards, visible URLs, and anchor links.
- Capture diagnostics showing input size, candidate cards found, accepted/rejected cards, source URL notes, and capture confidence.
- Duplicate preview against local history before saving, without silently dropping likely duplicates.
- Capture health endpoint showing browser automation disabled by default.
- Experimental LinkedIn capture scaffold with disabled-by-default health/start/stop/status API responses, URL/currentJobId utilities, mock dry-run package generation, selected-job-only prototype capture, legacy batch capture port, diagnostics, and review conversion into the normal capture pipeline.
- Frontend review dashboard with demo jobs, decision counts, filters, and decision cards.
- Local export package generation under ignored `backend/data/exports/`.
- JSON, CSV, and multi-sheet XLSX export formats.
- Local JSONL history/tracker under ignored `backend/data/history/`.
- Save-to-history, queue filters, backward-compatible status updates, duplicate skip reporting, and optional visible Duplicate / Already Reviewed records.
- Demo cleanup endpoint and UI for local exports/history.
- Backend tests for health, profiles, parser, decision engine, capture, export, history, and cleanup.
- Frontend production build with `npm run build`.

## Safe Capture Modes

| Mode | Status | What it does |
| --- | --- | --- |
| Manual jobs | Implemented | User stages one or more raw job texts in the Capture page. |
| Page text | Implemented | User pastes visible page text; JOLT extracts local job blocks and sends them through the same parser and decision engine. |
| HTML fragment / uploaded HTML content | Implemented | User provides copied HTML locally; JOLT strips page noise, preserves likely job links, and extracts job cards conservatively. |
| Manual browser helper | Implemented | User manually clicks a bookmarklet/helper on a page they already opened; it copies visible card text and URLs for pasting into Page text mode. |
| Experimental LinkedIn local capture | Disabled experimental scaffold | Backend/API/UI boundary exists behind `JOLT_ENABLE_EXPERIMENTAL_LINKEDIN_CAPTURE=false` by default. When enabled, mock dry runs use fake data, the selected-job prototype can read the current URL plus visible copied page text for one manually selected job, and the legacy batch port can perform user-supervised local card clicks with strict limits. |

Page text / HTML and manual helper capture are local and user-controlled. The helper does not open pages, navigate, crawl, store credentials, bypass authentication, bypass CAPTCHA, or submit applications.

The experimental LinkedIn capture scaffold is not connected to Save to History automatically. When the flag is enabled, it can generate a mock package with fake jobs under ignored local data, capture one currently selected job after a focus handoff countdown, or run the legacy batch capture port with user-supervised local browser control. Batch mode uses legacy-style visual ROI/title-signal card detection, may click detected left-panel cards, copy URL/text, scroll, and optionally use `start=` pagination within `max_jobs`, `max_pages`, timeout, and stop limits. URL-only, too-short, missing-ID, and duplicate-ID captures are diagnosed instead of counted as successful new jobs. It still performs no Selenium, Playwright, login, credential storage, CAPTCHA/rate-limit bypass, auto-apply, or recruiter messaging. The selected-job and legacy batch prototypes are Windows/local and depend on optional experimental keyboard/clipboard support.

Optional selected-job capture dependencies are intentionally separate from normal requirements:

```bash
cd backend
pip install -r requirements-experimental.txt
```

## What It Intentionally Does Not Do

- No Playwright or Selenium automation.
- No LinkedIn scraping.
- No mass crawling.
- No auto-apply behavior.
- No credential storage.
- No CAPTCHA, paywall, rate-limit, or authentication bypass.
- No profile editing UI yet.
- No database or cloud sync.
- No production deployment.

These are intentional boundaries for the current portfolio demo, not failed features.

## Tech Stack

Frontend:

- React
- TypeScript
- Vite
- Plain CSS

Backend:

- FastAPI
- Pydantic models
- Rule-based parser and decision services
- JSON-backed profiles
- JSONL local history
- `openpyxl` for XLSX export
- `pytest` + FastAPI `TestClient`

## Local Setup

These commands are Windows-friendly and assume you are at the repository root.

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pytest
uvicorn app.main:app --reload --no-use-colors
```

Backend URL:

```text
http://127.0.0.1:8000
```

### Frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm run build
npm run dev
```

Frontend URL:

```text
http://localhost:5173
```

## Demo Flow

1. Start the backend.
2. Start the frontend.
3. Open `http://localhost:5173`.
4. Confirm the backend badge is online.
5. On Capture, select `Rafael Default` or another profile.
6. Click `Load demo jobs`.
7. Click `Run capture review`.
8. Review Apply / Discard / Manual Review cards.
9. Export the current capture run as JSON, CSV, or the multi-sheet XLSX workflow tracker.
10. Click `Save to history` and confirm new jobs were saved while duplicates were skipped.
11. Open History / Tracker, review the Apply Today / Manual Review / Waiting / Follow Up queues, update one application status, and export the saved tracker data with latest statuses.
12. Open About and optionally clean local demo data.

Page text / HTML demo:

1. Switch Capture to `Page text` or `HTML fragment`.
2. Paste synthetic labelled job blocks, copied HTML, or a `JOLT_CAPTURE_V1` payload copied by the manual browser helper.
3. Click `Extract page text and review` or `Extract HTML and review`.
4. Open capture diagnostics and capture notes to see extraction hints, source URL notes, accepted/rejected candidate counts, and duplicate preview warnings.

More demo steps are in [docs/demo-checklist.md](docs/demo-checklist.md).

## API Endpoints

Run the backend locally, then use `http://127.0.0.1:8000`.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Backend health check. |
| GET | `/api/profiles` | List rule profile summaries. |
| GET | `/api/profiles/{profile_id}` | Load one full rule profile. |
| POST | `/api/parse/job` | Parse raw job text into a normalized job object. |
| POST | `/api/parse-and-classify/job` | Parse raw job text and classify it with a profile. |
| POST | `/api/classify/job` | Classify an already-normalized job. |
| GET | `/api/capture/health` | Report safe capture modes and automation status. |
| POST | `/api/capture/run` | Run capture review from manual jobs or pasted page text/HTML. |
| GET | `/api/experimental-capture/linkedin/health` | Report disabled/dry-run status for the experimental LinkedIn capture scaffold. |
| POST | `/api/experimental-capture/linkedin/start` | Return disabled by default, or run `mock_dry_run`, `selected_job_only`, or `legacy_batch_capture` when explicitly enabled. |
| POST | `/api/experimental-capture/linkedin/stop` | Safe no-op stop boundary for the experimental scaffold. |
| GET | `/api/experimental-capture/linkedin/status` | Report disabled/idle/dry-run scaffold status. |
| POST | `/api/experimental-capture/linkedin/review-latest` | Convert the latest experimental package into normal capture review cards with a selected profile; nothing is auto-saved. |
| POST | `/api/export/capture-result` | Generate JSON, CSV, or XLSX files from a capture result. |
| POST | `/api/export/history` | Generate JSON, CSV, or XLSX files from saved History / Tracker data. |
| POST | `/api/history/save-capture-result` | Save reviewed capture results into local history. |
| GET | `/api/history/jobs` | List saved reviewed jobs. |
| GET | `/api/history/jobs/{history_id}` | Load one saved job. |
| PATCH | `/api/history/jobs/{history_id}/status` | Update a saved job's application status. |
| POST | `/api/demo/cleanup` | Delete generated local demo files under `backend/data/exports/` and `backend/data/history/`. |

## Screenshots

### Capture workflow

Capture starts from a local portfolio demo workflow with profile selection, capture health, and manual/page-text modes.

![Capture page](docs/screenshots/01-capture-page.png)

### Page text / HTML capture

Page text mode accepts user-provided visible page text or copied HTML and keeps browser automation disabled.

The Capture page also includes a manual browser helper/bookmarklet. Install it as a browser bookmark first; clicking the helper inside JOLT will not capture jobs, and Chrome may block `javascript:` URLs pasted or clicked directly. The user opens a job results page themselves, clicks the installed bookmark there, and pastes the copied `JOLT_CAPTURE_V1` payload back into JOLT. It only inspects visible content in the current page when clicked and does not automate browsing.

Chrome setup: press `Ctrl + Shift + B`, copy the bookmarklet code from JOLT, right-click the bookmarks bar, choose Add page, name it `JOLT Capture`, paste the copied code into URL, then use that bookmark on a page you opened manually.

![Page text capture](docs/screenshots/02-page-text-capture.png)

### Review dashboard

Capture results are parsed, classified, filtered, and displayed as explainable decision cards.

![Review dashboard](docs/screenshots/03-review-dashboard.png)

### Export package

Reviewed capture results can be exported locally as JSON, CSV, or a multi-sheet XLSX with Summary, All Reviewed Jobs, Apply Today, Manual Review, Waiting / Follow Up, Duplicates / Already Reviewed, Decision Explanations, and Capture Diagnostics sheets. History / Tracker also has its own export action that uses the latest saved statuses.

![Export controls](docs/screenshots/04-export-controls.png)

### History / Tracker

Reviewed jobs can be saved locally and tracked with application statuses. `Save to history` saves new jobs and skips duplicates by default, preserving any existing tracker status. Changing a status in History / Tracker persists immediately; `Save to history` is only needed after a new capture review.

![History tracker](docs/screenshots/05-history-tracker.png)

### Local demo safety

The About page documents the local-only demo boundary, disabled automation, and cleanup control.

![About and demo safety](docs/screenshots/06-about-demo-safety.png)

See [docs/screenshots/README.md](docs/screenshots/README.md) for the screenshot plan.

## Documentation

- [Architecture](docs/architecture.md)
- [Demo checklist](docs/demo-checklist.md)
- [Release checklist](docs/release-checklist.md)
- [Portfolio walkthrough](docs/portfolio-walkthrough.md)
- [GitHub presentation notes](docs/github-presentation.md)
- [Interview explanation](docs/interview-explanation.md)
- [LinkedIn post draft](docs/linkedin-post-draft.md)
- [Engineering log](docs/engineering-log.md)

## Roadmap

- Add downloadable export UX.
- Add richer queue ranking and bulk status actions.
- Improve already-reviewed labels in exports.
- Add profile editing and validation UI.
- Add optional browser-assisted capture only if it can remain explicit, local, recoverable, and respectful of site terms.
- Add a short demo video.

## Privacy And Repository Hygiene

Generated/private job-search data is ignored by Git, including real exports, CSV/JSONL outputs, XLSX trackers, local history, private run folders, logs, local env files, and user-specific profiles.

Do not commit real captured job text, recruiter notes, application history, personal data, access tokens, generated trackers, or private exports.

The demo cleanup button removes generated local files under:

```text
backend/data/exports/
backend/data/history/
```

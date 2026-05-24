# LinkAut Job Search Assistant

Local job-offer decision assistant for fast, explainable job review.

LinkAut is a local React + FastAPI app that helps turn messy job-offer text into structured, explainable decisions. It is built for a human-in-the-loop job search workflow: capture or paste job text, parse it, apply a configurable rule profile, review the result, and decide what deserves attention.

It is not a mass-apply bot, not a black-box recommender, and not currently a LinkedIn scraper. The current safe demo boundary uses manually supplied raw job text and simulated capture runs. Browser automation is intentionally disabled until a safer, isolated capture adapter is added in a later phase.

## Current Workflow

```text
raw job text / simulated capture
-> parser
-> configurable rule profile
-> decision engine
-> review dashboard
-> local export package
-> local history / application tracker
```

The frontend Capture page can load demo jobs, send them to the backend through `POST /api/capture/run`, and display parsed + classified results as decision cards.

Current decision labels:

- Apply
- Maybe
- Discard
- Manual Review
- Duplicate

Explainable outputs include:

- score
- priority
- reasons
- warnings
- missing information
- parser confidence
- matched positive keywords
- matched risk keywords

## What Problem It Solves

Job search review is repetitive: the same language, location, work-mode, schedule, and fit checks need to happen again and again. LinkAut makes that review faster and more consistent while keeping the user in control.

The goal is not to hide uncertainty. Low parser confidence, missing work mode, unclear location, risky shift/on-call language, and unsupported mandatory languages are surfaced in the decision output so the user can review them honestly.

## Implemented Features

- React + Vite local frontend.
- FastAPI local backend.
- Backend health check at `GET /api/health`.
- Configurable rule profile system.
- Rafael Default profile as one demo/default profile, not global hardcoded frontend logic.
- Rule Profiles page for viewing available profiles and full profile details.
- Rule-based parser with parser confidence.
- Parser endpoint: `POST /api/parse/job`.
- Combined parse/classify endpoint: `POST /api/parse-and-classify/job`.
- Classification endpoint: `POST /api/classify/job`.
- Backend decision engine with explainable scoring and hard-discard rules.
- Safe capture runner boundary using manual `raw_jobs`.
- Capture health endpoint showing browser automation disabled.
- Frontend Capture dashboard with demo jobs.
- Review result cards with decision, score, priority, parser confidence, reasons, warnings, missing information, matched keywords, and raw preview.
- Filtered result view by decision or errors.
- Local export package generation for capture review results.
- JSON, CSV, and XLSX export formats under ignored `backend/data/exports/`.
- Local history/tracker persistence under ignored `backend/data/history/`.
- Save reviewed capture runs to history and update application status locally.
- Demo cleanup endpoint and UI button for clearing local exports/history.
- Backend tests for profiles, parsing, classification, capture runner, export, history, and health.
- Frontend production build with `npm run build`.

## Architecture

### Frontend

- React + Vite.
- Capture page as the main workflow screen.
- Rule Profiles page for profile inspection.
- API client in `frontend/src/api.ts`.
- App shell and dashboard UI in `frontend/src/App.tsx`.

### Backend

- FastAPI app under `backend/app`.
- API routers under `backend/app/api`.
- Profile service for loading default profiles.
- Parser service for conservative raw-text normalization.
- Decision engine for profile-based scoring and labels.
- Capture runner for simulated capture runs over manual raw jobs.
- Export service for JSON, CSV, and XLSX files generated from capture review results.
- History store for local reviewed-job persistence, duplicate detection, and application status updates.
- Demo cleanup service for removing generated local demo exports/history.

### Data Flow

```text
manual raw jobs
-> POST /api/capture/run
-> parser service
-> decision engine
-> capture run result
-> frontend review dashboard
-> POST /api/export/capture-result
-> backend/data/exports/
-> optional POST /api/history/save-capture-result
-> backend/data/history/
```

For more detail, see [docs/architecture.md](docs/architecture.md).

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
| GET | `/api/capture/health` | Report current safe capture mode and automation status. |
| POST | `/api/capture/run` | Run a simulated capture batch from manual raw jobs. |
| POST | `/api/export/capture-result` | Generate JSON, CSV, or XLSX files from a capture run result. |
| POST | `/api/history/save-capture-result` | Save reviewed capture results into local history. |
| GET | `/api/history/jobs` | List saved reviewed jobs. |
| GET | `/api/history/jobs/{history_id}` | Load one saved job. |
| PATCH | `/api/history/jobs/{history_id}/status` | Update a saved job's application status. |
| POST | `/api/demo/cleanup` | Delete generated local demo files under `backend/data/exports/` and `backend/data/history/`. |

Example capture request:

```json
{
  "profile_id": "rafael_default",
  "source": "manual_frontend",
  "dry_run": true,
  "max_results": 3,
  "raw_jobs": [
    {
      "source": "manual_frontend",
      "raw_text": "Title: Microsoft 365 Support Specialist\nCompany: Example SaaS\nLocation: Remote, Spain\nWork mode: Remote\nEnglish required."
    }
  ]
}
```

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

The backend runs at:

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

Open:

```text
http://localhost:5173
```

## Demo Workflow

1. Start the backend.
2. Start the frontend.
3. Open `http://localhost:5173`.
4. Go to the Capture page.
5. Confirm the backend health badge is online.
6. Click `Load demo jobs`.
7. Click `Run capture review`.
8. Review Apply / Discard / Manual Review result cards.
9. Optionally click `Export JSON`, `Export CSV`, or `Export XLSX` to generate local files under `backend/data/exports/`.
10. Optionally click `Save to history`, then open History / Tracker and update an application status.
11. Open About to review demo safety and optionally clean local demo data.
12. Open Rule Profiles to confirm Rafael Default is a demo/default profile, not a global hardcoded rule set.

See [docs/demo-checklist.md](docs/demo-checklist.md) for a reviewer/demo checklist.

## Demo Safety

The built-in demo jobs are synthetic. Browser automation and LinkedIn scraping are disabled in the current safe boundary. Generated exports and history are local files under `backend/data/`, ignored by Git, and can be cleared from the About page with `Clean local demo data`.

Do not commit real captured job text, recruiter notes, application history, or generated tracker files.

## Current Limitations

These are intentionally not implemented yet:

- real browser automation;
- LinkedIn scraping;
- profile editing UI;
- authentication;
- production deployment.

These are future phases, not failed features. The current milestone focuses on a safe local demo boundary and the verified parser -> profile -> decision engine -> review dashboard chain.

## Roadmap

- Phase 7: portfolio README and documentation.
- Phase 8: local export package for capture review results.
- Phase 9: local history tracker and application status persistence.
- Next: richer XLSX tracker sheets and downloadable export UX.
- Later: safer browser-assisted capture adapter behind the existing capture boundary.
- Later: profile editing and validation UI.
- Later: packaging, demo screenshots, and portfolio walkthrough materials.

## Repository Hygiene

Private/generated job-search data is ignored by Git, including logs, real captures, real exports, XLSX trackers, CSV/JSONL outputs, private run folders, local env files, and user-specific profiles.

Do not commit real captured job text, private job history, recruiter notes, personal application data, access tokens, or real tracker exports.

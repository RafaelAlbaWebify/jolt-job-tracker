# JOLT Architecture

## Purpose

JOLT is a local job-offer decision assistant for fast, explainable job review. The current implementation proves the core review chain:

```text
manual raw job text or pasted page text/HTML
-> parser
-> configurable rule profile
-> decision engine
-> frontend review dashboard
-> optional export and local history
```

The project is intentionally local-first and human-in-the-loop. It helps a job seeker review and prioritize roles, but it does not apply to jobs automatically and does not currently scrape LinkedIn.

Current milestone: local portfolio demo.

## Current Repository Shape

```text
backend/
  app/
    api/
      capture.py
      classify.py
      demo.py
      export.py
      health.py
      history.py
      parse.py
      profiles.py
    config/
      default_profiles.json
    services/
      capture_runner.py
      browser_capture.py
      decision_engine.py
      export_package.py
      demo_cleanup.py
      history_store.py
      parser.py
      profiles.py
    main.py
    models.py
  tests/

frontend/
  src/
    api.ts
    App.tsx
    main.tsx
    styles.css
```

## Backend Services

### FastAPI App

`backend/app/main.py` creates the FastAPI app, configures local CORS for the Vite dev server, and mounts API routers.

### Profile Service

`backend/app/services/profiles.py` loads read-only default rule profiles from `backend/app/config/default_profiles.json`.

Profiles define language rules, work-mode preferences, location constraints, positive keywords, risk keywords, discard keywords, stretch skills, risk severity settings, and portfolio-safety metadata.

Rafael Default is one demo/default profile. It is not global hardcoded application behavior.

### Parser Service

`backend/app/services/parser.py` converts raw job-offer text into the normalized job shape used by the decision engine.

The parser is rule-based and conservative. It detects fields such as title, company, location, work mode, mandatory languages, shift/on-call indicators, positive/risk keywords, parser confidence, and parser notes.

### Decision Engine

`backend/app/services/decision_engine.py` classifies an already-normalized job with the selected rule profile.

The engine returns explainable outputs:

- decision;
- score;
- priority;
- reasons;
- triggered rules;
- warnings;
- missing information;
- matched positive keywords;
- matched risk keywords;
- parser confidence;
- profile ID.

Hard discard rules override positive scoring.

### Capture Runner

`backend/app/services/capture_runner.py` is the current safe capture boundary.

It accepts manually supplied `raw_jobs` or raw jobs produced by capture adapters, parses each job, classifies each parsed job, collects per-job errors, and returns one capture run result.

### Capture Adapter

`backend/app/services/browser_capture.py` currently implements the safe capture adapter boundary for pasted page text/HTML and copied/uploaded HTML content.

Supported modes:

- `manual_raw_jobs`: existing explicit raw job input.
- `page_text`: user-provided copied page text is normalized and conservatively split into job blocks.
- `html_fragment`: user-provided copied HTML is stripped, normalized, and conservatively split into job blocks.
- `uploaded_html_content`: uploaded/copied HTML content follows the same safe local extraction path.
- `browser_assisted`: accepted as an experimental mode but not enabled; no browser automation is attempted.

The adapter does not store credentials, bypass protections, crawl pages, or hardcode LinkedIn as the core architecture.

The page text/HTML extractor is dependency-light and conservative. It handles clear labelled fields, repeated `Job Card` or separator blocks, compact title/company/location listings, simple copied HTML card structures, and job-like links from visible URLs or anchor `href` values. It rejects tiny/noisy candidate cards, reports extraction diagnostics, and returns one fallback captured job with notes when structure is unclear instead of over-splitting page fragments.

### Export Service

`backend/app/services/export_package.py` writes local export files for a capture review result.

Supported formats:

- JSON: structured capture result.
- CSV: flattened review rows.
- XLSX: workbook with a `Capture Review` sheet.

Generated files are written under ignored `backend/data/exports/`. Raw job text is excluded by default and can be included explicitly for local/private review.

### History Store

`backend/app/services/history_store.py` persists reviewed jobs locally under ignored `backend/data/history/`.

The current implementation uses JSONL file storage rather than a database. It can save reviewed capture results, list saved jobs, load one saved job, update application status, and detect duplicates by source URL, external ID, or normalized title/company/location fallback. Capture runs also use this duplicate logic as a preview so likely duplicates are labelled before save rather than silently removed.

### Demo Cleanup

`backend/app/services/demo_cleanup.py` removes generated local demo artifacts from `backend/data/exports/` and `backend/data/history/` only.

The cleanup endpoint is manual, local-only, and path-fenced so it cannot delete source code, specs, default profiles, or arbitrary filesystem paths.

## Frontend Pages

The current frontend is a compact React app rather than a fully split page/component tree.

Implemented views:

- Capture: primary demo workflow, profile selector, capture health, manual jobs, page text/HTML/HTML-fragment capture, capture diagnostics, demo jobs, review dashboard, duplicate preview, decision filters, decision cards.
- Rule Profiles: profile list and profile detail view.
- History / Tracker: saved reviewed jobs, simple filters, and application status updates.
- About: project purpose, demo safety notes, intentionally disabled features, and local cleanup control.
- Review Dashboard and Manual Paste / Debug: visible navigation placeholders for future phases.

## API Surface

Current local endpoints:

- `GET /api/health`
- `GET /api/profiles`
- `GET /api/profiles/{profile_id}`
- `POST /api/parse/job`
- `POST /api/parse-and-classify/job`
- `POST /api/classify/job`
- `GET /api/capture/health`
- `POST /api/capture/run`
- `POST /api/export/capture-result`
- `POST /api/history/save-capture-result`
- `GET /api/history/jobs`
- `GET /api/history/jobs/{history_id}`
- `PATCH /api/history/jobs/{history_id}/status`
- `POST /api/demo/cleanup`

## Current Data Flow

```text
Frontend Capture page
-> user loads demo jobs, stages raw text, pastes page text, or provides HTML content
-> POST /api/capture/run
-> capture runner and adapter validate raw jobs/page content and return diagnostics
-> parser service normalizes raw text
-> decision engine applies selected profile
-> history duplicate preview labels likely already-saved jobs
-> backend returns run summary, diagnostics, and per-job results
-> frontend displays decision overview, filters, and cards
-> user optionally exports JSON, CSV, or XLSX
-> backend writes files under backend/data/exports/
-> user optionally saves reviewed jobs
-> backend writes JSONL history under backend/data/history/
-> History / Tracker displays saved jobs and updates application status
-> About can manually clean generated local demo exports/history
```

## Intentionally Excluded Features

The following are not implemented in the current safe demo:

- LinkedIn scraping;
- real browser automation;
- profile editing UI;
- authentication;
- production deployment.

These exclusions keep the project honest and portfolio-safe while the parser/profile/decision/review chain is being hardened.

## Future Extension Points

- Richer XLSX tracker and auditable run package sheets.
- Apply Today and Manual Review queues built from saved history.
- Richer duplicate/already-reviewed labels using saved history during capture/classification.
- Optional browser-assisted capture adapter with explicit user control and no credential storage.
- Profile editing and validation UI.
- Demo mode with committed fake/anonymized sample runs.
- Broader privacy cleanup preview for logs, runs, and other generated private data.

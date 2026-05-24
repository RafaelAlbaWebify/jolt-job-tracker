# LinkAut Architecture

## Purpose

LinkAut is a local job-offer decision assistant for fast, explainable job review. The current implementation proves the core review chain:

```text
manual raw job text
-> parser
-> configurable rule profile
-> decision engine
-> frontend review dashboard
```

The project is intentionally local-first and human-in-the-loop. It helps a job seeker review and prioritize roles, but it does not apply to jobs automatically and does not currently scrape LinkedIn.

## Current Repository Shape

```text
backend/
  app/
    api/
      capture.py
      classify.py
      health.py
      parse.py
      profiles.py
    config/
      default_profiles.json
    services/
      capture_runner.py
      decision_engine.py
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

It accepts manually supplied `raw_jobs`, parses each job, classifies each parsed job, collects per-job errors, and returns one capture run result. Browser automation is disabled in this phase.

## Frontend Pages

The current frontend is a compact React app rather than a fully split page/component tree.

Implemented views:

- Capture: primary demo workflow, profile selector, capture health, staged raw jobs, demo jobs, review dashboard, decision filters, decision cards.
- Rule Profiles: profile list and profile detail view.
- Review Dashboard, History / Tracker, Manual Paste / Debug, About: visible navigation placeholders for future phases.

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

## Current Data Flow

```text
Frontend Capture page
-> user loads demo jobs or stages raw text
-> POST /api/capture/run
-> capture runner validates raw jobs
-> parser service normalizes raw text
-> decision engine applies selected profile
-> backend returns run summary and per-job results
-> frontend displays decision overview, filters, and cards
```

## Intentionally Excluded Features

The following are not implemented in the current safe demo:

- real browser automation;
- LinkedIn scraping;
- XLSX/export package generation;
- persistent history/tracker storage;
- profile editing UI;
- authentication;
- production deployment.

These exclusions keep the project honest and portfolio-safe while the parser/profile/decision/review chain is being hardened.

## Future Extension Points

- Export service for XLSX tracker and auditable run package.
- History/status service for duplicates, already-reviewed jobs, and application statuses.
- Safer browser-assisted capture adapter behind the existing capture runner boundary.
- Profile editing and validation UI.
- Demo mode with committed fake/anonymized sample runs.
- Privacy cleanup preview and cleanup command.

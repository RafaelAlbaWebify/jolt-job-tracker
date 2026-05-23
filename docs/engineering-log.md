# Engineering Log

## Entry Template

```markdown
## YYYY-MM-DD HH:MM - <Task ID / Change Title>

- Type: Feature | Bugfix | Refactor | Optimization | Test | Docs | Cleanup
- Files changed:
  - ...
- Problem / goal:
  - ...
- Root cause:
  - ...
- Change made:
  - ...
- Tests/checks run:
  - ...
- Result:
  - ...
- Remaining risks / follow-up:
  - ...
```

## 2026-05-23 - Repository Assessment

- Type: Docs
- Files changed:
  - `docs/engineering-log.md`
- Problem / goal:
  - First-pass repository inspection before implementation.
- Change made:
  - Recorded that the repository was a small project shell and that `AGENTS.md` / `specs/` were not present yet at the time of the first assessment.
- Tests/checks run:
  - GitHub file reads for `README.md`, `.gitignore`, and expected SDD paths.
- Result:
  - No app features were implemented.
- Remaining risks / follow-up:
  - Add and assess SDD files before scaffolding application code.

## 2026-05-23 - Phase 0 SDD Reassessment

- Type: Docs / Cleanup
- Files changed:
  - `.gitignore`
  - `docs/engineering-log.md`
- Problem / goal:
  - Re-run Phase 0 after SDD files were added.
  - Compare the current repository state against `AGENTS.md` and `specs/*.md`.
  - Apply the previously proposed `.gitignore` update unless it conflicts with the SDD.
- Root cause:
  - The first assessment happened before the SDD files existed on `main`.
- Change made:
  - Confirmed the SDD files are present.
  - Reconciled the target structure and hygiene rules against the SDD.
  - Updated `.gitignore` to cover Python, React, local env files, private LinkAut generated data, browser automation artifacts, real run packages, private user profiles, editor files, and safe exceptions for anonymized samples/demo data.
  - Documented current repo gaps, proposed target structure, proposed `.gitignore` changes, and next recommended implementation phase.
  - Did not create React or FastAPI files.
  - Did not implement app features.
- Tests/checks run:
  - Read `AGENTS.md`.
  - Read `specs/product-spec.md`.
  - Read `specs/technical-plan.md`.
  - Read `specs/tasks.md`.
  - Read current `.gitignore`.
  - Read existing `docs/engineering-log.md`.
- Result:
  - Phase 0 documentation is aligned with the SDD.
- Remaining risks / follow-up:
  - Existing legacy Streamlit/capture/parser/classifier scripts were not present in the repository at that time.

## 2026-05-23 - Phase 1 Local-Server Skeleton

- Type: Feature / Docs
- Files changed:
  - `backend/main.py`
  - `backend/requirements.txt`
  - `backend/tests/test_health.py`
  - `backend/core/.gitkeep`
  - `backend/capture/.gitkeep`
  - `backend/legacy/.gitkeep`
  - `backend/config/.gitkeep`
  - `frontend/package.json`
  - `frontend/index.html`
  - `frontend/vite.config.ts`
  - `frontend/tsconfig.json`
  - `frontend/src/main.tsx`
  - `frontend/src/App.tsx`
  - `frontend/src/api.ts`
  - `frontend/src/styles.css`
  - `frontend/src/vite-env.d.ts`
  - `docs/engineering-log.md`
- Problem / goal:
  - Create the first minimal React + FastAPI local-server skeleton for LinkAut.
  - Make Capture the first/main page and Manual Paste / Debug clearly secondary.
  - Add a frontend health indicator that calls `GET /api/health`.
  - Avoid implementing real capture, parsing, classification, export, history, XLSX, rule profiles, or legacy pipeline files.
- Root cause:
  - Not applicable; this was new skeleton work.
- Change made:
  - Added a minimal FastAPI app with CORS configured for the local Vite dev server.
  - Added `GET /api/health`, returning backend status, service name, and a short running message.
  - Added a focused backend health test using FastAPI `TestClient`.
  - Added a Vite + React + TypeScript frontend skeleton.
  - Added basic app navigation for Capture, Review Dashboard, Rule Profiles, History / Tracker, Manual Paste / Debug, and About.
  - Set Capture as the default active page.
  - Added a frontend API helper and backend health badge.
- Tests/checks run:
  - Read SDD files and verified committed backend/frontend files by GitHub file readback.
  - Local runtime commands were not run in the connector-only environment.
- Result:
  - Backend and frontend skeletons were added without real workflow logic.
- Remaining risks / follow-up:
  - Run backend and frontend setup/build commands locally.

## 2026-05-23 - Phase 1 Backend Package Structure Repair

- Type: Bugfix / Docs
- Files changed:
  - `backend/app/__init__.py`
  - `backend/app/main.py`
  - `backend/app/api/__init__.py`
  - `backend/app/api/health.py`
  - `backend/tests/test_health.py`
  - `backend/main.py` (removed)
  - `docs/engineering-log.md`
- Problem / goal:
  - Fix backend startup for the documented command from `backend/`: `uvicorn app.main:app --reload`.
  - Preserve the existing `GET /api/health` response behavior.
- Root cause:
  - The initial Phase 1 backend placed the FastAPI app at `backend/main.py`, but the desired package entrypoint was `backend/app/main.py`.
- Change made:
  - Moved the FastAPI application entrypoint into `backend/app/main.py`.
  - Added package initializers for `backend/app/` and `backend/app/api/`.
  - Moved the health endpoint into `backend/app/api/health.py` and included it from `backend/app/main.py`.
  - Updated the health test to import `app` from `app.main`.
  - Removed the obsolete `backend/main.py` entrypoint.
- Tests/checks run:
  - Verified changed files by GitHub file readback.
  - Local runtime verification remained pending.
- Result:
  - Repository structure matched `uvicorn app.main:app --reload`.
- Remaining risks / follow-up:
  - Run local backend startup and health endpoint checks.

## 2026-05-23 - Phase 2 Configurable Rule Profiles

- Type: Feature / Test / Docs
- Files changed:
  - `backend/app/models.py`
  - `backend/app/config/default_profiles.json`
  - `backend/app/services/__init__.py`
  - `backend/app/services/profiles.py`
  - `backend/app/api/profiles.py`
  - `backend/app/main.py`
  - `backend/tests/test_profiles.py`
  - `frontend/src/api.ts`
  - `frontend/src/App.tsx`
  - `frontend/src/styles.css`
  - `docs/engineering-log.md`
- Problem / goal:
  - Add configurable rule profiles as backend data and expose them in the React UI.
  - Keep Rafael's personal rules as one default/demo profile, not global hardcoded behavior.
  - Avoid implementing classification, capture, parser, export, history, manual paste logic, or profile editing.
- Root cause:
  - Not applicable; this was Phase 2 read/display functionality.
- Change made:
  - Added `RuleProfile` and `RuleProfileSummary` backend models.
  - Added default profile storage at `backend/app/config/default_profiles.json`.
  - Added default profiles: `rafael_default`, `generic_remote_it_support`, `saas_support`, and `infrastructure_support`.
  - Added a profile loading service and read-only endpoints: `GET /api/profiles` and `GET /api/profiles/{profile_id}`.
  - Added backend profile tests.
  - Updated the frontend Rule Profiles page to fetch, select, and display profile details.
- Tests/checks run:
  - Read SDD files and verified backend changed files and tests by GitHub file readback.
  - Local commands were not run in the connector-only environment.
- Result:
  - Rule profiles became available through backend config/API and frontend display.
- Remaining risks / follow-up:
  - Run backend tests and frontend build locally.

## 2026-05-23 - Phase 2.1 Backend Development Dependency Cleanup

- Type: Cleanup / Docs
- Files changed:
  - `backend/requirements-dev.txt`
  - `README.md`
  - `docs/engineering-log.md`
- Problem / goal:
  - Add explicit backend development/test dependencies so local verification does not require manual package discovery.
- Root cause:
  - Phase 2 added FastAPI `TestClient` tests, but `pytest` and `httpx` were not declared in the repository.
- Change made:
  - Added `backend/requirements-dev.txt` with `pytest` and `httpx`.
  - Documented backend setup and test commands in `README.md`.
  - Did not modify runtime requirements or product logic.
- Tests/checks run:
  - Verified dependency files by GitHub file readback.
- Result:
  - Backend test dependencies are declared separately from runtime dependencies.
- Remaining risks / follow-up:
  - Run the documented verification command locally.

## 2026-05-23 - Phase 3 Decision Engine Recovery

- Type: Feature / Test / Docs
- Files changed:
  - `backend/app/models.py`
  - `backend/app/services/decision_engine.py`
  - `backend/app/api/classify.py`
  - `backend/app/main.py`
  - `backend/tests/test_decision_engine.py`
  - `docs/engineering-log.md`
- Problem / goal:
  - Recover and complete the backend-only Phase 3 decision engine after a stalled connector run.
  - Classify already-normalized job records with a selected rule profile and return an explainable result.
  - Avoid parser, capture, frontend dashboard, XLSX/export, history, and profile editing work.
- Root cause:
  - The previous run partially landed models, the decision service, and classify API file, but it did not mount the classify router, add tests, or write the Phase 3 log entry before interruption.
- Change made:
  - Confirmed normalized job, decision result, and classify request models are present.
  - Confirmed pure decision engine service is present.
  - Confirmed `POST /api/classify/job` route is present.
  - Mounted the classify router in `backend/app/main.py`.
  - Added backend tests for mandatory-language hard discard, remote distance exemption, hybrid Madrid discard, duplicate detection, missing info, low parser confidence, risk discard, and positive keywords not overriding hard discard.
  - Documented the chosen already-reviewed behavior in code: already-reviewed jobs currently return `Duplicate` so they do not re-enter Apply/Maybe queues.
- Tests/checks run:
  - Read SDD files and verified changed files by GitHub file readback.
  - Local tests were not run in the connector-only environment.
- Result:
  - Backend Phase 3 decision engine state was completed.
- Remaining risks / follow-up:
  - Run `cd backend && python -m pytest` locally.

## 2026-05-23 - Phase 4 Backend Parser and Parser Confidence

- Type: Feature / Test / Docs
- Files changed:
  - `backend/app/models.py`
  - `backend/app/services/parser.py`
  - `backend/app/api/parse.py`
  - `backend/app/main.py`
  - `backend/tests/test_parser.py`
  - `docs/engineering-log.md`
- Problem / goal:
  - Add a backend parser service that converts raw job-offer text into the existing `NormalizedJob` shape expected by the Phase 3 decision engine.
  - Keep parsing rule-based, conservative, and backend-only.
- Root cause:
  - Phase 3 intentionally accepted already-normalized jobs only, leaving the raw text to normalized job boundary unimplemented.
- Change made:
  - Added a parser service that extracts labeled title/company/location, work mode, language signals, mandatory language signals, employment type, shift/on-call indicators, technical signal keywords, risk keywords, parser notes, and parser confidence.
  - Added conservative missing/unclear-field notes instead of aggressive guessing.
  - Added `POST /api/parse/job` and `POST /api/parse-and-classify/job`.
  - Added parser request/result models for the new API shape.
  - Added backend parser tests for work mode detection, mandatory versus optional language handling, shift/on-call risk detection, low confidence, parser notes, parse API output, and parse-to-decision compatibility.
- Tests/checks run:
  - Read SDD files and verified changed files by GitHub file readback.
  - Local tests were not run in the connector-only environment.
- Result:
  - Backend Phase 4 parser boundary was implemented and test-covered.
- Remaining risks / follow-up:
  - Run `cd backend && python -m pytest` locally.
  - Future parser phases should add structured parser confidence scores, richer extraction, and legacy parser wrapping once capture/reference files are available.

## 2026-05-23 - Phase 5 Backend Capture Boundary and Runner Scaffold

- Type: Feature / Test / Docs
- Files changed:
  - `backend/app/models.py`
  - `backend/app/services/capture_runner.py`
  - `backend/app/api/capture.py`
  - `backend/app/main.py`
  - `backend/tests/test_capture_runner.py`
  - `docs/engineering-log.md`
- Problem / goal:
  - Add a safe backend capture boundary that represents capture runs without implementing browser automation or LinkedIn scraping.
  - Support the future flow `capture run -> raw captured jobs -> parse -> classify -> run summary` using manually supplied `raw_jobs` for now.
- Root cause:
  - Earlier phases implemented parser and decision engine boundaries, but no backend capture-run shape existed yet.
- Change made:
  - Added capture request/result/health models, including `CaptureRunRequest`, `CapturedRawJob`, `CaptureRunResult`, `CaptureHealthStatus`, and per-job capture results.
  - Added `backend/app/services/capture_runner.py` to validate manual raw jobs, apply `max_results`, parse each raw job, classify each parsed job, collect per-job errors, and return an in-memory run summary.
  - Added capture health that reports `capture_mode: manual_raw_jobs` and `browser_automation_enabled: false` with explicit warnings that real browser automation is not implemented.
  - Added `POST /api/capture/run` and `GET /api/capture/health`.
  - Mounted the capture router in FastAPI.
  - Added backend tests for capture health, empty runs, successful raw job parse/classify, mandatory German discard, mixed-run error isolation, max-results limiting/warnings, and no persistence/history file creation.
- Tests/checks run:
  - Read `AGENTS.md`.
  - Read `specs/product-spec.md`.
  - Read `specs/technical-plan.md`.
  - Read `specs/tasks.md`.
  - Reviewed `docs/engineering-log.md`.
  - Verified changed files by GitHub file readback where available.
  - Local tests were not run in this connector-only environment.
- Result:
  - Backend Phase 5 capture boundary is implemented without browser automation, scraping, persistence, export, frontend dashboard, history/tracker persistence, or profile editing.
- Remaining risks / follow-up:
  - Run `cd backend && python -m pytest` locally to verify the full backend test suite.
  - Future capture phases should wrap real browser-assisted capture behind this boundary only after legacy capture behavior is available and isolated.

## 2026-05-23 - Phase 6A Frontend Capture Review Dashboard

- Type: Feature / Docs
- Files changed:
  - `frontend/src/api.ts`
  - `frontend/src/App.tsx`
  - `frontend/src/styles.css`
  - `docs/engineering-log.md`
- Problem / goal:
  - Make the React frontend visibly useful by letting the Capture page run a simulated capture batch with manually staged raw job text entries.
  - Display the returned backend parse/classify decisions as a review dashboard before later persistence/export work.
- Root cause:
  - Phase 5 exposed the backend capture boundary, but the frontend still showed only a capture placeholder and did not consume `GET /api/capture/health` or `POST /api/capture/run`.
- Change made:
  - Added typed frontend API models and helpers for capture health and capture review runs.
  - Updated the Capture page to load profiles, default to `rafael_default` when available, show capture health, stage multiple raw job entries, load demo jobs, and submit a dry-run manual capture request.
  - Added frontend-only result filters for All, Apply, Maybe, Discard, Manual Review, Duplicate, and Errors.
  - Added run summary metrics and explainable decision cards showing parsed fields, decision, priority, score, reasons, warnings, missing information, parser confidence, matched keywords, source URL, and per-job errors.
  - Left browser automation, scraping, XLSX/export, persistent history/tracker, profile editing, and backend product logic untouched.
- Tests/checks run:
  - Read `AGENTS.md`.
  - Read `specs/product-spec.md`.
  - Read `specs/technical-plan.md`.
  - Read `specs/tasks.md`.
  - Reviewed `docs/engineering-log.md`.
  - Read existing frontend API/app/style files and backend capture model/API shape.
  - Updated files through the GitHub connector.
  - Local `npm run build` was not run in this connector-only environment.
- Result:
  - Phase 6A frontend dashboard is implemented against the existing backend capture boundary.
- Remaining risks / follow-up:
  - Run `cd frontend && npm install && npm run build` locally.
  - Run the backend locally before trying the dashboard so `/api/profiles`, `/api/capture/health`, and `/api/capture/run` are available.
  - Future phases should add persistent review queues, status updates, history/tracker storage, and export only after this local demo dashboard is verified.

## 2026-05-23 - Phase 6A.1 Frontend TypeScript Build Configuration

- Type: Cleanup / Docs
- Files changed:
  - `frontend/tsconfig.json`
  - `docs/engineering-log.md`
- Problem / goal:
  - Fix local `npm run build` failure caused by TypeScript reporting deprecated `moduleResolution=node10` behavior from the existing `"moduleResolution": "Node"` setting.
- Root cause:
  - The frontend Vite app was using the older Node module resolution setting while depending on `typescript@latest`, which now warns/errors for the deprecated Node10-style resolution.
- Change made:
  - Updated `frontend/tsconfig.json` from `"moduleResolution": "Node"` to `"moduleResolution": "Bundler"`, which matches modern Vite/ESM TypeScript projects.
  - Did not add `ignoreDeprecations`, change frontend product behavior, or modify backend logic.
- Tests/checks run:
  - Inspected `frontend/tsconfig.json`, `frontend/package.json`, and `frontend/vite.config.ts`.
  - Searched for related tsconfig references through the GitHub connector.
  - Reasoned that `"moduleResolution": "Bundler"` is compatible with `"module": "ESNext"`, Vite, and the existing ESM frontend package.
  - Local verification command to run: `cd frontend && npm run build`.
  - Local build was not run in this connector-only environment.
- Result:
  - TypeScript configuration now uses the modern Vite-compatible module resolution setting.
- Remaining risks / follow-up:
  - Run `cd frontend && npm run build` locally to confirm the build is clean in the installed dependency environment.

## 2026-05-23 - Phase 6A.2 React TypeScript Declaration Dependencies

- Type: Cleanup / Docs
- Files changed:
  - `frontend/package.json`
  - `docs/engineering-log.md`
- Problem / goal:
  - Fix local `npm run build` failures where TypeScript could not find declaration files for `react`, `react-dom/client`, or `react/jsx-runtime`, causing JSX elements to be typed as `any`.
- Root cause:
  - The React frontend depends on `react` and `react-dom`, but the project did not declare `@types/react` or `@types/react-dom`. With `strict` TypeScript and `jsx: react-jsx`, those missing declarations break JSX type checking.
- Change made:
  - Added `@types/react` and `@types/react-dom` as frontend development dependencies.
  - Kept `moduleResolution: Bundler` from Phase 6A.1.
  - Did not change backend logic, product behavior, or the Phase 6A capture review dashboard.
  - `frontend/package-lock.json` is not currently tracked on `main`; a temporary lockfile was generated locally to inspect dependency resolution, but no existing tracked lockfile could be updated through the repository.
- Tests/checks run:
  - Inspected `frontend/package.json`, `frontend/tsconfig.json`, `frontend/src/main.tsx`, `frontend/src/App.tsx`, and `frontend/src/vite-env.d.ts`.
  - Confirmed `frontend/package-lock.json` is absent from `main` and is not ignored by `.gitignore`.
  - Generated a temporary package lock with `npm install --package-lock-only --ignore-scripts` from the updated package metadata.
  - Local full `npm run build` against the repository was not run in this connector-only environment.
- Result:
  - React JSX declaration packages are now declared for local install/build.
- Remaining risks / follow-up:
  - Run `cd frontend && npm install && npm run build` locally. If local `npm install` creates `frontend/package-lock.json`, commit it in the next small cleanup so dependency resolution is fully locked.

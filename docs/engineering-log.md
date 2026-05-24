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

## 2026-05-23 - Phase 6A.3 / 6A.4 Frontend Lockfile Hygiene

- Type: Cleanup / Docs
- Files changed:
  - `.gitignore`
  - `frontend/package-lock.json`
  - `docs/engineering-log.md`
- Problem / goal:
  - Finish frontend dependency lockfile hygiene after the React TypeScript declaration fix and local build verification.
- Root cause:
  - `npm install` expanded `frontend/package-lock.json` locally, while TypeScript incremental builds can produce `tsconfig.tsbuildinfo` cache files that should remain untracked.
- Change made:
  - Kept `frontend/package-lock.json` tracked for reproducible frontend installs.
  - Confirmed `.gitignore` includes `*.tsbuildinfo`, so TypeScript incremental build cache files remain local.
  - Confirmed no root-level `package-lock.json` is being added.
  - Did not change backend logic, frontend product behavior, or add new product features.
- Tests/checks run:
  - User locally verified `cd frontend`, `npm install`, and `npm run build`.
  - Confirmed `.gitignore` still ignores `*.tsbuildinfo`.
  - Confirmed the root of the repository does not contain a tracked `package-lock.json`.
- Result:
  - Frontend lockfile tracking and TypeScript build-cache hygiene now match the locally verified build.
- Remaining risks / follow-up:
  - Future frontend dependency changes should update both `frontend/package.json` and `frontend/package-lock.json`.

## 2026-05-23 - Phase 6B Capture Review Dashboard UX Polish

- Type: Feature / Cleanup / Docs
- Files changed:
  - `frontend/src/App.tsx`
  - `frontend/src/styles.css`
  - `docs/engineering-log.md`
- Problem / goal:
  - Improve the Capture page and review results so the verified parser/decision workflow reads as a portfolio-ready local job-offer decision assistant instead of a developer test screen.
- Root cause:
  - Phase 6A made the workflow functional, but the results area, filters, and decision cards had a flat visual hierarchy and exposed every detail at full length.
- Change made:
  - Added a safe demo workflow note that explains browser automation is intentionally disabled while the real backend parser and decision engine are used.
  - Added compact decision overview counts for Apply, Maybe, Discard, Manual Review, Duplicate, and Errors.
  - Added count-aware result filters.
  - Reworked decision cards with compact top facts, score/priority, parser confidence, and expandable detail sections for warnings, missing information, matched keywords, and raw staged preview.
  - Tightened Capture page spacing and card styling without changing backend calls, profile selection, capture health, demo loading, or Rule Profiles behavior.
- Tests/checks run:
  - Read `AGENTS.md`.
  - Read `specs/product-spec.md`.
  - Read `specs/technical-plan.md`.
  - Read `specs/tasks.md`.
  - Reviewed `docs/engineering-log.md`.
  - Ran `cd frontend && npm run build`.
- Result:
  - Frontend production build passed.
- Remaining risks / follow-up:
  - Browser automation, XLSX/export, persistent history/tracker, profile editing, and backend decision-rule changes remain intentionally out of scope.

## 2026-05-24 - Phase 7 Portfolio Documentation

- Type: Docs
- Files changed:
  - `README.md`
  - `docs/architecture.md`
  - `docs/demo-checklist.md`
  - `docs/engineering-log.md`
- Problem / goal:
  - Make the repository portfolio-ready for GitHub reviewers by documenting the current verified local demo flow accurately.
- Root cause:
  - The previous README was brief and did not describe the current React + FastAPI workflow, safe capture boundary, API surface, setup, demo path, limitations, or roadmap in enough detail for reviewers.
- Change made:
  - Rewrote `README.md` around the positioning: local job-offer decision assistant for fast, explainable job review.
  - Documented the implemented raw job text / simulated capture -> parser -> configurable profile -> decision engine -> review dashboard flow.
  - Added current features, architecture, API endpoints, Windows-friendly setup commands, demo workflow, limitations, roadmap, and repository hygiene notes.
  - Added `docs/architecture.md` with backend services, frontend views, current data flow, intentionally excluded features, and future extension points.
  - Added `docs/demo-checklist.md` with setup commands, demo click path, expected visible results, useful screenshots, and what not to claim as implemented.
  - Did not change backend logic, frontend behavior, browser automation, scraping, export, history, or profile editing.
- Tests/checks run:
  - Read `AGENTS.md`.
  - Read `specs/product-spec.md`.
  - Read `specs/technical-plan.md`.
  - Read `specs/tasks.md`.
  - Reviewed `docs/engineering-log.md`.
  - Inspected current backend and frontend structure.
  - Ran `cd frontend && npm run build`.
  - Ran `cd backend && python -m pytest`; global Python did not have `pytest` installed.
  - Ran `cd backend && .\.venv\Scripts\python.exe -m pytest`.
- Result:
  - Frontend production build passed.
  - Backend tests passed in the existing backend virtualenv: 35 passed, 1 pytest cache warning.
- Remaining risks / follow-up:
  - Add screenshots or a short demo video after the UI is run locally with the backend.

## 2026-05-24 - Phase 8 Capture Result Export Package

- Type: Feature / Test / Docs
- Files changed:
  - `backend/app/models.py`
  - `backend/app/main.py`
  - `backend/app/api/export.py`
  - `backend/app/services/export_package.py`
  - `backend/tests/test_export_package.py`
  - `backend/requirements.txt`
  - `frontend/src/api.ts`
  - `frontend/src/App.tsx`
  - `frontend/src/styles.css`
  - `README.md`
  - `docs/architecture.md`
  - `docs/demo-checklist.md`
  - `docs/engineering-log.md`
- Problem / goal:
  - Add a safe local export package feature for already-reviewed capture results without adding browser automation, scraping, persistent history, profile editing, authentication, or decision-rule changes.
- Root cause:
  - Phase 7 documented export package / XLSX as the next roadmap item, but the verified capture review dashboard had no way to persist review results as local files.
- Change made:
  - Added export request/response models for capture result exports.
  - Added `POST /api/export/capture-result`.
  - Added an export service that writes JSON, CSV, or XLSX files under ignored `backend/data/exports/`.
  - Added `openpyxl` as an explicit backend runtime dependency for XLSX generation.
  - Added raw-text privacy handling: raw job text and parsed descriptions are excluded by default and included only when explicitly requested.
  - Added frontend export controls for JSON, CSV, and XLSX after a successful capture review, plus display of generated local file paths and warnings.
  - Updated README, architecture notes, and demo checklist for the implemented export flow.
- Tests/checks run:
  - Installed updated backend runtime requirements into the existing backend virtualenv.
  - Ran `cd backend && .\.venv\Scripts\python.exe -m pytest`.
  - Ran `cd frontend && npm run build`.
- Result:
  - Backend tests passed: 43 passed, 1 pytest cache warning.
  - Frontend production build passed.
- Remaining risks / follow-up:
  - Export files are generated locally and paths are shown in the UI, but download streaming is intentionally not implemented yet.
  - The XLSX is a focused capture review sheet; richer multi-sheet application tracker/export package remains a future phase.

## 2026-05-24 - Phase 9 Local History and Application Tracker Persistence

- Type: Feature / Test / Docs
- Files changed:
  - `backend/app/models.py`
  - `backend/app/main.py`
  - `backend/app/api/history.py`
  - `backend/app/services/history_store.py`
  - `backend/tests/test_history_store.py`
  - `frontend/src/api.ts`
  - `frontend/src/App.tsx`
  - `frontend/src/styles.css`
  - `README.md`
  - `docs/architecture.md`
  - `docs/demo-checklist.md`
  - `docs/engineering-log.md`
- Problem / goal:
  - Add local history/tracker persistence so reviewed capture results can be saved and revisited across sessions.
  - Keep persistence local, ignored by Git, and portfolio-safe.
- Root cause:
  - Phase 8 could export reviewed results, but the app still had no local application-status tracker or duplicate-aware reviewed-job history.
- Change made:
  - Added history models for saved reviewed jobs, save summaries, and application status updates.
  - Added a JSONL-backed history store under ignored `backend/data/history/`.
  - Added duplicate detection by source URL, external ID, or normalized title/company/location fallback.
  - Added `POST /api/history/save-capture-result`, `GET /api/history/jobs`, `GET /api/history/jobs/{history_id}`, and `PATCH /api/history/jobs/{history_id}/status`.
  - Added frontend Capture controls to save a reviewed run to history manually.
  - Added a History / Tracker page with saved job filters and application status updates.
  - Updated README, architecture notes, and demo checklist for the implemented history flow.
- Tests/checks run:
  - Ran `cd backend && .\.venv\Scripts\python.exe -m pytest`.
  - Ran `cd frontend && npm run build`.
- Result:
  - Backend tests passed: 52 passed, 1 pytest cache warning.
  - Frontend production build passed.
- Remaining risks / follow-up:
  - History uses simple local JSONL storage, not a database.
  - Capture-time duplicate/already-reviewed labeling against history remains a future phase.

## 2026-05-24 - Phase 10 Portfolio Demo Finishing Pass

- Type: Feature / Cleanup / Test / Docs
- Files changed:
  - `backend/app/models.py`
  - `backend/app/main.py`
  - `backend/app/api/demo.py`
  - `backend/app/services/demo_cleanup.py`
  - `backend/tests/test_demo_cleanup.py`
  - `frontend/src/api.ts`
  - `frontend/src/App.tsx`
  - `frontend/src/styles.css`
  - `README.md`
  - `docs/architecture.md`
  - `docs/demo-checklist.md`
  - `docs/engineering-log.md`
- Problem / goal:
  - Improve portfolio/demo presentation and add a safe local cleanup path for generated demo exports/history.
  - Keep the phase focused on demo polish, safety, and usability without adding risky automation.
- Root cause:
  - The verified workflow was functional, but the About page was still a placeholder and generated demo data had to be cleaned manually.
- Change made:
  - Added `POST /api/demo/cleanup` for manual local cleanup of `backend/data/exports/` and `backend/data/history/` only.
  - Added path-fenced cleanup logic with deleted file/directory counts and warnings.
  - Added backend cleanup tests for allowed-folder deletion, missing folders, returned counts, and protection of files outside the allowed folders.
  - Reworked the About page to explain LinkAut, the safe workflow, implemented modules, intentionally disabled features, local/privacy-first behavior, portfolio purpose, and cleanup controls.
  - Added UI privacy notes for synthetic demo jobs, local exports, and local history.
  - Improved the History empty state wording.
  - Updated README, architecture docs, and demo checklist for demo safety and cleanup.
- Tests/checks run:
  - Ran `cd backend && .\.venv\Scripts\python.exe -m pytest`.
  - Ran `cd frontend && npm run build`.
- Result:
  - Backend tests passed: 56 passed, 1 pytest cache warning.
  - Frontend production build passed.
- Remaining risks / follow-up:
  - Cleanup intentionally covers only exports/history in this phase; broader privacy cleanup for logs, runs, captures, and preview mode remains future work.

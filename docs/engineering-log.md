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
  - Did not create React or FastAPI files.
  - Did not implement app features.
- Tests/checks run:
  - Read `AGENTS.md`.
  - Read `specs/product-spec.md`.
  - Read `specs/technical-plan.md`.
  - Read `specs/tasks.md`.
  - Read current `.gitignore`.
  - Read existing `docs/engineering-log.md`.
  - Checked representative target app paths and confirmed they are not present yet: `frontend/package.json`, `backend/main.py`, `backend/core/parser_service.py`, and `backend/config/default_profiles/rafael_default.json`.
- Result:
  - Phase 0 documentation is now aligned with the SDD.
  - Repository remains pre-implementation, as requested.
- Remaining risks / follow-up:
  - Existing legacy Streamlit/capture/parser/classifier scripts are not currently present in this repository, so P0.1/P0.3 cannot identify or preserve concrete legacy entry points yet.
  - If the legacy pipeline exists outside this repository, it should be imported under the SDD's `backend/capture/legacy/` and `backend/legacy/` areas before wrapper implementation starts.

### SDD Presence Confirmation

The SDD files are present on `main`:

- `AGENTS.md`
- `specs/product-spec.md`
- `specs/technical-plan.md`
- `specs/tasks.md`

The SDD confirms the intended product direction:

- Target app: local React frontend plus FastAPI backend.
- Primary workflow: `capture -> parse -> classify/sort -> review dashboard -> tracker/export`.
- Manual paste: fallback/debug/single-job workflow only.
- Legacy Streamlit pipeline: reference material to preserve/wrap first, not the target UI.
- Product positioning: local job-offer automation and decision-support assistant, not a mass-apply bot or scraper-first project.

### Current Repository Gaps Against SDD

The repository has the SDD and hygiene baseline, but not the application implementation yet.

Current tracked baseline:

- `README.md`
- `LICENSE`
- `.gitignore`
- `AGENTS.md`
- `specs/product-spec.md`
- `specs/technical-plan.md`
- `specs/tasks.md`
- `docs/engineering-log.md`

Missing or not yet confirmed:

- Legacy capture script(s), parser, classifier, exporter, history, and Streamlit reference files.
- Current run commands and dependency files for the legacy pipeline.
- `backend/` FastAPI wrapper skeleton.
- `frontend/` React app skeleton.
- `backend/config/default_profiles/*.json` default/demo profiles.
- `backend/config/user_profiles/.gitkeep` placeholder for private local profiles.
- Parser confidence implementation.
- Decision/rule engine modules.
- Dedupe/history/status tracker modules.
- Apply Today and Manual Review queue logic.
- XLSX/export package implementation.
- Capture health diagnostics and logs viewer.
- Demo mode and privacy cleanup tooling.
- Backend tests and frontend/manual verification checklist.
- `docs/demo-checklist.md` and `docs/privacy-checklist.md`.

### Proposed Target Structure

This follows the SDD's technical plan and keeps manual paste as a debug/fallback path rather than the main flow.

```text
linkaut-job-search-assistant/
  AGENTS.md
  README.md
  LICENSE
  .gitignore
  specs/
    product-spec.md
    technical-plan.md
    tasks.md
  docs/
    engineering-log.md
    demo-checklist.md
    privacy-checklist.md
  backend/
    main.py
    core/
      models.py
      parser_service.py
      decision_engine.py
      rule_engine.py
      profiles.py
      location.py
      dedupe.py
      history.py
      status_tracker.py
      apply_queue.py
      exporter.py
      xlsx_exporter.py
      diagnostics.py
      privacy_cleanup.py
      demo_mode.py
      engineering_log.py
    capture/
      runner.py
      legacy/
        capture_engine_v35_left_panel_guided.py
    legacy/
      classifier_legacy.py
      parser_legacy.py
      runner_legacy.py
    config/
      default_profiles/
        rafael_default.json
        generic_it_support.json
        remote_support_demo.json
        portfolio_safe_demo.json
      user_profiles/
        .gitkeep
    tests/
      test_decision_engine.py
      test_parser_confidence.py
      test_profiles.py
      test_dedupe.py
      test_status_tracker.py
      test_apply_queue.py
      test_xlsx_exporter.py
      test_privacy_cleanup.py
  frontend/
    package.json
    index.html
    vite.config.ts
    src/
      App.tsx
      api.ts
      pages/
        CapturePage.tsx
        ReviewDashboardPage.tsx
        ResultsPage.tsx
        ProfilesPage.tsx
        HistoryPage.tsx
        ApplyTodayPage.tsx
        ManualReviewPage.tsx
        ExportsPage.tsx
        ManualPasteDebugPage.tsx
        LogsDiagnosticsPage.tsx
        DemoModePage.tsx
        PrivacyCleanupPage.tsx
        AboutPage.tsx
      components/
        PipelineStatus.tsx
        CaptureHealthPanel.tsx
        ReviewSummaryCards.tsx
        DecisionBadge.tsx
        ApplicationStatusBadge.tsx
        JobDecisionCard.tsx
        TriggeredRulesList.tsx
        MissingInfoList.tsx
        ParserConfidenceBadge.tsx
        ProfileSelector.tsx
        ApplyTodayQueue.tsx
        ManualReviewQueue.tsx
        ExportPackagePanel.tsx
  samples/
  examples/
  demo_data/
  portfolio_demo/
  runs/
```

### Proposed `.gitignore` Changes Applied

The `.gitignore` update was applied with one SDD-driven adjustment: instead of treating all demo/sample outputs as uncommittable, it keeps broad protection for private/generated files while allowing explicitly named safe sample/demo directories.

Important protections now covered:

- Python caches, virtual environments, coverage, mypy, and ruff caches.
- Node/React dependencies and build outputs.
- `.env` files and local/private configuration.
- Private LinkAut generated folders such as captures, logs, outputs, debug outputs, exports, local data, and manual inputs.
- Real/private run packages via `runs/*` with explicit `runs/demo_*/` exceptions.
- Private user profiles under `backend/config/user_profiles/*` while allowing a `.gitkeep` placeholder.
- Real job-search exports and captures via `*.csv`, `*.xlsx`, `*.jsonl`, and `*.log`.
- Browser automation artifacts such as Playwright reports, browser profiles, snapshots, and screenshots.
- Editor/OS files.

Safe exceptions are allowed under:

- `samples/`
- `examples/`
- `demo_data/`
- `portfolio_demo/`
- `runs/demo_*/`

### Next Recommended Implementation Phase

Next phase should be P0 completion, not React/FastAPI implementation yet:

1. Locate or import the legacy Streamlit/capture/parser/classifier pipeline as reference material.
2. Identify current capture, parser, classifier, exporter, config, and history entry points.
3. Document current run commands and latest known output formats.
4. Confirm whether MVP state/history should remain CSV/JSON or move to SQLite.
5. Confirm which Rafael-specific profile details can be committed publicly versus kept private.
6. Only after those confirmations, start P1: create the FastAPI wrapper skeleton and React capture-first control panel.

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
  - Not applicable; this is new skeleton work.
- Change made:
  - Added a minimal FastAPI app with CORS configured for the local Vite dev server.
  - Added `GET /api/health`, returning backend status, service name, and a short running message.
  - Added a focused backend health test using FastAPI `TestClient`.
  - Added a Vite + React + TypeScript frontend skeleton.
  - Added basic app navigation for Capture, Review Dashboard, Rule Profiles, History / Tracker, Manual Paste / Debug, and About.
  - Set Capture as the default active page.
  - Added placeholder copy that marks unimplemented pipeline work honestly.
  - Added a frontend API helper and backend health badge.
  - Added minimal backend folder placeholders without importing legacy pipeline code.
- Tests/checks run:
  - Read `AGENTS.md`.
  - Read `specs/product-spec.md`.
  - Read `specs/technical-plan.md`.
  - Read `specs/tasks.md`.
  - Verified committed backend/frontend files by GitHub file readback.
  - Local runtime commands were not run because this Codex environment does not have a local clone of the GitHub repository available; updates were made through the GitHub connector.
- Result:
  - Backend skeleton exists under `backend/`.
  - Frontend skeleton exists under `frontend/`.
  - Frontend health indicator is wired to `GET /api/health`.
  - No real app workflow logic or legacy files were added.
- Remaining risks / follow-up:
  - Run `pip install -r backend/requirements.txt` and `uvicorn main:app --reload` from `backend/` in a local clone to verify backend startup.
  - Run `npm install` and `npm run build` from `frontend/` in a local clone to verify TypeScript/Vite build.
  - Add profile loading and capture wrapper endpoints only in the next approved phase.
  - Import or identify legacy pipeline files before wrapping real capture/parser/classifier behavior.

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
  - Avoid implementing product features beyond the structure repair.
- Root cause:
  - The initial Phase 1 backend placed the FastAPI app at `backend/main.py`, but the documented and desired package entrypoint is `backend/app/main.py`. Running `uvicorn app.main:app --reload` from `backend/` therefore failed with `ModuleNotFoundError: No module named 'app'`.
- Change made:
  - Moved the FastAPI application entrypoint into the `app` package at `backend/app/main.py`.
  - Added package initializers for `backend/app/` and `backend/app/api/`.
  - Moved the health endpoint into `backend/app/api/health.py` as an `APIRouter` mounted under `/api`.
  - Included the health router from `backend/app/main.py`.
  - Updated the health test to import `app` from `app.main`.
  - Removed the obsolete `backend/main.py` entrypoint.
  - Checked for `legacy/streamtlit_pipeline` and `legacy/streamlit_pipeline`; neither path exists on `main`, so no safe rename was performed.
- Tests/checks run:
  - Verified `backend/app/main.py` by GitHub file readback.
  - Verified `backend/app/api/health.py` by GitHub file readback.
  - Verified `backend/tests/test_health.py` imports `from app.main import app` by GitHub file readback.
  - Verified `backend/main.py` is no longer present by GitHub file readback returning 404.
  - Verification command to run in a local clone: `cd backend && uvicorn app.main:app --reload`.
  - Endpoint verification to run locally: open `http://127.0.0.1:8000/api/health` and confirm it returns the existing JSON response.
- Result:
  - Repository structure now matches the documented `uvicorn app.main:app --reload` import path.
  - `GET /api/health` response body remains unchanged.
  - No profiles, capture, parser, classifier, export, history, XLSX, frontend, or legacy pipeline features were added.
- Remaining risks / follow-up:
  - Local runtime verification still needs to be run in an actual local clone with dependencies installed, because this Codex environment is updating the GitHub repo through the connector and cannot execute the repository in place.
  - If a misspelled `legacy/streamtlit_pipeline` directory exists only in another branch or local working copy, rename it to `legacy/streamlit_pipeline` there before importing legacy code.

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
  - Not applicable; this is Phase 2 read/display functionality.
- Change made:
  - Added `RuleProfile` and `RuleProfileSummary` backend models.
  - Added default profile storage at `backend/app/config/default_profiles.json`.
  - Added default profiles: `rafael_default`, `generic_remote_it_support`, `saas_support`, and `infrastructure_support`.
  - Added a small profile loading service for default profile JSON.
  - Added read-only endpoints: `GET /api/profiles` and `GET /api/profiles/{profile_id}`.
  - Added backend tests for list loading, `rafael_default` presence, required detail fields, and controlled 404 for unknown profiles.
  - Extended frontend API helpers with profile summary/detail fetches.
  - Updated the Rule Profiles page to fetch profiles, select one in local React state, display full details, and mark Rafael Default as a demo/default preset rather than a global rule set.
- Tests/checks run:
  - Read `AGENTS.md`.
  - Read `specs/product-spec.md`.
  - Read `specs/technical-plan.md`.
  - Read `specs/tasks.md`.
  - Reviewed `docs/engineering-log.md`.
  - Verified backend changed files and profile tests by GitHub file readback.
  - Frontend file readback through the GitHub connector timed out after writes, so local frontend verification remains required.
  - Local commands were not run in this connector-only environment.
- Result:
  - Rule profiles are available as backend configuration data.
  - Read-only profile API endpoints are wired into FastAPI.
  - The React Rule Profiles view can fetch, select, and display profile details.
  - No real classification or profile editing was added.
- Remaining risks / follow-up:
  - Run `cd backend && pytest` locally to verify health and profile tests.
  - Run `cd frontend && npm run build` locally to verify the TypeScript/Vite build.
  - In a later phase, connect selected profile state to capture/classification run summaries.
  - In a later phase, add profile validation/editing only after read-only profile display is stable.

## 2026-05-23 - Phase 2.1 Backend Development Dependency Cleanup

- Type: Cleanup / Docs
- Files changed:
  - `backend/requirements-dev.txt`
  - `README.md`
  - `docs/engineering-log.md`
- Problem / goal:
  - Add explicit backend development/test dependencies so local verification does not require manual package discovery.
- Root cause:
  - Phase 2 added FastAPI `TestClient` tests, but `pytest` and `httpx` were not declared in the repository. Local verification therefore required manually installing them.
- Change made:
  - Added `backend/requirements-dev.txt` with only test/development dependencies needed for the current tests: `pytest` and `httpx`.
  - Documented backend setup and test commands in `README.md`.
  - Did not modify runtime requirements or product logic.
- Tests/checks run:
  - Verified `backend/requirements.txt` remains runtime-focused.
  - Verified `backend/requirements-dev.txt` was absent before this cleanup.
  - Verification command for local checkout: `cd backend && python -m pip install -r requirements.txt && python -m pip install -r requirements-dev.txt && python -m pytest`.
- Result:
  - Backend test dependencies are now declared separately from runtime dependencies.
  - Local backend setup commands are documented.
- Remaining risks / follow-up:
  - Run the verification command in a local checkout to confirm dependency installation and tests pass in the user's Python environment.

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
  - Read `AGENTS.md`.
  - Read `specs/product-spec.md`.
  - Read `specs/technical-plan.md`.
  - Read `specs/tasks.md`.
  - Reviewed `docs/engineering-log.md`.
  - Verified changed files by GitHub file readback.
  - Local tests were not run in this connector-only environment.
- Result:
  - Backend Phase 3 decision engine state is complete in the repository.
  - No parser, capture, frontend dashboard, XLSX/export, history, or profile editing was implemented.
- Remaining risks / follow-up:
  - Run `cd backend && python -m pytest` locally to verify the full backend test suite.
  - Future phases should refine location parsing/distance handling once a real parser and normalized location service exist.

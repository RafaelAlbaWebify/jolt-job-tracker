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

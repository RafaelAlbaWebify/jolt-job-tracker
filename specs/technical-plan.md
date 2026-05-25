# Technical Plan: JOLT / React Local Job Opportunity Tracker

## 1. Architecture Goal

Create a local React + Python backend application that preserves useful, safe text-level lessons from the existing capture/parser/classifier pipeline while replacing the Streamlit GUI and improving modularity. Risky browser automation remains disabled/experimental until explicitly designed and reviewed.

Primary flow:

```text
React UI
→ FastAPI backend
→ capture runner
→ parser service
→ decision engine with active rule profile
→ dedupe/history/status service
→ review dashboard
→ XLSX/export package service
```

Manual paste uses the same backend services as a fallback/debug flow.

---

## 2. Target Repository Structure

```text
JOLT/
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
        generic_remote_it_support.json
        saas_support.json
        infrastructure_support.json
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

  docs/
    engineering-log.md
    demo-checklist.md
    privacy-checklist.md
  samples/
  demo_data/
  specs/
  AGENTS.md
  README.md
  .gitignore
```

Codex must inspect the actual repository before moving files.

---

## 3. Migration Strategy

### Phase 1: Protect current pipeline

- Confirm current capture, parser, classifier, outputs, and configs.
- Add strict `.gitignore`.
- Add `docs/engineering-log.md`.
- Create a baseline run summary from the current working behavior.

### Phase 2: FastAPI wrapper around legacy pipeline

- Keep existing capture engine.
- Keep existing parser script.
- Keep existing classifier behavior.
- Add backend endpoints that run current scripts and return summaries.
- Do not refactor core logic until the wrapper works.

### Phase 3: React control panel

- Capture page as main page.
- Review dashboard before export.
- Decision cards/table.
- Apply Today queue.
- Manual Review queue.
- Export package download.
- Logs/diagnostics page.

### Phase 4: Extract services

Split legacy classifier and pipeline behavior into backend services:

- parser service;
- decision/rule engine;
- profile service;
- dedupe/history;
- status tracker;
- XLSX/export package;
- diagnostics;
- privacy cleanup;
- demo mode.

### Phase 5: Portfolio hardening

- Add portfolio-safe demo data.
- Add anonymized sample export package.
- Add README and demo checklist.
- Add tests around rules, dedupe, parser confidence, and XLSX export.

---

## 4. Backend API Plan

Suggested FastAPI endpoints:

```text
GET  /api/health

GET  /api/profiles
GET  /api/profiles/{profile_id}
POST /api/profiles
PUT  /api/profiles/{profile_id}
POST /api/profiles/{profile_id}/reset
POST /api/profiles/{profile_id}/validate

POST /api/capture/start
GET  /api/capture/status/{run_id}
GET  /api/capture/latest
GET  /api/capture/health/{run_id}

POST /api/pipeline/run-latest
POST /api/parser/run-latest-capture
POST /api/classifier/run
POST /api/manual/analyze

GET  /api/results/latest
GET  /api/results/{run_id}
GET  /api/review/{run_id}/summary
GET  /api/review/{run_id}/apply-today
GET  /api/review/{run_id}/manual-review
GET  /api/review/{run_id}/duplicates
GET  /api/review/{run_id}/discarded

GET  /api/history
GET  /api/history/{job_key}
POST /api/history/mark-actioned
POST /api/history/update-status

GET  /api/exports/latest
POST /api/exports/{run_id}/xlsx
POST /api/exports/{run_id}/package
GET  /api/exports/download/{file_id}

GET  /api/logs/latest
GET  /api/logs/engineering
POST /api/logs/engineering

GET  /api/demo/status
POST /api/demo/enable
POST /api/demo/disable
POST /api/demo/load-sample-run

GET  /api/privacy/cleanup/preview
POST /api/privacy/cleanup/run
```

Needs confirmation:

- Whether capture runs synchronously or as background subprocess with polling.
- Whether MVP run state uses JSON files or SQLite.
- Whether XLSX export uses `openpyxl` only or also `pandas`.

---

## 5. Core Data Models

### ParsedJob

```json
{
  "job_id": "",
  "source_url": "",
  "title": "",
  "company": "",
  "location": "",
  "work_mode": "remote | hybrid | onsite | unknown",
  "distance_km": null,
  "employment_type": "",
  "contract_type": "",
  "salary": "",
  "languages_detected": [],
  "mandatory_languages": [],
  "optional_languages": [],
  "shift_signals": [],
  "on_call_signals": [],
  "risk_signals": [],
  "positive_signals": [],
  "role_family_signals": [],
  "parser_notes": [],
  "parser_confidence": "high | medium | low",
  "parser_confidence_score": 0,
  "raw_text": ""
}
```

### DecisionResult

```json
{
  "decision": "Apply | Maybe | Manual Review | Discard | Duplicate | Already Reviewed",
  "score": 0,
  "priority": "High | Medium | Low",
  "application_status": "New",
  "reasons": [],
  "triggered_rules": [],
  "warnings": [],
  "missing_information": [],
  "hard_discard_reasons": [],
  "recommended_next_action": "",
  "parser_confidence": "",
  "duplicate_status": "",
  "history_status": "",
  "extracted_fields": {}
}
```

### RuleProfile

Must include language, location, work mode, role fit, risk severity, parser-confidence, dedupe, export, and status defaults.

### PipelineRun

Tracks run ID, timestamps, active profile, input/output files, counts, diagnostics, and export package paths.

---

## 6. Module Responsibilities

### `profiles.py`

- Load default profiles.
- Load user profiles.
- Validate profile schema.
- Save/edit/reset profiles.
- Keep private profiles out of Git.

### `parser_service.py`

- Normalize legacy parser outputs into `ParsedJob`.
- Parse manual text into `ParsedJob`.
- Calculate parser confidence.
- Preserve parser notes.
- Never make final Apply/Maybe/Discard decisions.

### `decision_engine.py` / `rule_engine.py`

- Apply selected profile.
- Run hard discards before positive scoring.
- Generate triggered rule IDs.
- Use human-readable labels.
- Route uncertain jobs to Manual Review.

### `dedupe.py`

- Detect duplicates using job ID, URL, normalized title/company/location, and history.
- Label duplicates/already-reviewed jobs without silently deleting them.
- Preserve visible `Duplicate` / `Already Reviewed` history entries when repeated jobs are saved.

### `history.py` / `status_tracker.py`

- Save seen jobs.
- Save application statuses.
- Support active statuses: `New`, `Apply Today`, `Manual Review`, `Waiting`, `Follow Up`, `Applied`, `Rejected`, `Archived`, `Duplicate`, and `Already Reviewed`.
- Continue accepting older local statuses such as `Not started`, `Interview`, `Watchlist`, and `Discarded`.
- Support updating statuses from UI.
- Preserve profile and run ID for auditability.

### `apply_queue.py`

- Build Apply Today queue.
- Exclude duplicates/already-applied jobs.
- Rank by decision, score, confidence, recency, and warnings.

### `xlsx_exporter.py`

- Generate multi-sheet XLSX tracker.
- Include Summary, All Reviewed Jobs, Apply Today, Manual Review, Waiting / Follow Up, Duplicates / Already Reviewed, Decision Explanations, and Capture Diagnostics.
- Add filters, frozen headers, adjusted widths, clickable URLs, and status columns.

### `exporter.py`

- Generate CSV, JSON, Markdown report, and complete run package.

### `diagnostics.py`

- Capture pipeline health metrics.
- Summarize logs.
- Surface likely failure causes.

### `demo_mode.py`

- Load sample jobs and portfolio-safe profile.
- Prevent accidental use of real private data in demos.

### `privacy_cleanup.py`

- Preview and run cleanup of generated/private data.
- Preserve source, specs, demo data, and anonymized samples.

### `engineering_log.py`

- Append entries to `docs/engineering-log.md`.
- Standardize task logs for bug fixes, optimizations, and feature work.

---

## 7. React Pages

### Capture Page

Main workflow page:

- profile selector;
- capture source/type;
- start capture;
- run parser/classifier;
- pipeline progress;
- capture health panel;
- latest run summary.

### Review Dashboard Page

Shown before export:

- summary cards;
- Apply Today queue preview;
- Manual Review queue preview;
- duplicates/already-reviewed counts;
- export readiness.

### Results Page

- grouped results;
- explainable decision cards;
- table/list toggle;
- filters by decision, status, confidence, duplicate status.

### Apply Today Page

- top actionable jobs;
- status update controls;
- source links;
- export selected jobs.

### Manual Review Page

- unclear/low-confidence jobs;
- reasons for review;
- manual status overrides.

### Profiles Page

- view/edit profiles;
- clone default profile;
- reset profile;
- validate profile.

### History Page

- saved jobs;
- application status tracker;
- duplicates/already-reviewed state;
- filters.

### Exports Page

- generate XLSX;
- generate run package;
- download latest files;
- show rule snapshot used.

### Logs / Diagnostics Page

- capture logs;
- backend errors;
- pipeline summaries;
- engineering log viewer.

### Demo Mode Page

- enable/disable demo mode;
- load sample run;
- generate demo XLSX.

### Privacy Cleanup Page

- preview generated/private files;
- run cleanup;
- show protected files.

---

## 8. XLSX Export Technical Requirements

Use `openpyxl` for XLSX creation unless a stronger reason exists.

Required workbook sheets:

- `Summary`
- `All Reviewed Jobs`
- `Apply Today`
- `Manual Review`
- `Waiting Follow Up`
- `Duplicates Reviewed`
- `Decision Explanations`
- `Capture Diagnostics`

Workbook requirements:

- frozen header row;
- filters enabled;
- sensible column widths;
- clickable source URLs;
- serialized lists as readable strings;
- application status column;
- run ID and profile ID included;
- no private raw job text in Shortlist unless explicitly configured.

---

## 9. Engineering Log Format

Create and maintain:

```text
docs/engineering-log.md
```

Entry template:

```markdown
## YYYY-MM-DD HH:MM — <Task ID / Change Title>

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

Codex should update this log during implementation, especially when repairing bugs or improving efficiency.

---

## 10. Testing Strategy

Required backend tests:

- profile loading/validation;
- mandatory language hard discard;
- remote location distance exemption;
- hybrid/onsite distance discard;
- risk severity behavior;
- parser confidence calculation;
- low confidence => Manual Review;
- hard discard overrides positive matches;
- dedupe by URL/job ID/title/company;
- already-reviewed status;
- Apply Today queue ranking;
- XLSX sheets and headers;
- export package creation;
- privacy cleanup preview preserves protected files.

Required frontend/manual checks:

- Capture page starts pipeline or shows controlled failure.
- Review dashboard shows counts.
- Decision cards show reasons/rules/warnings/missing info.
- Status update persists.
- XLSX export downloads.
- Demo mode uses fake data only.
- Cleanup preview does not include source/spec files.

---

## 11. Repository Hygiene

Ignore generated/private files:

```text
.venv/
__pycache__/
logs/
outputs/
debug_outputs/
captures_id/
manual_inputs/
exports/
runs/real_*/
*.csv
*.jsonl
*.log
*.xlsx
.env
local_config.json
personal_rules.json
backend/config/user_profiles/
outputs/state/job_history_master.csv
```

Allow only anonymized examples under:

```text
samples/
demo_data/
portfolio_demo/
```


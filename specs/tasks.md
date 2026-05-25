# Tasks: JOLT / Portfolio-Ready React Local Server Version

## Priority Groups

- P0: Protect and document current working pipeline.
- P1: React + FastAPI wrapper MVP.
- P2: Configurable rule profiles.
- P3: Review dashboard, decision cards, queues, and statuses.
- P4: History, dedupe, parser confidence, diagnostics.
- P5: XLSX/export package and privacy/demo tooling.
- P6: Refactor legacy logic into testable services.
- P7: Portfolio hardening and documentation.

---

## P0 — Current Pipeline Protection

### P0.1 Inspect and document current repository

Objective: Confirm current files, entry points, outputs, dependencies, and private/generated data before migration.

Acceptance criteria:

- Capture script identified.
- Parser script identified.
- Classifier/export/history code identified.
- Config files identified.
- Current run commands documented.
- Private/generated folders listed.
- Unknowns marked as “Needs confirmation”.

---

### P0.2 Add strict `.gitignore`

Objective: Prevent private/generated data from entering GitHub.

Acceptance criteria: `.gitignore` excludes:

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

---

### P0.3 Preserve current capture-parser-classifier behavior

Objective: Establish current behavior as a baseline before React migration.

Acceptance criteria:

- Current capture can still run.
- Current parser can still run.
- Current classifier can still generate exports.
- Latest known successful output format documented.
- No legacy behavior is removed before replacement exists.

---

### P0.4 Create engineering log

Objective: Require Codex to log implementation, repair, and optimization work.

Files:

```text
docs/engineering-log.md
```

Acceptance criteria:

- File exists.
- Contains entry template.
- First entry documents repository inspection and baseline decision.
- Future bug fixes, optimizations, refactors, and features append entries.

---

## P1 — React + FastAPI Wrapper MVP

### P1.1 Create FastAPI backend skeleton

Acceptance criteria:

- Backend starts locally.
- `/api/health` returns OK.
- Backend has folders for core, capture, legacy, config, tests.
- Engineering log updated.

---

### P1.2 Create React frontend skeleton

Acceptance criteria:

- React app starts locally.
- Capture page is the first/main page.
- Navigation includes Review Dashboard, Results, Profiles, History, Apply Today, Manual Review, Exports, Logs/Diagnostics, Demo Mode, Privacy Cleanup, Manual Paste / Debug, About.

---

### P1.3 Add backend capture runner endpoint

Objective: Run existing capture script through backend without rewriting it.

Acceptance criteria:

- `POST /api/capture/start` starts capture or returns controlled error.
- Capture run gets a run ID.
- Exit code, stdout/stderr summary, and log path are captured.
- Failure does not crash backend.
- Capture health object is created.

---

### P1.4 Add parser/classifier runner endpoint

Objective: Run existing parse/classify pipeline from backend.

Acceptance criteria:

- Endpoint can process latest capture.
- Endpoint returns parsed/classified files.
- Endpoint reports row counts, decision counts, duplicate counts, and parser errors.
- Active profile ID is recorded.

---

### P1.5 Add React pipeline controls

Acceptance criteria:

- User can start capture.
- User can run parse/classify.
- UI shows status, latest run, counts, active profile, errors.
- Long logs are collapsed/expandable.
- User can navigate to Review Dashboard after successful run.

---

## P2 — Configurable Rule Profiles

### P2.1 Define rule profile schema

Objective: Formalize configurable filters for reusable portfolio use.

Acceptance criteria:

Schema includes:

- language rules;
- location/distance rules;
- work mode rules;
- schedule/on-call/shift severities;
- role fit rules;
- positive/risk/discard keywords;
- stretch skills;
- parser confidence thresholds;
- duplicate/already-reviewed behavior;
- default statuses;
- export options.

---

### P2.2 Create default profiles

Create:

```text
backend/app/config/default_profiles.json
```

Current profile IDs:

- `rafael_default`
- `generic_remote_it_support`
- `saas_support`
- `infrastructure_support`

Acceptance criteria:

- Rafael default uses Vigo, 30 km, English/Spanish, remote preference.
- Generic/demo profiles do not expose private Rafael-only data.
- Profiles validate against schema.

---

### P2.3 Add backend profile service

Acceptance criteria:

- List profiles.
- Load profile.
- Validate profile.
- Save user profile.
- Clone default profile.
- Reset user profile to default.
- User profiles are ignored by Git.

---

### P2.4 Add React profile selector

Acceptance criteria:

- User can select active profile before capture/classification.
- Active profile is visible on Capture, Review Dashboard, Results, and Exports pages.
- Active profile is stored in run summary.

---

### P2.5 Add Rules & Profiles editor

Acceptance criteria:

User can edit or configure:

- accepted mandatory languages;
- mandatory/optional language severity;
- base location;
- max distance;
- remote ignores distance;
- accepted/preferred work modes;
- risk severities;
- positive keywords;
- discard keywords;
- stretch skills;
- parser confidence thresholds.

Needs confirmation:

- MVP editor can be form-based or JSON-editor based.

---

### P2.6 Connect classifier to selected profile

Acceptance criteria:

- Changing accepted languages changes language decisions.
- Changing base/max distance changes location decisions.
- Changing risk severity changes Maybe/Discard behavior.
- Selected profile appears in Rules Snapshot export.

---

## P3 — Review Dashboard, Decision Cards, Queues, and Statuses

### P3.1 Normalize classification labels

Objective: Replace user-facing A/B/C/D with clear labels.

Acceptance criteria:

- UI uses Apply / Maybe / Manual Review / Discard / Duplicate / Already Reviewed.
- Exports include human-readable labels.
- Legacy labels only remain internally if needed.

---

### P3.2 Build review dashboard before export

Acceptance criteria:

Dashboard shows summary cards for:

```text
Captured
Parsed
Apply
Maybe
Manual Review
Discard
Duplicates
Already Reviewed
Low Parser Confidence
Export Ready
```

Dashboard links to Apply Today, Manual Review, Duplicates, and Discarded views.

---

### P3.3 Build explainable decision cards

Acceptance criteria:

Each card/row shows:

- decision label;
- application status;
- score/priority;
- title/company/location/work mode;
- parser confidence;
- reasons;
- triggered rules;
- warnings;
- missing information;
- duplicate/already-reviewed status;
- recommended next action;
- source URL.

---

### P3.4 Add application status tracker inside app

Acceptance criteria:

Statuses supported:

```text
New
Apply Today
Manual Review
Waiting
Follow Up
Applied
Rejected
Archived
Duplicate
Already Reviewed
```

User can update status from the History / Tracker queue view. The update persists immediately through the history API and survives refresh. Legacy local statuses such as `Not started`, `Interview`, `Watchlist`, and `Discarded` remain accepted for backward compatibility but are mapped into current workflow statuses for normal display/export.

Status persists locally and exports to tracker/history XLSX.

---

### P3.5 Build Apply Today queue

Acceptance criteria:

- Shows top 5–10 actionable jobs by default.
- Excludes duplicates, already-applied, already-reviewed, hard-warning jobs.
- Prioritizes Apply + high score + good parser confidence + recent run.
- User can mark job as Applied/Waiting/Archived/Discarded.

---

### P3.6 Build Manual Review queue

Acceptance criteria:

Manual Review queue includes jobs with:

- low parser confidence;
- unclear work mode;
- unclear location;
- unclear language requirement;
- unclear on-call/shift;
- parser mismatch;
- suspicious parsed fields;
- stretch/defensibility concerns.

Each item explains why manual review is needed.

---

## P4 — History, Dedupe, Parser Confidence, Diagnostics

### P4.1 Implement duplicate and already-reviewed detection

Acceptance criteria:

Deduplication checks:

- job ID;
- source URL;
- normalized company + title;
- normalized company + title + location;
- history action status.

Duplicates are labeled and counted in capture/review, not silently hidden. Saving a repeated job should skip adding another tracker row by default, report skipped duplicates/already-reviewed jobs, preserve the existing status, and only create visible `Duplicate` or `Already Reviewed` history entries when duplicate saving is explicitly enabled.

---

### P4.2 Protect and migrate history

Acceptance criteria:

- Existing `job_history_master.csv` is backed up before changes.
- Backend can read existing history.
- History stores job key, first seen, last seen, decision, status, profile, run ID.
- Private history is ignored by Git.

Needs confirmation:

- Keep CSV/JSON for MVP or move to SQLite.

---

### P4.3 Add parser confidence score

Acceptance criteria:

Each parsed job has:

```text
parser_confidence
parser_confidence_score
parser_notes
```

Low confidence routes to Manual Review unless hard discard is certain.

Tests cover missing title/company/location/work mode, short text, and mismatch notes.

---

### P4.4 Add capture health diagnostics

Acceptance criteria:

Capture health includes:

- run ID;
- status;
- timestamps;
- active profile;
- source type;
- pages processed;
- jobs detected;
- jobs captured;
- duplicates detected;
- parser errors;
- exit code;
- latest log path;
- last diagnostic event;
- likely failure cause.

React shows compact health summary and expandable logs.

---

### P4.5 Add latest run summary state

Acceptance criteria:

Backend stores:

```text
latest capture file
latest parsed file
latest classified file
latest XLSX tracker
counts
active profile
timestamp
run ID
```

React shows this after restart.

---

## P5 — XLSX, Export Package, Demo Mode, Privacy Cleanup

### P5.1 Implement XLSX tracker export

Objective: Create a real working tracker for applying and keeping records.

Acceptance criteria:

Workbook name:

```text
JOLT_job_tracker_<run_id>.xlsx
```

Sheets:

- Summary;
- All Reviewed Jobs;
- Apply Today;
- Manual Review;
- Waiting / Follow Up;
- Duplicates / Already Reviewed;
- Decision Explanations;
- Capture Diagnostics.

Workbook includes frozen headers, filters, adjusted widths, clickable URLs, status column, readable list serialization, workflow queue sheets, and diagnostics.

---

### P5.2 Add export package generation

Acceptance criteria:

Each run package contains:

```text
raw_capture.jsonl
parsed_jobs.csv
classified_jobs.json
classified_jobs.csv
JOLT_job_tracker_<run_id>.xlsx
classification_report.md
rules_snapshot.json
run_summary.json
diagnostics.log
```

Real packages are ignored by Git.

---

### P5.3 Add Exports page

Acceptance criteria:

- User can generate/download XLSX tracker.
- User can generate/download full run package.
- UI shows included files and active profile.
- Capture export uses the current capture result; tracker export uses saved History / Tracker data with latest statuses.
- Tracker export uses clean saved history, so skipped duplicates do not appear as new rows.
- Demo exports are clearly marked as demo if demo mode is active.

---

### P5.4 Add Public Demo Mode

Acceptance criteria:

- Demo mode can load fake/anonymized jobs.
- Demo dashboard includes Apply, Maybe, Manual Review, Discard, Duplicate examples.
- Demo mode can generate demo XLSX.
- Demo mode avoids real capture/private history by default.
- UI clearly shows when Demo Mode is active.

---

### P5.5 Add Privacy Cleanup tool

Acceptance criteria:

- Cleanup preview lists files/folders to remove.
- Cleanup preserves source code, specs, demo data, default profiles, README.
- Cleanup targets logs, captures, outputs, debug files, real runs, real XLSX trackers, history.
- User gets a clear result summary.

---

### P5.6 Add portfolio-safe rule profiles and samples

Acceptance criteria:

- Current portfolio-safe profiles contain no private details.
- Samples contain no real recruiter names, private notes, personal emails, or real job-history data.
- README can demonstrate app without exposing personal data.

---

## P6 — Refactor Legacy Logic into Testable Services

### P6.1 Split classifier responsibilities

Acceptance criteria:

Separate modules exist for:

- decision/rule engine;
- profiles/preferences;
- parser confidence;
- location rules;
- dedupe;
- history/status tracking;
- Apply Today queue;
- XLSX/export package;
- diagnostics.

---

### P6.2 Create parser service abstraction

Acceptance criteria:

- Batch parser output normalizes into ParsedJob objects.
- Manual paste produces same ParsedJob shape.
- Parser notes and confidence preserved.
- Parser does not make final decisions.

---

### P6.3 Implement triggered rule IDs

Acceptance criteria:

- Each rule has ID, label, severity, reason.
- Decision result includes triggered rules.
- Tests assert rule IDs.
- XLSX and decision cards show rule labels/reasons.

---

### P6.4 Add backend tests

Required tests:

- mandatory German => Discard under Rafael profile;
- optional German => warning only;
- remote Madrid => not distance discard;
- hybrid Madrid => Discard under Rafael profile;
- hybrid Vigo => allowed;
- positive M365 plus mandatory French => Discard;
- high on-call changes according to configured severity;
- missing work mode => Manual Review;
- low parser confidence => Manual Review;
- duplicate URL/job ID labeled Duplicate;
- already applied job labeled Already Reviewed/Already Applied;
- Apply Today queue excludes duplicates/applied jobs;
- XLSX contains required sheets and headers;
- queue sheets filter relevant rows;
- duplicate/already-reviewed rows appear in the duplicate/reviewed sheet;
- privacy cleanup does not delete source/spec/demo data.

---

## P7 — Portfolio Hardening and Documentation

### P7.1 Rewrite README around automation-first positioning

Acceptance criteria:

README states:

- local job-offer automation and decision assistant;
- capture is primary productivity workflow;
- capture includes safe manual paste/helper workflows and any real browser automation remains disabled/experimental;
- manual helper UX explains bookmarklet installation, Chrome `javascript:` URL blocking, and sample `JOLT_CAPTURE_V1` payload testing;
- experimental LinkedIn capture scaffold exists only as disabled-by-default schemas, API boundary, URL/currentJobId utilities, fake-data mock dry-run packages, selected-job-only prototype capture with focus handoff countdown, review conversion, and diagnostics; no full browser automation, card iteration, scrolling, or pagination is implemented;
- configurable profiles make it reusable;
- manual paste is fallback/debug;
- React + backend architecture;
- XLSX tracker/export package;
- privacy limitations.

---

### P7.2 Add demo checklist

Acceptance criteria:

Checklist covers:

- clean install;
- start backend/frontend;
- enable Demo Mode;
- select profile;
- run sample classification;
- show Review Dashboard;
- show Apply Today and Manual Review queues;
- export demo XLSX;
- show rules configurability;
- explain capture limitations;
- confirm no private data in repo.

---

### P7.3 Add privacy checklist

Acceptance criteria:

Checklist includes searching for:

- real emails;
- phone numbers;
- recruiter names;
- real captured LinkedIn text;
- raw logs;
- XLSX trackers;
- job history;
- personal paths.

---

### P7.4 Add About page

Acceptance criteria:

About page explains:

- local automation assistant;
- configurable rules;
- capture/parser/classifier pipeline;
- review dashboard;
- XLSX tracker;
- human-in-the-loop decisions;
- browser automation limitations;
- privacy and demo mode.

---

### P7.5 Maintain engineering log throughout implementation

Acceptance criteria:

- Each completed task appends a log entry.
- Bug repairs include root cause and test result.
- Efficiency improvements document before/after behavior when possible.
- Log contains no private captured job data.

---

## Recommended First Codex Implementation Task

Ask Codex to implement the wrapper MVP first, not a full rewrite:

```text
Create the React + FastAPI local-server skeleton for JOLT.
Keep the current capture/parser/classifier scripts as legacy modules.
Add strict .gitignore and docs/engineering-log.md.
Implement backend health, profile loading, capture runner wrapper, latest run summary, and a React Capture page with profile selector and pipeline status.
Do not refactor the classifier yet.
Do not implement XLSX until the wrapper can read latest classified results.
Update docs/engineering-log.md with every meaningful change.
```


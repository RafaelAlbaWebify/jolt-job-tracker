# AGENTS.md

## Project: JOLT / Job Opportunity Logic Tracker

## Purpose

JOLT is a local job-offer automation and decision-support tool. Its purpose is to speed up job-search filtering by automating the repetitive pipeline:

```text
browser-assisted capture
→ parser / normalizer
→ configurable rule profile
→ decision engine
→ review dashboard
→ Apply / Maybe / Discard / Manual Review shortlist
→ XLSX tracker / export package / history
```

The app should not be presented as a generic “LinkedIn scraper” or mass-apply bot. The stronger positioning is:

> A local job-offer automation assistant that captures job listings, parses them, applies configurable rule profiles, and produces explainable, tracker-ready job-search decisions.

Manual paste is a fallback, single-job review, and parser/debug workflow. It must not dominate the product narrative.

---

## Product Direction

Codex should migrate the existing Streamlit-based pipeline toward a React local-server app, similar in spirit to the Webify Site Check app:

- React frontend running locally.
- Python backend, preferably FastAPI.
- Existing capture, parser, classifier, preferences, history, export, and diagnostics wrapped behind backend services first.
- Gradual refactor into testable backend modules.
- Browser-assisted capture remains the primary productivity feature, but must be isolated, observable, recoverable, and honest about fragility.
- Filters/rules must be configurable profiles so the app is useful as a portfolio project, not only as Rafael’s personal tool.

---

## Core Workflows

### Primary workflow: automated capture, sorting, and tracking

```text
User opens a supported job search/results page
→ User selects an active rule profile
→ User starts Capture Jobs from JOLT
→ Backend runs browser-assisted capture
→ Raw job data is saved in a run folder
→ Parser extracts structured fields and parser confidence
→ Decision engine applies the selected rule profile
→ Results are grouped in the review dashboard
→ User reviews decision cards, duplicates, manual-review items, and Apply Today queue
→ User saves statuses and exports an XLSX tracker/export package
```

### Secondary workflow: manual paste / fallback / debug

```text
User pastes one job description and optional URL
→ Parser extracts fields
→ Decision engine applies selected profile
→ One explainable decision card is shown
```

Manual paste exists to test the engine, review one-off jobs, and recover when capture fails.

---

## First-Class Product Requirements

### 1. Rule profiles

The app must support reusable rule profiles. Rafael’s rules are a default/demo profile, not the whole application.

Required profiles for portfolio/demo:

```text
rafael_default
generic_it_support
remote_support_demo
portfolio_safe_demo
```

Profiles must configure:

- accepted mandatory languages;
- mandatory versus optional language severity;
- base location;
- max distance for hybrid/onsite;
- remote-distance exemption;
- accepted/preferred work modes;
- shift, weekend, 24/7, and on-call severities;
- role families to prefer, warn, or discard;
- positive keywords;
- negative/risk keywords;
- stretch skills and defensibility rules;
- parser-confidence thresholds;
- duplicate/already-reviewed handling;
- default export/tracker behavior.

### 2. Review dashboard before export

The user must be able to review a run before exporting. The dashboard should show counts and grouped results:

```text
Captured
Parsed
Apply
Maybe
Manual Review
Discard
Duplicates
Already Reviewed
Parser Low Confidence
```

### 3. Explainable decision cards

Every job shown in the UI must have an explainable card or expandable row containing:

- decision label;
- score/priority;
- company, role, location, work mode;
- parser confidence;
- main reasons;
- triggered rules;
- warnings;
- missing information;
- duplicate/already-reviewed status;
- recommended next action;
- source URL when available.

### 4. Duplicate and already-reviewed detection

The app must detect jobs already seen, reviewed, applied, discarded, or exported.

Deduplication keys should include, when available:

- LinkedIn job ID;
- source URL;
- normalized company + title;
- normalized company + title + location;
- fuzzy title/company similarity only as a secondary signal.

Duplicates must not silently disappear. They should be labeled as `Duplicate` or `Already Reviewed` and optionally hidden by filter.

### 5. Application status tracker inside the app

The app should track application status, not only classification status.

Recommended statuses:

```text
New
Apply Today
Applied
Waiting
Follow Up
Interview
Rejected
Discarded
Archived
Duplicate
Already Reviewed
```

Status changes must be saved to local history and reflected in the XLSX export.

### 6. Apply Today queue

The UI must generate a focused queue of the best jobs to apply to next.

Default logic:

- decision is Apply;
- high score/priority;
- no hard warnings;
- not duplicate;
- not already applied/reviewed;
- parser confidence is high or acceptable;
- recent capture.

The queue should be small enough to be actionable, for example top 5–10 jobs.

### 7. Manual review queue

Uncertain jobs should be grouped separately instead of being hidden in Maybe or Discard.

Manual review reasons may include:

- work mode unclear;
- location unclear;
- language requirement unclear;
- on-call/shift unclear;
- parser confidence low;
- title/company mismatch;
- role may be too senior or outside evidence;
- capture mismatch or suspicious parsed fields.

### 8. Parser confidence score

Parser output must include confidence. Suggested values:

```text
high
medium
low
```

Confidence should account for:

- job title found;
- company found;
- location found;
- work mode found;
- raw job description length;
- parser mismatch notes;
- unsupported/missing key fields;
- suspicious title/company/location extraction.

Low-confidence jobs should normally go to Manual Review unless a hard discard is certain.

### 9. Capture health diagnostics

Capture is central, so the UI must show capture health clearly.

Required diagnostic fields:

- run ID;
- started/finished time;
- active profile;
- capture source/page type;
- pages processed;
- cards/jobs detected;
- jobs captured;
- duplicates skipped/labeled;
- parser errors;
- exit code;
- latest log path;
- last diagnostic event;
- likely failure cause if available.

Capture logs should be compact by default with expandable detail.

### 10. Public demo mode

The app needs a safe portfolio/demo mode.

Demo mode must:

- use anonymized or fake job data;
- avoid real LinkedIn captures;
- avoid real recruiter/company notes unless explicitly fake/sample;
- disable or sandbox destructive cleanup actions;
- show realistic Apply/Maybe/Discard/Manual Review examples;
- support screenshots and video demos without exposing private job-search history.

### 11. Privacy cleanup tool

The app or backend should provide a cleanup command/action that removes private/generated local data before publishing or sharing.

It should target:

```text
logs/
captures_id/
outputs/
debug_outputs/
manual_inputs/
exports/
runs/ with real data
job_history_master.csv
real XLSX trackers
raw LinkedIn job text
```

Cleanup must be safe: never delete source code, specs, anonymized samples, or default demo profiles.

### 12. Better classification labels

The UI must use human-readable labels:

```text
Apply
Maybe
Manual Review
Discard
Duplicate
Already Reviewed
```

Legacy A/B/C/D labels may remain internally only if useful, but the user-facing app and exports must be clear.

### 13. Export package

Each run should produce an auditable export package, not only isolated CSVs.

Recommended structure:

```text
runs/<timestamp_or_run_id>/
  raw_capture.jsonl
  parsed_jobs.csv
  classified_jobs.json
  classified_jobs.csv
  JOLT_job_tracker.xlsx
  classification_report.md
  rules_snapshot.json
  run_summary.json
  diagnostics.log
```

### 14. Configurable portfolio-safe rules

The app should demonstrate reusable configuration without exposing Rafael’s private details. Public-safe/demo profiles should be generic enough for GitHub while Rafael’s real profile can remain local/private if needed.

Portfolio-safe profiles should avoid personal contact details, private job history, exact application notes, or unreleased personal data.

### 15. XLSX tracker export

The app must export a usable XLSX tracker, not only CSV.

Recommended sheets:

- `Shortlist` — Apply/Maybe/Manual Review jobs to work from.
- `All Captured Jobs` — every classified job.
- `Discarded` — discarded jobs with hard-discard reasons.
- `Manual Review` — unclear or low-confidence jobs.
- `Duplicates` — duplicates and already-reviewed items.
- `Rules Snapshot` — selected profile and rule configuration used.
- `Run Summary` — counts, timestamps, diagnostics, source batch.

The XLSX should include frozen headers, filters, adjusted widths, clickable URLs, status dropdowns where feasible, and clear decision/status columns.

---

## Rafael Default Profile

Rafael’s default profile is one preset. It should remain editable and replaceable.

Default behavior:

- Mandatory languages other than Spanish or English => Discard.
- Hybrid or onsite roles more than 30 km from Vigo, Spain => Discard.
- Remote roles ignore distance.
- Avoid high-pressure roles, 24/7 operations, heavy on-call, chaotic startups, rotating/night shifts, and call-centre style jobs.
- Prefer stable remote support, IT Operations, SaaS Support, Infrastructure Support, Microsoft 365, Entra ID, endpoint, networking, and automation-related roles.
- Do not recommend claiming skills not evidenced in Rafael’s CV, LinkedIn, or projects unless realistically interview-ready in 1–2 days.

---

## Engineering Log Requirement for Codex

Codex must keep an implementation and repair log during development.

Required file:

```text
docs/engineering-log.md
```

Every meaningful change should add an entry with:

- timestamp;
- task ID or reason for change;
- files changed;
- bug fixed, feature added, or optimization made;
- root cause if a bug was investigated;
- approach taken;
- tests/checks run;
- result;
- remaining risks or follow-up.

For larger runs, Codex may also write machine-readable logs:

```text
runs/<run_id>/run_summary.json
runs/<run_id>/diagnostics.log
```

The engineering log is for maintainability and portfolio credibility. It should not contain private job data, access tokens, personal application notes, or raw captured job content.

---

## Development Principles for Codex

Codex should:

- Preserve existing working capture/parser/classifier behavior before refactoring.
- Wrap legacy scripts behind backend endpoints first.
- Replace Streamlit with React local-server UI.
- Make capture the first/main UI workflow.
- Keep manual paste as fallback/debug.
- Keep GUI, capture, parser, decision engine, profiles, history, exporter, diagnostics, and cleanup separate.
- Add tests before changing rule behavior.
- Protect local history and private generated data.
- Update `docs/engineering-log.md` after bug fixes, efficiency improvements, refactors, and feature additions.

Codex must not:

- Rebrand the app as a mass scraper or application bot.
- Hardcode Rafael-only assumptions throughout the app.
- Hide parser/capture uncertainty.
- Silently delete private data without explicit cleanup action.
- Commit real captured job data, logs, XLSX trackers, or history.
- Mix React UI code with backend decision rules.

---

## Repository Hygiene

Do not commit:

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
real captured job data
```

Allow only anonymized samples and portfolio-safe demo outputs under clearly named directories such as:

```text
samples/
examples/
demo_data/
portfolio_demo/
```


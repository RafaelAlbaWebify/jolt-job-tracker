# Product Spec: JOLT / Job Opportunity Logic Tracker

## 1. Summary

JOLT is a local job-offer automation and decision assistant. It helps users capture batches of job listings, parse messy job data, apply configurable rule profiles, and produce explainable job-search decisions:

- Apply
- Maybe
- Manual Review
- Discard
- Duplicate
- Already Reviewed

The app is automation-first. Manual paste exists, but only as a fallback, single-job review, or parser/debug workflow.

The product should be strong enough for Rafael’s real job search and presentable as a portfolio project. Therefore, Rafael’s own filters must be implemented as one configurable default profile, not as the only hardcoded behavior.

---

## 2. Product Positioning

Use this positioning:

> A local job-offer automation assistant that captures job listings, parses them, applies configurable rule profiles, and produces explainable, tracker-ready job-search decisions.

Avoid positioning as:

- a generic LinkedIn scraper;
- a mass-apply bot;
- a stealth automation system;
- an autonomous recruiter;
- a black-box AI job recommender;
- a cloud SaaS product for MVP.

The value is the complete workflow: capture, parsing, configurable filtering, explainable decisions, review dashboard, XLSX tracker, history, and portfolio-safe demo mode.

---

## 3. Primary Product Goals

The app should help users:

1. Capture job offers faster.
2. Sort large batches into useful groups.
3. Discard unsuitable roles quickly and explain why.
4. Surface best jobs in an Apply Today queue.
5. Flag unclear jobs in a Manual Review queue.
6. Track duplicates and already-reviewed jobs.
7. Keep an application-status record inside the app.
8. Export a usable XLSX tracker and full run package.
9. Demonstrate configurable local automation in a public portfolio.

---

## 4. Primary Workflow

```text
Open supported job results page
→ Start JOLT local app
→ Select active rule profile
→ Capture jobs
→ Parse and normalize jobs
→ Classify/sort jobs
→ Review dashboard
→ Update statuses / choose Apply Today jobs
→ Export XLSX tracker and run package
→ Continue applying and tracking progress
```

Capture is a core productivity feature. In the current portfolio demo it is limited to manual jobs, pasted page text, HTML fragments, uploaded/copied HTML content, and a user-triggered manual browser helper/bookmarklet that copies visible current-page content into a pasted `JOLT_CAPTURE_V1` payload. Automated browser capture remains disabled/experimental and must expose clear diagnostics, logs, and recovery options before any future implementation.

The manual browser helper must not navigate, crawl, store credentials, bypass CAPTCHA/login/rate-limit protections, run in the background, or submit applications.

Phase 17A adds only an experimental LinkedIn capture scaffold: disabled-by-default feature flag, health/start/stop/status API boundaries, raw run package schemas, currentJobId URL utilities, duplicate-reference helpers, and diagnostic status codes. It must not perform real browser automation, click job cards, navigate result pages, use pyautogui/pywin32/Selenium/Playwright, log in, store credentials, bypass protections, auto-apply, send messages, or feed dry-run output into History.

---

## 5. Secondary Workflow: Manual Paste / Debug

Manual paste supports:

- reviewing a single job from any source;
- debugging the parser;
- testing a rule profile;
- demonstrating the decision engine without running capture;
- recovering when capture extraction is unclear or when a future browser-assisted adapter fails.

Manual paste must use the same parser, profile system, and decision engine as captured jobs.

---

## 6. Rule Profiles

The app must support multiple configurable profiles.

Required default/demo profiles:

```text
rafael_default
generic_remote_it_support
saas_support
infrastructure_support
```

Each profile should define:

### Language rules

- accepted mandatory languages;
- language aliases;
- mandatory unsupported language behavior: Discard / Manual Review / Warning / Ignore;
- optional unsupported language behavior;
- ambiguous language behavior.

### Location and distance rules

- base city/location;
- max distance for hybrid/onsite;
- whether remote roles ignore distance;
- allowed countries/regions;
- blocked countries/regions;
- unknown location behavior.

### Work mode rules

- accepted work modes;
- preferred work modes;
- severity for onsite, hybrid, remote, unknown;
- remote-only mode option.

### Schedule and pressure rules

- on-call severity;
- 24/7 severity;
- rotating shift severity;
- night shift severity;
- weekend work severity;
- call-centre/call-center severity;
- high-pressure/fast-paced severity;
- chaotic-startup severity.

### Role fit rules

- preferred role families;
- maybe/manual-review role families;
- discard role families;
- positive keywords;
- negative keywords;
- stretch skills;
- defensibility settings.

### Parser and confidence rules

- minimum parser confidence for Apply;
- low-confidence behavior;
- parser mismatch behavior;
- missing critical field behavior.

### Tracking/export rules

- default status for Apply/Maybe/Manual Review/Discard;
- whether duplicates are hidden or shown;
- default Apply Today queue size;
- export package options.

---

## 7. Rafael Default Profile

Rafael’s profile should be implemented as a configurable preset.

Default rules:

- Mandatory languages other than Spanish or English => Discard.
- Hybrid or onsite roles more than 30 km from Vigo, Spain => Discard.
- Remote roles ignore distance.
- Avoid high-pressure roles, 24/7 operations, heavy on-call, chaotic startups, rotating/night shifts, and call-centre style jobs.
- Prefer stable remote roles in IT Support, IT Operations, SaaS Support, Infrastructure Support, Microsoft 365, Entra ID, endpoint support, networking, and automation-adjacent support.
- Do not classify as Apply if main requirements are not evidenced in Rafael’s CV, LinkedIn, or projects unless realistically interview-ready in 1–2 days.

Needs confirmation:

- Which parts of Rafael’s real profile should be committed as public demo defaults versus stored locally as private profile data.

---

## 8. Review Dashboard Before Export

The app must show a review dashboard after each run and before export.

Dashboard summary cards:

```text
Captured jobs
Parsed jobs
Apply
Maybe
Manual Review
Discard
Duplicates
Already Reviewed
Low Parser Confidence
Export Ready
```

Dashboard views:

- Apply Today queue.
- All Apply jobs.
- Maybe jobs.
- Manual Review queue.
- Duplicates / Already Reviewed.
- Discarded jobs.
- Capture diagnostics.

The user should be able to review and adjust statuses before exporting the XLSX tracker.

---

## 9. Explainable Decision Cards

Each job must be shown as a card or expandable table row.

Required visible fields:

- decision label;
- application status;
- score / priority;
- title;
- company;
- location;
- work mode;
- distance or location rule result;
- parser confidence;
- main reasons;
- triggered rules;
- warnings;
- missing information;
- duplicate/already-reviewed status;
- recommended next action;
- source URL.

The card should make uncertainty visible. It should never imply certainty when the parser has low confidence or critical fields are missing.

---

## 10. Duplicate and Already-Reviewed Detection

The app must keep history and detect repeated jobs.

Detection sources:

- job ID;
- source URL;
- normalized company + title;
- normalized company + title + location;
- source batch/run ID;
- previous application/action status;
- fuzzy similarity only as a secondary signal.

User-facing labels:

- Duplicate;
- Already Reviewed;
- Already Applied;
- Previously Discarded;
- Seen Before.

Duplicates should be visible by default in summary counts and optionally hidden in the main shortlist.

---

## 11. Application Status Tracker Inside the App

The app should track the application process locally.

Recommended statuses:

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

Backward-compatible saved statuses such as `Not started`, `Interview`, `Watchlist`, and `Discarded` may remain readable for old local history, but the active queue UI should emphasize the statuses above.

The user should be able to update status from the History / Tracker view. Status changes should persist immediately through the history API, survive refresh, and appear in tracker/history XLSX exports. `Save to History` is only required after a new capture result; it should save new jobs and skip duplicate/already-reviewed jobs by default while preserving existing tracker statuses. Capture export uses the current run payload, while tracker export uses saved history with latest statuses.

Legacy statuses remain readable for old local files but should not be emphasized as normal UI choices. Recommended mappings are `Not started` -> `New`, `Watchlist` -> `Follow Up`, `Discarded` -> `Rejected`, and `Interview` -> `Waiting`.

Needs confirmation:

- Whether status/history storage remains CSV/JSON for MVP or moves to SQLite.

---

## 12. Apply Today Queue

The Apply Today queue should show the most actionable jobs from the latest run/history.

Default criteria:

- decision = Apply;
- high priority/score;
- not duplicate;
- not already applied/reviewed;
- parser confidence high or acceptable;
- no blocking warnings;
- recent capture;
- profile match is strong.

Default queue size: top 5–10 jobs.

The user should be able to mark jobs as Applied, Waiting, Follow Up, Archived, or Discarded.

---

## 13. Manual Review Queue

The Manual Review queue should isolate uncertainty.

Typical reasons:

- work mode unclear;
- location unclear;
- language requirement unclear;
- on-call or shift unclear;
- parser confidence low;
- parser mismatch;
- suspicious title/company/location pairing;
- role could be too senior;
- role has stretch skills;
- employment type unclear.

Manual Review is not a failure. It is how the app stays honest.

---

## 14. Parser Confidence Score

Each parsed job should include:

```json
{
  "parser_confidence": "high | medium | low",
  "parser_confidence_score": 0,
  "parser_notes": []
}
```

Confidence should be lowered by:

- missing title;
- missing company;
- missing location;
- missing work mode;
- very short raw description;
- parser mismatch notes;
- suspicious company/location extraction;
- capture panel mismatch;
- unsupported or malformed fields.

Low confidence should route the job to Manual Review unless a hard discard is certain.

---

## 15. Capture Health Diagnostics

The capture workflow must produce visible health diagnostics.

Required fields:

```json
{
  "run_id": "",
  "status": "running | success | warning | failed",
  "started_at": "",
  "finished_at": "",
  "source_type": "",
  "active_profile": "",
  "pages_processed": 0,
  "jobs_detected": 0,
  "jobs_captured": 0,
  "duplicates_detected": 0,
  "parser_errors": 0,
  "exit_code": 0,
  "latest_log_path": "",
  "last_diagnostic_event": "",
  "likely_failure_cause": ""
}
```

The UI should show a compact summary and expandable logs.

---

## 16. Public Demo Mode

Public Demo Mode must allow safe portfolio demonstrations.

Demo Mode should:

- use fake/anonymized job data;
- disable real capture by default or clearly separate it;
- load portfolio-safe profiles;
- populate demo dashboard with Apply/Maybe/Manual Review/Discard examples;
- allow demo XLSX export using fake data;
- avoid real recruiter names, private notes, real application history, personal emails, or raw captured LinkedIn data.

---

## 17. Privacy Cleanup Tool

The app should provide a cleanup tool or command.

Cleanup should remove private/generated data:

```text
logs/
captures_id/
outputs/
debug_outputs/
manual_inputs/
exports/
runs/real_*/
real XLSX trackers
job_history_master.csv
raw captured job text
```

Cleanup must preserve:

```text
source code
specs
README
anonymized samples
demo data
default portfolio-safe profiles
```

The cleanup UI should show what will be removed before removal.

---

## 18. Better Classification Labels

User-facing labels must be:

- Apply
- Maybe
- Manual Review
- Discard
- Duplicate
- Already Reviewed

Legacy A/B/C/D labels may remain only as internal priority bands if needed. Exports should include human-readable labels.

---

## 19. XLSX Tracker Export

XLSX is a core export format. Capture XLSX exports the current reviewed run; tracker/history XLSX exports saved local history with the latest application statuses.

Required file name pattern:

```text
JOLT_job_tracker_<run_id_or_timestamp>.xlsx
```

Current workflow-oriented sheets:

### `Summary`

Counts by decision, status, priority, profile, duplicate/reviewed state, export timestamp, source/capture mode, and diagnostics basics.

### `All Reviewed Jobs`

Main working sheet for reviewed jobs.

Columns:

```text
Status
Priority
Decision
Score
Company
Role
Location
Work Mode
Distance / Location Rule
Languages
Main Reasons
Warnings
Missing Information
Source URL
Date Captured
Date Applied
Follow-up Date
Contact / Recruiter
Application Link
Notes
```

### `Manual Review`

Unclear jobs and low-confidence parser cases.

### `Apply Today`

Current high-priority next-action queue.

### `Waiting / Follow Up`

Rows currently waiting or needing follow-up.

### `Duplicates / Already Reviewed`

Duplicate, previously seen, and already-reviewed jobs that exist in saved history. Repeated Save to History actions should not add new duplicate rows unless the user explicitly chooses to include duplicate records.

### `Decision Explanations`

Triggered rules, matched keywords, warnings, missing information, and discard explanation summaries.

### `Capture Diagnostics`

Counts, timestamps, source batch, and diagnostics.

Preferred XLSX features:

- frozen header row;
- filters enabled;
- adjusted column widths;
- clickable URLs;
- status dropdowns if feasible;
- clear decision/status formatting;
- no private data in demo exports.

---

## 20. Export Package

Each run should produce an auditable package:

```text
runs/<run_id>/
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

Real run packages must be ignored by Git. Demo run packages may be committed only if anonymized.

---

## 21. Engineering Log Requirement

Codex must maintain:

```text
docs/engineering-log.md
```

Each meaningful implementation, bug repair, efficiency improvement, refactor, or diagnostic improvement must log:

- timestamp;
- task ID;
- files changed;
- problem or goal;
- root cause when applicable;
- change made;
- tests/checks run;
- result;
- remaining risk/follow-up.

The engineering log should support maintainability and portfolio credibility. It must not contain private job text, personal application notes, access tokens, or raw LinkedIn data.

---

## 22. Non-Goals

The project should not become:

- a mass application bot;
- a cloud SaaS in the MVP;
- an AI recruiter;
- a black-box decision system;
- a full CRM;
- a scraper-first portfolio project;
- a repository containing private job-search data.


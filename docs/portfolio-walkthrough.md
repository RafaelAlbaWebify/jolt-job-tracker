# JOLT Portfolio Walkthrough

## Problem

Job searching creates repetitive review work. Every listing has to be checked for language requirements, location and work mode fit, schedule risk, role fit, and whether it is worth applying to now, later, or not at all. Doing that manually across many listings is slow and inconsistent.

## Solution

JOLT is a local job-offer decision assistant. It takes user-provided job text, parses it into a normalized job record, applies a selected rule profile, and returns an explainable decision that a human can review before exporting or saving.

The current milestone is a local portfolio demo. It proves the core product chain without risky automation:

```text
manual jobs or pasted page text/HTML
-> parser
-> rule profile
-> decision engine
-> review dashboard
-> export
-> local history/tracker
```

## Workflow

1. The user selects a rule profile.
2. The user loads synthetic demo jobs, stages manual job text, or pastes visible page text / copied HTML.
3. The backend capture runner converts that input into raw job entries.
4. The parser extracts structured fields and parser confidence.
5. The decision engine applies profile rules and returns Apply, Maybe, Discard, Manual Review, or Duplicate.
6. The frontend shows decision counts, filters, and explainable cards.
7. The user can export JSON / CSV / XLSX or save the reviewed run to local history.
8. The History / Tracker page lets the user update application status locally.

## Architecture

Frontend:

- React + Vite app.
- Capture page as the main workflow.
- Rule Profiles page for profile inspection.
- History / Tracker page for saved local decisions.
- About page for demo safety and cleanup.

Backend:

- FastAPI routers for health, profiles, parse, classify, capture, export, history, and demo cleanup.
- Profile service backed by JSON default profiles.
- Rule-based parser service.
- Decision engine service.
- Capture runner and page text / HTML adapter.
- Export package service for JSON, CSV, and XLSX.
- JSONL local history store.

## Why The Safe Capture Boundary Exists

The project is intentionally not presented as a scraper. Real browser automation can be fragile and can create ethical or operational risk if it bypasses site protections or runs as mass crawling.

The current safe boundary supports:

- manual jobs;
- user-provided page text / copied HTML;
- explicit disabled browser-assisted placeholder.

This keeps the valuable parser/profile/decision/review workflow testable while making the limits honest.

## Where The Real Value Is

The strongest part of JOLT is not scraping. The real value is the explainable review pipeline:

- normalized job records;
- configurable rule profiles;
- hard-discard and risk rules;
- parser confidence;
- visible missing information;
- review dashboard before export;
- local tracker and export package.

That is what makes the app reusable and portfolio-safe.

## Intentionally Avoided

- LinkedIn scraping.
- Playwright or Selenium automation.
- Credential storage.
- CAPTCHA, paywall, authentication, or rate-limit bypass.
- Auto-apply behavior.
- Profile editing in the current UI.
- Database or cloud sync.
- Real generated job-search data in Git.

## Future Roadmap

- Richer XLSX tracker sheets and export package reports.
- Apply Today and Manual Review queues from saved history.
- Capture-time duplicate/already-reviewed labels.
- Profile editing and validation UI.
- Optional browser-assisted capture only if explicit, local, observable, and respectful of site terms.
- Portfolio screenshots and a short demo video using synthetic data.

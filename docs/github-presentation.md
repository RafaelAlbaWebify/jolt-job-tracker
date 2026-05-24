# GitHub Presentation Notes

## Suggested Repository Description

Local job-offer decision assistant built with React and FastAPI for explainable job review, export, and tracking.

## Suggested GitHub Topics

- `fastapi`
- `react`
- `typescript`
- `python`
- `job-search`
- `portfolio-project`
- `local-first`
- `automation`
- `parser`
- `decision-engine`
- `xlsx`
- `rule-engine`

## Suggested Pinned Repo Description

LinkAut is a local React + FastAPI app that parses user-provided job text, applies configurable rule profiles, explains Apply / Maybe / Discard / Manual Review decisions, exports XLSX / CSV / JSON, and saves reviewed jobs to a local tracker.

## Suggested README Opening Blurb

LinkAut is a local job-offer decision assistant for fast, explainable job review. It turns manual job text or user-provided page text/HTML into structured parser output, applies configurable rule profiles, explains each decision, and supports local export and tracking.

## What To Say In An Interview

LinkAut is a portfolio project that demonstrates a full local workflow, not just a UI mockup. The backend has separate services for parsing, profile loading, decision logic, capture boundaries, export, history, and cleanup. The frontend makes that chain visible through a Capture page, review dashboard, profile viewer, local tracker, and About/demo safety page.

The important design decision is the safe boundary around capture. I did not build it as a scraper or mass automation tool. The current demo works with manual jobs and user-provided page text/HTML, while browser-assisted capture is clearly disabled and experimental. That keeps the project honest and lets the parser and decision engine be tested properly.

## What Not To Claim

- Do not say it scrapes LinkedIn.
- Do not say browser automation is implemented.
- Do not say it applies to jobs automatically.
- Do not call it production SaaS.
- Do not imply generated export/history data should be committed.

## Suggested Screenshot Order

1. Capture page with local portfolio demo safety copy.
2. Page text / HTML mode with synthetic pasted content.
3. Review dashboard with decision counts and cards.
4. Export controls.
5. History / Tracker.
6. About / demo safety cleanup.

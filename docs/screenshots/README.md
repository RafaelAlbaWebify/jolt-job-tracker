# Screenshot Capture Guide

Actual screenshots are not committed yet. Use this guide to capture real screenshots manually from the local app with synthetic demo data only.

## Recommended Setup

- Browser: Chrome, Edge, or Firefox.
- Browser zoom: `90%` or `100%`; use `90%` if the Capture page feels cramped.
- Window width: `1440px` wide when possible.
- Window height: at least `900px`.
- Backend: `http://127.0.0.1:8000`.
- Frontend: `http://localhost:5173`.
- Data: use only synthetic demo jobs from the app or synthetic text from `docs/demo-checklist.md`.

## Recommended Demo Data Flow

1. Start the backend.
2. Start the frontend.
3. Open the Capture page.
4. Select `Rafael Default` or another demo profile.
5. Click `Load demo jobs`.
6. Click `Run capture review`.
7. Export XLSX if capturing export controls.
8. Save to history if capturing History / Tracker.
9. Use About for demo safety and cleanup screenshots.
10. Clean local demo data after the screenshot session if needed.

For page text / HTML capture:

1. Switch Capture to `Page text / HTML`.
2. Paste the synthetic multi-job sample from `docs/demo-checklist.md`.
3. Click `Extract and review`.
4. Open capture notes on one result card if useful.

## Screenshot Files To Add

| Filename | What it should show |
| --- | --- |
| `docs/screenshots/01-capture-page.png` | Capture page before or after `Load demo jobs`, showing local portfolio demo copy, profile selector, capture health, and manual/page text modes. |
| `docs/screenshots/02-page-text-capture.png` | Page text / HTML mode with synthetic pasted content and the disabled browser-assisted placeholder visible if possible. |
| `docs/screenshots/03-review-dashboard.png` | Review dashboard after a run, showing decision counts and at least one decision card. |
| `docs/screenshots/04-export-controls.png` | Export controls after a successful run, ideally showing JSON / CSV / XLSX buttons and a generated local path. |
| `docs/screenshots/05-history-tracker.png` | History / Tracker after saving demo jobs, showing saved jobs and application status controls. |
| `docs/screenshots/06-about-demo-safety.png` | About page showing current milestone, intentionally disabled features, local storage notes, and cleanup control. |

## Privacy Checklist Before Screenshots

- Use synthetic demo jobs only.
- Do not show real job applications, recruiter names, notes, emails, phone numbers, personal URLs, or private company data.
- Do not include generated real export paths that reveal private project locations beyond the local repo.
- Do not include browser tabs with personal accounts, emails, messages, or private search pages.
- Do not show real LinkedIn pages or real captured LinkedIn text.
- Do not include terminal output containing secrets, tokens, local environment values, or private paths outside this repository.
- Confirm no generated real `.xlsx`, `.csv`, `.jsonl`, `.log`, export, or history files are staged before publishing.

## After Capturing

If screenshots are added later, update the README screenshot section from placeholder checklist/table wording to embedded images or links. Keep screenshots portfolio-safe and committed only when they contain synthetic data.

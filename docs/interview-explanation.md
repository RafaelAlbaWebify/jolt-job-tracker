# Interview Explanation

## 30-Second Explanation

LinkAut is a local job-offer decision assistant built with React and FastAPI. It helps review job listings faster by parsing manual job text or user-provided page text, applying configurable rule profiles, and explaining whether each role should be Apply, Maybe, Discard, or Manual Review. It also exports results and saves reviewed jobs to a local tracker.

## 90-Second Explanation

I built LinkAut to make repetitive job-search review more structured. When you are looking at many Technical Support, IT Ops, or Infrastructure Support roles, the same questions come up repeatedly: Is the work mode clear? Is the location acceptable? Are the language requirements compatible? Is there 24/7, heavy on-call, or shift risk? Does the role match the profile?

The app is local-first. The frontend is React and TypeScript, and the backend is FastAPI. The workflow is:

```text
manual job text or user-provided page text/HTML
-> parser
-> configurable rule profile
-> decision engine
-> review dashboard
-> export / local history
```

Each decision is explainable. The card shows the decision, score, priority, parser confidence, reasons, warnings, missing information, and matched keywords. It can export JSON, CSV, or XLSX and save jobs to local history with application status.

I deliberately avoided making it a scraper or auto-apply tool. Browser-assisted capture is visible as a disabled/experimental placeholder, and the working demo uses content the user provides.

## Technical Explanation

The backend is split into services:

- profile loading from JSON default profiles;
- parser service for normalizing raw job text;
- decision engine for profile-based rules and scoring;
- capture runner and page text / HTML adapter;
- export package service for JSON, CSV, and XLSX;
- JSONL-backed local history store;
- demo cleanup service for generated local data.

The frontend is a compact React/Vite app with a main Capture page, Rule Profiles page, History / Tracker page, and About page. It calls the backend APIs and displays the real parser and decision-engine output rather than duplicating business rules in the UI.

## Safe Answer: Is This A LinkedIn Scraper?

No. The current portfolio demo is not a LinkedIn scraper. It supports manual job text and user-provided page text or copied HTML. Browser-assisted capture is shown as an explicit disabled/experimental placeholder. It does not crawl sites, store credentials, bypass authentication, or automate applications.

## Safe Answer: Does It Use AI?

Not in the current implementation. The current value is rule-based parsing, configurable profiles, explainable decision logic, local export, and local tracking. AI could be explored later for richer parsing or summarization, but I would keep the final decision explainable and user-controlled.

## Safe Answer: What Would You Improve Next?

I would improve three areas:

1. Add richer XLSX tracker sheets and downloadable export UX.
2. Add Apply Today and Manual Review queues from saved history.
3. Add profile editing and validation so users can adjust rules without touching JSON.

After that, I would only consider browser-assisted capture if it stays explicit, local, observable, and respectful of site terms.

## Safe Answer: Why Did You Build It?

I built it because job-search review has a lot of repetitive operational checking. My background and target roles are around IT Operations, Technical Support, and Infrastructure Support, where structured triage matters. LinkAut applies that same mindset to job review: normalize the input, apply clear rules, surface risks, keep uncertainty visible, and make the output easy to track.

# LinkedIn Post Draft

## Short Version

I have been working on JOLT, a local job-search decision assistant built with React and FastAPI.

The idea is simple: job searching involves a lot of repetitive review. JOLT takes manual job text or user-provided page text/HTML, parses it, applies configurable rules, and explains whether a role looks like Apply, Maybe, Discard, or Manual Review.

It can export reviewed results to XLSX, CSV, or JSON, and save jobs into a local tracker.

I have been careful with the boundaries: it is not a scraper, not a mass-apply bot, and browser automation is disabled in the current demo. The current value is the parser, rule profiles, decision engine, review dashboard, and local tracker.

The project is now at a local portfolio demo milestone.

## Slightly Longer Version

I have been building JOLT, a local job-search decision assistant with React and FastAPI.

The problem it solves is very practical: reviewing job offers gets repetitive quickly. The same checks come up again and again: language requirements, location, work mode, shift/on-call risk, role fit, missing information, and whether a job is worth applying to now.

JOLT turns manual job text or user-provided page text/HTML into a structured review flow:

```text
raw job text
-> parser
-> configurable rule profile
-> decision engine
-> review dashboard
-> export / local tracker
```

The app explains each decision instead of hiding it. A result includes the decision label, score, priority, reasons, warnings, missing information, parser confidence, and matched keywords.

It currently supports:

- React + FastAPI local app;
- configurable rule profiles;
- parser confidence;
- Apply / Maybe / Discard / Manual Review decisions;
- local JSON / CSV / XLSX export;
- local history and application status tracking;
- demo cleanup for generated local data.

I intentionally kept the capture boundary safe: this is not a LinkedIn scraper, not a mass-apply bot, and browser automation is disabled in the current portfolio demo. Page text / HTML capture uses content the user provides.

For me, the interesting part is not scraping. It is building a transparent review pipeline that makes repetitive job-search decisions faster, more consistent, and easier to explain.

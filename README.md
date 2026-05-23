# LinkAut Job Search Assistant

A local job-search automation assistant for capturing, parsing, classifying, and tracking job offers with configurable rule profiles.

LinkAut is a local job-search automation assistant designed to speed up job-offer review.

It captures or imports job offers, parses relevant fields, applies configurable rule profiles, and sorts opportunities into clear decision categories such as Apply, Maybe, Manual Review, Duplicate, or Discard.

The project is designed around a human-in-the-loop workflow: it helps prioritise and explain decisions, but it does not apply to jobs automatically.

## Backend setup

From `backend/`:

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pytest
```

Run the local backend with:

```bash
uvicorn app.main:app --reload
```

## Important note

LinkAut is not a mass-application bot and is not intended to bypass job-board rules. Browser-assisted capture is treated as a local productivity feature and may break if a website changes its layout. The core value of the project is the configurable parsing, rule-based classification, review dashboard, application tracking, and export workflow.

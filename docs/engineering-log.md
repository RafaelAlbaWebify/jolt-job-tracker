# Engineering Log

## 2026-05-23 - Repository assessment

### Scope

First-pass repository inspection only. No feature implementation was performed.

Requested comparison targets:

- `AGENTS.md`
- `specs/*.md`
- Existing repository contents

### Current repository assessment

The repository is currently a very small project shell rather than an implemented application. On `main`, the accessible tracked files are:

- `README.md`
- `.gitignore`
- `LICENSE`
- `docs/engineering-log.md` (created by this assessment)

`AGENTS.md` is not present on `main`, so there are no repository-specific agent instructions to reconcile yet.

`specs/` is not present on `main`, so there are no checked-in spec files to compare against yet. The README does establish the intended product direction: a local job-search assistant for capturing or importing offers, parsing fields, applying configurable rule profiles, classifying opportunities, supporting human review, tracking applications, and exporting results.

The current repository does not contain the legacy Streamlit pipeline, React frontend, FastAPI backend, parser/classifier modules, tests, or sample fixtures. The next work should therefore start by adding structure and specs before porting or implementing behavior.

### Product direction to preserve

- Legacy Streamlit pipeline is reference material only.
- Target application architecture is React frontend plus FastAPI backend.
- Primary workflow is `capture -> parse -> classify -> review -> export`.
- Manual paste should exist as a fallback/debug path, not as the main workflow.
- Human-in-the-loop review remains central; the project should not become a mass-application bot.

### Proposed target folder structure

```text
.
├── AGENTS.md
├── README.md
├── LICENSE
├── .gitignore
├── docs/
│   ├── engineering-log.md
│   ├── architecture.md
│   └── decisions/
├── specs/
│   ├── product.md
│   ├── workflow.md
│   ├── capture.md
│   ├── parsing.md
│   ├── classification.md
│   ├── review.md
│   └── export.md
├── frontend/
│   ├── package.json
│   ├── index.html
│   ├── vite.config.ts
│   └── src/
│       ├── app/
│       ├── components/
│       ├── features/
│       │   ├── capture/
│       │   ├── review/
│       │   └── export/
│       ├── api/
│       └── types/
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── services/
│   │   │   ├── capture/
│   │   │   ├── parsing/
│   │   │   ├── classification/
│   │   │   ├── review/
│   │   │   └── export/
│   │   └── storage/
│   └── tests/
├── legacy/
│   └── streamlit_reference/
├── samples/
│   ├── captures/
│   ├── parsed/
│   └── exports/
└── scripts/
```

### Private/generated files to ignore or remove

The current `.gitignore` already covers several important generated/private paths, including virtual environments, Python caches, Node build outputs, local LinkAut data folders, real exports/captures, and personal config files.

Additional private/generated files that should be ignored and removed if already committed in future imports:

- `captures/` and `captures_raw/`
- `browser_profiles/`, `.playwright/`, and Playwright/browser session artifacts
- `html_snapshots/`, screenshots, and raw captured job pages unless sanitized under `samples/`
- `backend/.env`, `frontend/.env`, and all local env variants
- `backend/logs/`, `frontend/.vite/`, coverage outputs, and test caches
- `.mypy_cache/`, `.ruff_cache/`, `.coverage`, `htmlcov/`
- OS/editor files such as `.DS_Store`, `Thumbs.db`, `.vscode/`, `.idea/`
- Real job-history data such as `job_history_master.csv`, personal rules, preferences, exported spreadsheets, JSONL capture logs, and debug dumps

### Proposed `.gitignore` update

```gitignore
# Python
.venv/
venv/
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
coverage.xml
htmlcov/

# Node / React
node_modules/
dist/
build/
.vite/
frontend/node_modules/
frontend/dist/
frontend/build/
frontend/.vite/
coverage/

# Environment / local config
.env
.env.*
!.env.example
backend/.env
backend/.env.*
frontend/.env
frontend/.env.*
local_config.json
personal_rules.json
job_preferences.json
job_history_master.csv

# LinkAut private/generated data
captures/
captures_id/
captures_raw/
manual_inputs/
outputs/
debug_outputs/
exports/
runs/
logs/
backend/data/
backend/logs/
data/
*.csv
*.xlsx
*.jsonl
*.log

# Browser automation artifacts
browser_profiles/
.playwright/
playwright-report/
test-results/
html_snapshots/
screenshots/

# Safe samples may be committed intentionally
!samples/**/*.csv
!samples/**/*.xlsx
!samples/**/*.json
!samples/**/*.jsonl
!samples/**/*.txt
!samples/**/*.md

# OS / editor
.DS_Store
Thumbs.db
.vscode/
.idea/
```

### Recommended next step

Before implementation, add the missing repository guidance and specs:

1. Create `AGENTS.md` with architecture, workflow, privacy, and implementation constraints.
2. Create `specs/*.md` for the capture, parse, classify, review, and export workflow.
3. Only then scaffold the React and FastAPI application around those specs.

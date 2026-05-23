from __future__ import annotations

from pathlib import Path
import glob

ROOT = Path.cwd()
CAPTURES_DIR = ROOT / "captures_id"
ANALYSIS_PAGES_DIR = CAPTURES_DIR / "analysis_pages"
OUTPUTS_DIR = ROOT / "outputs"
REPORTS_DIR = OUTPUTS_DIR / "reports"
GSHEET_DIR = OUTPUTS_DIR / "tracker_v2_import"
CONFIG_DIR = ROOT / "config"
LOGS_DIR = ROOT / "logs"
STATE_DIR = OUTPUTS_DIR / "state"
HISTORY_MASTER = STATE_DIR / "job_history_master.csv"

CAPTURE_SCRIPT = ROOT / "capture_engine_v35_left_panel_guided.py"
PARSER_RUNNER = ROOT / "scripts" / "run_after_capture_v34.py"


def ensure_dirs() -> None:
    for p in [CAPTURES_DIR, ANALYSIS_PAGES_DIR, OUTPUTS_DIR, REPORTS_DIR, GSHEET_DIR, CONFIG_DIR, LOGS_DIR, STATE_DIR]:
        p.mkdir(parents=True, exist_ok=True)


def latest_file(pattern: Path | str) -> Path | None:
    matches = [Path(p) for p in glob.glob(str(pattern))]
    if not matches:
        return None
    return max(matches, key=lambda p: p.stat().st_mtime)


def latest_raw_jsonl() -> Path | None:
    return latest_file(CAPTURES_DIR / "linkedin_job_text_v*.jsonl")


def parsed_csv_files() -> list[Path]:
    files = [Path(p) for p in glob.glob(str(CAPTURES_DIR / "linkedin_jobs_parsed_v34_v*.csv"))]
    if not files:
        files = [Path(p) for p in glob.glob(str(CAPTURES_DIR / "linkedin_jobs_parsed_v*_v*.csv"))]
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def latest_parsed_csv() -> Path | None:
    files = parsed_csv_files()
    return files[0] if files else None


def latest_analysis_pages() -> list[Path]:
    latest = latest_parsed_csv()
    if not latest:
        return []
    prefix = latest.stem
    return sorted(ANALYSIS_PAGES_DIR.glob(f"{prefix}_for_analysis_page_*_of_*.csv"))

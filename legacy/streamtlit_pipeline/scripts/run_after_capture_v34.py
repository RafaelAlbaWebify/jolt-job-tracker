from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] if Path(__file__).resolve().parent.name == "scripts" else Path(__file__).resolve().parent
CAPTURE_DIR = ROOT / "captures_id"
PARSER = ROOT / "scripts" / "linkedin_parse_v34_left_panel_state.py"
SPLITTER = ROOT / "scripts" / "linkedin_split_parsed_by_page.py"


def latest(pattern: str) -> Path | None:
    files = sorted(CAPTURE_DIR.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def expected_parsed_csv(raw_path: Path) -> Path:
    stem = raw_path.stem
    stem = stem.replace("linkedin_job_text_v20_", "")
    stem = stem.replace("linkedin_job_text_", "")
    return CAPTURE_DIR / f"linkedin_jobs_parsed_v34_{stem}.csv"


def run(cmd: list[str]) -> None:
    print("")
    print("Running:", " ".join(str(x) for x in cmd))
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Parse the latest LinkedIn raw JSONL capture with parser v34 and split it into analysis CSV files."
    )
    parser.add_argument(
        "raw_jsonl",
        nargs="?",
        type=Path,
        help="Optional explicit raw JSONL path. If omitted, uses the latest captures_id/linkedin_job_text_v35_*.jsonl.",
    )
    args = parser.parse_args()

    if not CAPTURE_DIR.exists():
        print(f"Capture directory not found: {CAPTURE_DIR}")
        return 2
    if not PARSER.exists():
        print(f"Parser not found: {PARSER}")
        return 3
    if not SPLITTER.exists():
        print(f"Splitter not found: {SPLITTER}")
        return 4

    raw = args.raw_jsonl or latest("linkedin_job_text_v35_*.jsonl")
    if raw is None:
        print(f"No raw JSONL found in {CAPTURE_DIR} matching linkedin_job_text_v35_*.jsonl")
        return 5
    raw = raw.resolve()

    print("Latest raw JSONL:", raw)
    print("Expected parsed CSV:", expected_parsed_csv(raw))

    run([sys.executable, str(PARSER), str(raw)])

    parsed = expected_parsed_csv(raw)
    if not parsed.exists():
        # Fallback in case parser naming changes later.
        parsed = latest("linkedin_jobs_parsed_v34_*.csv")
    if parsed is None or not parsed.exists():
        print(f"No parsed CSV produced in {CAPTURE_DIR}")
        return 6

    print("Parsed CSV:", parsed.resolve())
    run([sys.executable, str(SPLITTER), str(parsed)])

    print("")
    print("Post-capture processing complete.")
    print("Use the generated files under captures_id/analysis_pages for manual/chat analysis.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

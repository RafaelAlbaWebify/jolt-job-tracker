import json
from pathlib import Path

from app.services.experimental_linkedin_capture.models import ExperimentalCaptureRunPackage


def write_legacy_run_package(root: Path, run: ExperimentalCaptureRunPackage) -> Path:
    run_dir = root / run.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run_summary.json").write_text(
        json.dumps(run.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    with (run_dir / "captured_jobs.jsonl").open("w", encoding="utf-8") as handle:
        for job in run.captured_jobs:
            handle.write(json.dumps(job.model_dump(mode="json")) + "\n")
            if job.raw_text:
                raw_path = run_dir / f"raw_text_{job.sequence:03d}.txt"
                raw_path.write_text(job.raw_text, encoding="utf-8")
    with (run_dir / "diagnostics.jsonl").open("w", encoding="utf-8") as handle:
        for event in run.diagnostics:
            handle.write(json.dumps(event.model_dump(mode="json")) + "\n")
    return run_dir

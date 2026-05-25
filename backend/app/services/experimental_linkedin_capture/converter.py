from app.models import CapturedRawJob
from app.services.experimental_linkedin_capture.models import ExperimentalCaptureRunPackage


def experimental_run_to_raw_jobs(run: ExperimentalCaptureRunPackage) -> list[CapturedRawJob]:
    raw_jobs: list[CapturedRawJob] = []
    for job in run.captured_jobs:
        notes = [
            "mock experimental LinkedIn capture dry-run",
            f"capture_state={job.capture_state}",
        ]
        if job.current_job_id:
            notes.append(f"current_job_id={job.current_job_id}")
        if job.duplicate_of is not None:
            notes.append(f"duplicate_of_sequence={job.duplicate_of}")

        raw_jobs.append(
            CapturedRawJob(
                source="experimental_linkedin_mock",
                source_url=job.source_url,
                raw_text=job.raw_text,
                captured_at=run.finished_at or run.started_at or "",
                external_id=job.current_job_id or "",
                capture_notes=notes,
            )
        )
    return raw_jobs

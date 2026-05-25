from app.models import CapturedRawJob
from app.services.experimental_linkedin_capture.models import ExperimentalCaptureRunPackage


def experimental_run_to_raw_jobs(run: ExperimentalCaptureRunPackage) -> list[CapturedRawJob]:
    raw_jobs: list[CapturedRawJob] = []
    for job in run.captured_jobs:
        if job.capture_state.startswith("selected_job_only"):
            source = "experimental_linkedin_selected_job"
            capture_label = "selected-job experimental capture"
        elif job.capture_state.startswith("legacy_batch"):
            source = "experimental_linkedin_legacy_batch"
            capture_label = "legacy batch experimental capture"
        else:
            source = "experimental_linkedin_mock"
            capture_label = "mock experimental LinkedIn capture dry-run"
        notes = [
            capture_label,
            f"capture_state={job.capture_state}",
        ]
        if job.current_job_id:
            notes.append(f"current_job_id={job.current_job_id}")
        if job.duplicate_of is not None:
            notes.append(f"duplicate_of_sequence={job.duplicate_of}")

        raw_jobs.append(
            CapturedRawJob(
                source=source,
                source_url=job.source_url,
                raw_text=job.raw_text,
                captured_at=run.finished_at or run.started_at or "",
                external_id=job.current_job_id or "",
                capture_notes=notes,
            )
        )
    return raw_jobs

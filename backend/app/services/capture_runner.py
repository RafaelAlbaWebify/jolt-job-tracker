from uuid import uuid4

from app.models import (
    CaptureHealthStatus,
    CaptureJobResult,
    CaptureRunRequest,
    CaptureRunResult,
    CapturedRawJob,
    RuleProfile,
)
from app.services.decision_engine import classify_job
from app.services.parser import parse_job

BROWSER_AUTOMATION_WARNING = "Browser automation is not implemented in this safe capture boundary."


def get_capture_health(last_run_status: str | None = None) -> CaptureHealthStatus:
    return CaptureHealthStatus(
        capture_mode="manual_raw_jobs",
        browser_automation_enabled=False,
        last_run_status=last_run_status,
        warnings=[BROWSER_AUTOMATION_WARNING, "Submit raw_jobs manually to simulate a capture run."],
    )


def _limited_raw_jobs(request: CaptureRunRequest, warnings: list[str]) -> list[CapturedRawJob]:
    if request.max_results < 1:
        warnings.append("max_results was below 1; no raw jobs were processed.")
        return []

    if len(request.raw_jobs) > request.max_results:
        warnings.append(
            f"raw_jobs contained {len(request.raw_jobs)} item(s); only the first {request.max_results} were processed."
        )
    return request.raw_jobs[: request.max_results]


def run_capture(request: CaptureRunRequest, profile: RuleProfile) -> CaptureRunResult:
    warnings: list[str] = [BROWSER_AUTOMATION_WARNING]
    if request.dry_run:
        warnings.append("dry_run is true; no browser automation was attempted.")
    if not request.raw_jobs:
        warnings.append("No raw_jobs were provided; this phase does not perform browser capture.")

    results: list[CaptureJobResult] = []
    parsed_count = 0
    classified_count = 0
    failed_count = 0

    for raw_job in _limited_raw_jobs(request, warnings):
        errors: list[str] = []
        if not raw_job.raw_text.strip():
            errors.append("raw_text is required for manual capture boundary processing.")
            failed_count += 1
            results.append(CaptureJobResult(raw_job=raw_job, errors=errors))
            continue

        try:
            parsed_job = parse_job(raw_job.raw_text, raw_job.source_url)
            parsed_count += 1
        except Exception as exc:  # pragma: no cover - defensive boundary for future parser changes.
            errors.append(f"Parser error: {exc}")
            failed_count += 1
            results.append(CaptureJobResult(raw_job=raw_job, errors=errors))
            continue

        try:
            decision = classify_job(parsed_job, profile)
            classified_count += 1
        except Exception as exc:  # pragma: no cover - defensive boundary for future decision changes.
            errors.append(f"Classification error: {exc}")
            failed_count += 1
            results.append(CaptureJobResult(raw_job=raw_job, parsed_job=parsed_job, errors=errors))
            continue

        results.append(CaptureJobResult(raw_job=raw_job, parsed_job=parsed_job, decision=decision, errors=[]))

    status = "completed_with_errors" if failed_count else "completed"
    return CaptureRunResult(
        run_id=f"capture_{uuid4().hex}",
        status=status,
        profile_id=request.profile_id,
        total_captured=len(results),
        parsed_count=parsed_count,
        classified_count=classified_count,
        failed_count=failed_count,
        results=results,
        warnings=warnings,
        capture_health=get_capture_health(status),
    )

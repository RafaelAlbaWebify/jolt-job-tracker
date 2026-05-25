from uuid import uuid4

from app.models import (
    CaptureDiagnostics,
    CaptureHealthStatus,
    CaptureJobResult,
    CaptureRunRequest,
    CaptureRunResult,
    CapturedRawJob,
    RuleProfile,
)
from app.services.browser_capture import capture_from_page_content
from app.services.decision_engine import classify_job
from app.services.history_store import find_duplicate_history_match
from app.services.parser import parse_job

BROWSER_AUTOMATION_WARNING = "Browser automation is not implemented or attempted by default."
PAGE_TEXT_WARNING = "Page text/HTML capture uses pasted or uploaded user-provided content only."
PAGE_CAPTURE_MODES = {"page_text", "html_fragment", "uploaded_html_content"}


def get_capture_health(last_run_status: str | None = None) -> CaptureHealthStatus:
    return CaptureHealthStatus(
        capture_mode="manual_raw_jobs,page_text,html_fragment,uploaded_html_content",
        browser_automation_enabled=False,
        last_run_status=last_run_status,
        warnings=[
            BROWSER_AUTOMATION_WARNING,
            "Use manual_raw_jobs, page_text, html_fragment, or uploaded_html_content with content you are allowed to access.",
        ],
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
    diagnostics = CaptureDiagnostics(
        capture_mode_used=request.capture_mode,
        input_size=sum(len(job.raw_text) for job in request.raw_jobs)
        if request.capture_mode == "manual_raw_jobs"
        else len(request.page_text or request.html_content or request.uploaded_html_content),
        candidate_cards_found=len(request.raw_jobs) if request.capture_mode == "manual_raw_jobs" else 0,
        cards_accepted=0,
        cards_rejected=0,
        capture_confidence="high" if request.raw_jobs else "medium",
    )
    if request.dry_run:
        warnings.append("dry_run is true; no browser automation was attempted.")

    raw_jobs = request.raw_jobs
    if request.capture_mode in PAGE_CAPTURE_MODES:
        extracted_jobs, extraction_warnings, extraction_diagnostics = capture_from_page_content(request)
        raw_jobs = extracted_jobs
        diagnostics = extraction_diagnostics
        warnings.append(PAGE_TEXT_WARNING)
        warnings.extend(extraction_warnings)
    elif request.capture_mode == "browser_assisted":
        warnings.append("browser_assisted capture is experimental and not enabled in this build.")
        raw_jobs = []
    elif request.capture_mode != "manual_raw_jobs":
        raise ValueError(f"Unsupported capture mode: {request.capture_mode}")

    request_for_processing = request.model_copy(update={"raw_jobs": raw_jobs})
    if not request_for_processing.raw_jobs:
        warnings.append("No raw_jobs were available for capture processing.")

    results: list[CaptureJobResult] = []
    parsed_count = 0
    classified_count = 0
    failed_count = 0

    for raw_job in _limited_raw_jobs(request_for_processing, warnings):
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

        duplicate_preview = False
        duplicate_reason = ""
        duplicate_history_id = ""
        try:
            duplicate_entry, duplicate_reason = find_duplicate_history_match(parsed_job, raw_job)
            if duplicate_entry is not None:
                duplicate_preview = True
                duplicate_history_id = duplicate_entry.history_id
                duplicate_warning = f"Likely duplicate before save: {duplicate_reason}."
                decision = decision.model_copy(update={"warnings": [*decision.warnings, duplicate_warning]})
        except ValueError as exc:
            warnings.append(f"Duplicate preview skipped because local history could not be read: {exc}")

        results.append(
            CaptureJobResult(
                raw_job=raw_job,
                parsed_job=parsed_job,
                decision=decision,
                errors=[],
                duplicate_preview=duplicate_preview,
                duplicate_reason=duplicate_reason,
                duplicate_history_id=duplicate_history_id,
            )
        )

    status = "completed_with_errors" if failed_count else "completed"
    diagnostics.cards_accepted = len(results)
    diagnostics.cards_rejected = max(diagnostics.cards_rejected, diagnostics.candidate_cards_found - diagnostics.cards_accepted)
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
        capture_diagnostics=diagnostics,
    )

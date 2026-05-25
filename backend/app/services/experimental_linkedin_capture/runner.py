import os
from uuid import uuid4

from app.services.experimental_linkedin_capture.diagnostics import (
    EXP_CAPTURE_COMPLETED,
    EXP_CAPTURE_DISABLED,
    EXP_CAPTURE_STARTED,
    EXP_CAPTURE_STOPPED,
    diagnostic_event,
    utc_now_iso,
)
from app.services.experimental_linkedin_capture.models import (
    ExperimentalCaptureResponse,
    ExperimentalCaptureRunPackage,
    ExperimentalCaptureStartRequest,
)

_LATEST_RUN: ExperimentalCaptureRunPackage | None = None


def experimental_capture_enabled() -> bool:
    return os.getenv("JOLT_ENABLE_EXPERIMENTAL_LINKEDIN_CAPTURE", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def disabled_response(action: str) -> ExperimentalCaptureResponse:
    event = diagnostic_event(
        EXP_CAPTURE_DISABLED,
        "Experimental LinkedIn capture is disabled. Set JOLT_ENABLE_EXPERIMENTAL_LINKEDIN_CAPTURE=true to enable dry-run scaffolding.",
        level="warning",
        details={"action": action},
    )
    return ExperimentalCaptureResponse(
        enabled=False,
        status="disabled",
        message="Experimental LinkedIn capture is disabled by default; no browser automation is available.",
        diagnostics=[event],
        warnings=[
            "No LinkedIn pages are opened, clicked, navigated, scraped, or submitted from this scaffold.",
        ],
    )


def health_response() -> ExperimentalCaptureResponse:
    if not experimental_capture_enabled():
        return disabled_response("health")
    return ExperimentalCaptureResponse(
        enabled=True,
        status=_LATEST_RUN.status if _LATEST_RUN else "idle",
        message="Experimental LinkedIn capture scaffold is enabled for dry-run status only. Real browser automation is not implemented.",
        run=_LATEST_RUN,
        warnings=[
            "Dry-run only: no pyautogui, pywin32, Selenium, Playwright, card clicking, page navigation, login, credentials, CAPTCHA bypass, auto-apply, or messaging.",
        ],
    )


def start_capture(request: ExperimentalCaptureStartRequest) -> ExperimentalCaptureResponse:
    global _LATEST_RUN
    if not experimental_capture_enabled():
        return disabled_response("start")

    started_at = utc_now_iso()
    diagnostics = [
        diagnostic_event(
            EXP_CAPTURE_STARTED,
            "Dry-run experimental capture scaffold started; no browser automation was executed.",
            details={"max_pages": request.max_pages, "max_jobs": request.max_jobs, "dry_run": request.dry_run},
        ),
        diagnostic_event(
            EXP_CAPTURE_COMPLETED,
            "Dry-run completed without capturing jobs.",
            details={"captured_jobs": 0},
        ),
    ]
    _LATEST_RUN = ExperimentalCaptureRunPackage(
        run_id=f"exp_linkedin_{uuid4().hex[:12]}",
        status="completed",
        started_at=started_at,
        finished_at=utc_now_iso(),
        max_pages=request.max_pages,
        max_jobs=request.max_jobs,
        diagnostics=diagnostics,
        warnings=[
            "Phase 17A scaffold only. It does not connect to the normal capture workflow or save to history.",
        ],
    )
    return ExperimentalCaptureResponse(
        enabled=True,
        status=_LATEST_RUN.status,
        message="Dry-run experimental capture scaffold completed; no browser automation ran.",
        run=_LATEST_RUN,
        diagnostics=diagnostics,
        warnings=_LATEST_RUN.warnings,
    )


def stop_capture() -> ExperimentalCaptureResponse:
    global _LATEST_RUN
    if not experimental_capture_enabled():
        response = disabled_response("stop")
        response.message = "Experimental LinkedIn capture is disabled; stop is a safe no-op."
        return response

    if _LATEST_RUN and _LATEST_RUN.status == "running":
        _LATEST_RUN.status = "stopped"
        _LATEST_RUN.finished_at = utc_now_iso()
        _LATEST_RUN.diagnostics.append(
            diagnostic_event(EXP_CAPTURE_STOPPED, "Experimental capture stop requested.")
        )
    return ExperimentalCaptureResponse(
        enabled=True,
        status=_LATEST_RUN.status if _LATEST_RUN else "idle",
        message="Stop requested. No browser automation is running in the Phase 17A scaffold.",
        run=_LATEST_RUN,
    )


def status_response() -> ExperimentalCaptureResponse:
    if not experimental_capture_enabled():
        response = disabled_response("status")
        response.status = "disabled"
        return response
    return ExperimentalCaptureResponse(
        enabled=True,
        status=_LATEST_RUN.status if _LATEST_RUN else "idle",
        message="Experimental LinkedIn capture scaffold status. Real browser automation is not implemented.",
        run=_LATEST_RUN,
    )


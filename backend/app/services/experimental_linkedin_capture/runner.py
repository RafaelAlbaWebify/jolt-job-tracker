import os
import json
from pathlib import Path
from uuid import uuid4

from app.models import CaptureRunRequest, CaptureRunResult, RuleProfile
from app.services.capture_runner import run_capture
from app.services.experimental_linkedin_capture.adapter import MockExperimentalLinkedInCaptureAdapter
from app.services.experimental_linkedin_capture.converter import experimental_run_to_raw_jobs
from app.services.experimental_linkedin_capture.diagnostics import (
    EXP_CAPTURE_COMPLETED,
    EXP_CAPTURE_DISABLED,
    EXP_CAPTURE_STOPPED,
    diagnostic_event,
)
from app.services.experimental_linkedin_capture.models import (
    ExperimentalCaptureResponse,
    ExperimentalCaptureRunPackage,
    ExperimentalCaptureStartRequest,
)

_LATEST_RUN: ExperimentalCaptureRunPackage | None = None
EXPERIMENTAL_CAPTURE_ROOT = Path(__file__).resolve().parents[3] / "data" / "experimental_capture"


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
            "Mock dry-run only: no pyautogui, pywin32, Selenium, Playwright, card clicking, page navigation, login, credentials, CAPTCHA bypass, auto-apply, or messaging.",
        ],
        captured_count=len(_LATEST_RUN.captured_jobs) if _LATEST_RUN else 0,
        can_review=bool(_LATEST_RUN and _LATEST_RUN.captured_jobs),
    )


def start_capture(request: ExperimentalCaptureStartRequest) -> ExperimentalCaptureResponse:
    global _LATEST_RUN
    if not experimental_capture_enabled():
        return disabled_response("start")

    run_id = f"exp_linkedin_mock_{uuid4().hex[:12]}"
    adapter = MockExperimentalLinkedInCaptureAdapter()
    _LATEST_RUN = adapter.run(run_id=run_id, max_pages=request.max_pages, max_jobs=request.max_jobs)
    if not request.dry_run:
        _LATEST_RUN.warnings.append("dry_run=false was requested, but Phase 17B only supports mock dry-run capture.")
    _write_run_package(_LATEST_RUN)
    return ExperimentalCaptureResponse(
        enabled=True,
        status=_LATEST_RUN.status,
        message="Mock experimental capture dry run completed with fake demo jobs; no browser automation ran.",
        run=_LATEST_RUN,
        diagnostics=_LATEST_RUN.diagnostics,
        warnings=_LATEST_RUN.warnings,
        captured_count=len(_LATEST_RUN.captured_jobs),
        can_review=bool(_LATEST_RUN.captured_jobs),
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
        captured_count=len(_LATEST_RUN.captured_jobs) if _LATEST_RUN else 0,
        can_review=bool(_LATEST_RUN and _LATEST_RUN.captured_jobs),
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
        captured_count=len(_LATEST_RUN.captured_jobs) if _LATEST_RUN else 0,
        can_review=bool(_LATEST_RUN and _LATEST_RUN.captured_jobs),
    )


def review_latest_capture(profile: RuleProfile) -> CaptureRunResult:
    if not experimental_capture_enabled():
        raise ValueError("Experimental LinkedIn capture is disabled.")
    if _LATEST_RUN is None or not _LATEST_RUN.captured_jobs:
        raise ValueError("No mock dry-run package is available for review.")

    raw_jobs = experimental_run_to_raw_jobs(_LATEST_RUN)
    request = CaptureRunRequest(
        profile_id=profile.profile_id,
        capture_mode="manual_raw_jobs",
        source="experimental_linkedin_mock",
        max_results=len(raw_jobs),
        dry_run=True,
        raw_jobs=raw_jobs,
    )
    result = run_capture(request, profile)
    result.warnings.extend(
        [
            "Experimental review uses fake mock dry-run data only.",
            "No browser automation ran and nothing was saved to history automatically.",
        ]
    )
    return result


def _write_run_package(run: ExperimentalCaptureRunPackage) -> None:
    EXPERIMENTAL_CAPTURE_ROOT.mkdir(parents=True, exist_ok=True)
    package_path = EXPERIMENTAL_CAPTURE_ROOT / f"{run.run_id}.json"
    package_path.write_text(json.dumps(run.model_dump(mode="json"), indent=2), encoding="utf-8")

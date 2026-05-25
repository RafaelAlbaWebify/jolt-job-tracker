import os
import json
from pathlib import Path
from uuid import uuid4

from app.models import CaptureRunRequest, CaptureRunResult, RuleProfile
from app.services.capture_runner import run_capture
from app.services.experimental_linkedin_capture.adapter import MockExperimentalLinkedInCaptureAdapter
from app.services.experimental_linkedin_capture.converter import experimental_run_to_raw_jobs
from app.services.experimental_linkedin_capture.diagnostics import (
    EXP_CAPTURE_DISABLED,
    EXP_CAPTURE_FAILED,
    EXP_CAPTURE_STOPPED,
    EXP_LEGACY_PACKAGE_WRITTEN,
    EXP_MOUSE_CONTROL_DEPENDENCIES_MISSING,
    EXP_MOUSE_CONTROL_DEPENDENCIES_OK,
    EXP_MOUSE_CONTROL_TEST_STARTED,
    EXP_MOUSE_MOVEMENT_ATTEMPTED,
    EXP_MOUSE_MOVEMENT_COMPLETED,
    EXP_MOUSE_MOVEMENT_FAILED,
    EXP_MOUSE_POSITION_CAPTURED,
    EXP_SCREEN_SIZE_CAPTURED,
    diagnostic_event,
    utc_now_iso,
)
from app.services.experimental_linkedin_capture.legacy_batch_adapter import LegacyBatchCaptureAdapter
from app.services.experimental_linkedin_capture.legacy_diagnostics import write_legacy_run_package
from app.services.experimental_linkedin_capture.legacy_mouse_control import LegacyMouseControl
from app.services.experimental_linkedin_capture.models import (
    ExperimentalCaptureResponse,
    ExperimentalCaptureRunPackage,
    ExperimentalCaptureStartRequest,
)
from app.services.experimental_linkedin_capture.windows_selected_job_adapter import (
    WindowsSelectedJobCaptureAdapter,
    _focus_handoff_events,
)

_LATEST_RUN: ExperimentalCaptureRunPackage | None = None
_STOP_REQUESTED = False
EXPERIMENTAL_CAPTURE_ROOT = Path(__file__).resolve().parents[3] / "data" / "experimental_capture"
SELECTED_JOB_ADAPTER_FACTORY = WindowsSelectedJobCaptureAdapter
LEGACY_BATCH_ADAPTER_FACTORY = LegacyBatchCaptureAdapter
MOUSE_CONTROL_FACTORY = LegacyMouseControl


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
        message="Experimental LinkedIn capture is enabled for mock dry runs, selected-job-only capture, and legacy batch capture.",
        run=_LATEST_RUN,
        warnings=[
            "Experimental only: user-supervised local browser control; no Selenium, Playwright, login, credentials, CAPTCHA bypass, auto-apply, or messaging.",
        ],
        captured_count=len(_LATEST_RUN.captured_jobs) if _LATEST_RUN else 0,
        can_review=bool(_LATEST_RUN and _LATEST_RUN.captured_jobs),
    )


def start_capture(request: ExperimentalCaptureStartRequest) -> ExperimentalCaptureResponse:
    global _LATEST_RUN, _STOP_REQUESTED
    if not experimental_capture_enabled():
        return disabled_response("start")

    _STOP_REQUESTED = False
    if request.mode == "selected_job_only":
        return _start_selected_job_capture(request)
    if request.mode == "legacy_batch_capture":
        return _start_legacy_batch_capture(request)

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
    global _LATEST_RUN, _STOP_REQUESTED
    if not experimental_capture_enabled():
        response = disabled_response("stop")
        response.message = "Experimental LinkedIn capture is disabled; stop is a safe no-op."
        return response

    _STOP_REQUESTED = True
    if _LATEST_RUN and _LATEST_RUN.status == "running":
        _LATEST_RUN.status = "stopped"
        _LATEST_RUN.finished_at = utc_now_iso()
        _LATEST_RUN.diagnostics.append(
            diagnostic_event(EXP_CAPTURE_STOPPED, "Experimental capture stop requested.")
        )
    return ExperimentalCaptureResponse(
        enabled=True,
        status=_LATEST_RUN.status if _LATEST_RUN else "idle",
        message="Stop requested. No long-running browser automation is running in this experimental scaffold.",
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
        message="Experimental LinkedIn capture status. Legacy batch mode remains experimental and user-supervised.",
        run=_LATEST_RUN,
        captured_count=len(_LATEST_RUN.captured_jobs) if _LATEST_RUN else 0,
        can_review=bool(_LATEST_RUN and _LATEST_RUN.captured_jobs),
    )


def test_mouse_control() -> ExperimentalCaptureResponse:
    if not experimental_capture_enabled():
        response = disabled_response("test_mouse_control")
        response.message = "Experimental LinkedIn capture is disabled; mouse-control test is unavailable."
        return response

    diagnostics = [diagnostic_event(EXP_MOUSE_CONTROL_TEST_STARTED, "Mouse-control test started.")]
    mouse = MOUSE_CONTROL_FACTORY()
    dependency_error = mouse.dependency_error()
    if dependency_error:
        diagnostics.append(
            diagnostic_event(EXP_MOUSE_CONTROL_DEPENDENCIES_MISSING, dependency_error, level="error")
        )
        return ExperimentalCaptureResponse(
            enabled=True,
            status="failed",
            message="Mouse-control test failed because experimental dependencies are missing.",
            diagnostics=diagnostics,
            warnings=[dependency_error],
        )
    diagnostics.append(diagnostic_event(EXP_MOUSE_CONTROL_DEPENDENCIES_OK, "pyautogui mouse control is available."))
    diagnostics.extend(_focus_handoff_events(3))
    try:
        screen_width, screen_height = mouse.screen_size()
        mouse_x, mouse_y = mouse.mouse_position()
        diagnostics.append(
            diagnostic_event(
                EXP_SCREEN_SIZE_CAPTURED,
                "Captured screen size.",
                details={"screen_width": screen_width, "screen_height": screen_height},
            )
        )
        diagnostics.append(
            diagnostic_event(
                EXP_MOUSE_POSITION_CAPTURED,
                "Captured current mouse position.",
                details={"mouse_x": mouse_x, "mouse_y": mouse_y},
            )
        )
        diagnostics.append(diagnostic_event(EXP_MOUSE_MOVEMENT_ATTEMPTED, "Moving mouse 20px right and back."))
        mouse.test_small_movement()
        diagnostics.append(diagnostic_event(EXP_MOUSE_MOVEMENT_COMPLETED, "Mouse movement test completed."))
        return ExperimentalCaptureResponse(
            enabled=True,
            status="completed",
            message="Mouse-control test completed without clicking.",
            diagnostics=diagnostics,
        )
    except Exception as exc:
        diagnostics.append(
            diagnostic_event(
                EXP_MOUSE_MOVEMENT_FAILED,
                "Mouse-control test failed during movement.",
                level="error",
                details={"error": str(exc)[:300]},
            )
        )
        return ExperimentalCaptureResponse(
            enabled=True,
            status="failed",
            message="Mouse-control test failed during movement.",
            diagnostics=diagnostics,
            warnings=[str(exc)],
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
        source="experimental_linkedin_package",
        max_results=len(raw_jobs),
        dry_run=True,
        raw_jobs=raw_jobs,
    )
    result = run_capture(request, profile)
    result.warnings.extend(
        [
            "Experimental review uses the latest experimental package and does not save automatically.",
            "Nothing was saved to history automatically.",
        ]
    )
    return result


def _write_run_package(run: ExperimentalCaptureRunPackage) -> None:
    EXPERIMENTAL_CAPTURE_ROOT.mkdir(parents=True, exist_ok=True)
    package_path = EXPERIMENTAL_CAPTURE_ROOT / f"{run.run_id}.json"
    package_path.write_text(json.dumps(run.model_dump(mode="json"), indent=2), encoding="utf-8")


def _start_selected_job_capture(request: ExperimentalCaptureStartRequest) -> ExperimentalCaptureResponse:
    global _LATEST_RUN
    if not request.selected_job_only:
        event = diagnostic_event(
            EXP_CAPTURE_FAILED,
            "selected_job_only=true is required for selected-job capture.",
            level="error",
            details={"mode": request.mode},
        )
        return ExperimentalCaptureResponse(
            enabled=True,
            status="failed",
            message="Selected-job capture requires selected_job_only=true.",
            diagnostics=[event],
            warnings=["No browser URL or page text was captured."],
        )

    run_id = f"exp_linkedin_selected_{uuid4().hex[:12]}"
    adapter = SELECTED_JOB_ADAPTER_FACTORY()
    _LATEST_RUN = adapter.run(
        run_id=run_id,
        max_pages=1,
        max_jobs=1,
        focus_delay_seconds=request.focus_delay_seconds,
    )
    if _LATEST_RUN.status == "completed" or _LATEST_RUN.captured_jobs:
        _write_run_package(_LATEST_RUN)
    return ExperimentalCaptureResponse(
        enabled=True,
        status=_LATEST_RUN.status,
        message=_selected_job_message(_LATEST_RUN),
        run=_LATEST_RUN,
        diagnostics=_LATEST_RUN.diagnostics,
        warnings=_LATEST_RUN.warnings,
        captured_count=len(_LATEST_RUN.captured_jobs),
        can_review=bool(_LATEST_RUN.captured_jobs),
    )


def _selected_job_message(run: ExperimentalCaptureRunPackage) -> str:
    if run.status == "failed":
        return "Selected-job capture failed or dependencies are missing; no browser automation fallback was attempted."
    return "Selected-job capture completed for the currently focused browser page; review before saving."


def _start_legacy_batch_capture(request: ExperimentalCaptureStartRequest) -> ExperimentalCaptureResponse:
    global _LATEST_RUN
    run_id = f"exp_linkedin_legacy_{uuid4().hex[:12]}"
    adapter = LEGACY_BATCH_ADAPTER_FACTORY()
    _LATEST_RUN = adapter.run(
        run_id=run_id,
        max_pages=request.max_pages,
        max_jobs=request.max_jobs,
        focus_delay_seconds=request.focus_delay_seconds,
        delay_between_cards_seconds=request.delay_between_cards_seconds,
        include_pagination=request.include_pagination,
        capture_detail_phase=request.capture_detail_phase,
        debug_screenshots=request.debug_screenshots,
        timeout_seconds=request.timeout_seconds,
        stop_requested=lambda: _STOP_REQUESTED,
    )
    if _LATEST_RUN.status == "completed" or _LATEST_RUN.captured_jobs:
        _write_run_package(_LATEST_RUN)
        package_dir = write_legacy_run_package(EXPERIMENTAL_CAPTURE_ROOT, _LATEST_RUN)
        _LATEST_RUN.diagnostics.append(
            diagnostic_event(
                EXP_LEGACY_PACKAGE_WRITTEN,
                "Legacy batch raw package was written under backend/data/experimental_capture.",
                details={"run_id": _LATEST_RUN.run_id, "package_dir": str(package_dir)},
            )
        )
    return ExperimentalCaptureResponse(
        enabled=True,
        status=_LATEST_RUN.status,
        message=_legacy_batch_message(_LATEST_RUN),
        run=_LATEST_RUN,
        diagnostics=_LATEST_RUN.diagnostics,
        warnings=_LATEST_RUN.warnings,
        captured_count=len(_LATEST_RUN.captured_jobs),
        can_review=bool(_LATEST_RUN.captured_jobs),
    )


def _legacy_batch_message(run: ExperimentalCaptureRunPackage) -> str:
    if run.status == "failed":
        return "Legacy batch capture failed or dependencies are missing; review diagnostics before trying again."
    if run.status == "stopped":
        return "Legacy batch capture stopped; any captured jobs can be reviewed before saving."
    return "Legacy batch capture completed; review the captured package before saving anything to history."

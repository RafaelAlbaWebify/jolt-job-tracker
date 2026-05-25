import importlib
import time
import tkinter
from dataclasses import dataclass

from app.services.experimental_linkedin_capture.diagnostics import (
    EXP_BROWSER_URL_CAPTURED,
    EXP_CURRENT_JOB_ID_EXTRACTED,
    EXP_CURRENT_JOB_ID_MISSING,
    EXP_DETAIL_TEXT_NOT_READY,
    EXP_DETAIL_TEXT_READY,
    EXP_FOCUSED_WINDOW_CAPTURE_FAILED,
    EXP_FOCUSED_WINDOW_CAPTURE_STARTED,
    EXP_FOCUS_HANDOFF_COMPLETED,
    EXP_FOCUS_HANDOFF_STARTED,
    EXP_FOCUS_HANDOFF_WAITING,
    EXP_NON_LINKEDIN_URL_CAPTURED,
    EXP_SELECTED_JOB_ADAPTER_DEPENDENCY_MISSING,
    EXP_SELECTED_JOB_CAPTURE_COMPLETED,
    EXP_SELECTED_JOB_CAPTURE_STARTED,
    EXP_VISIBLE_TEXT_CAPTURED,
    EXP_VISIBLE_TEXT_TOO_SHORT,
    diagnostic_event,
    utc_now_iso,
)
from app.services.experimental_linkedin_capture.models import (
    ExperimentalCapturedJobRecord,
    ExperimentalCaptureDiagnostic,
    ExperimentalCaptureRunPackage,
)
from app.services.experimental_linkedin_capture.url_utils import extract_current_job_id

MIN_SELECTED_JOB_TEXT_CHARS = 600
DETAIL_READY_MARKERS = (
    "about the job",
    "easy apply",
    "save",
    "applicants",
    "remote",
    "hybrid",
    "on-site",
    "company",
    "job",
)


@dataclass
class SelectedJobSnapshot:
    source_url: str
    raw_text: str
    diagnostics: list[ExperimentalCaptureDiagnostic]
    warnings: list[str]
    errors: list[str]


class WindowsSelectedJobCaptureAdapter:
    """Experimental selected-job reader.

    This adapter copies the focused browser URL and visible page text only. It does not
    click job cards, scroll panels, paginate, log in, apply, or send messages.
    """

    def run(
        self,
        *,
        run_id: str,
        max_pages: int = 1,
        max_jobs: int = 1,
        focus_delay_seconds: int = 5,
    ) -> ExperimentalCaptureRunPackage:
        started_at = utc_now_iso()
        diagnostics = [
            diagnostic_event(
                EXP_SELECTED_JOB_CAPTURE_STARTED,
                "Selected-job capture started. The user must have focused a browser with one job selected.",
                details={"max_pages": max_pages, "max_jobs": max_jobs, "focus_delay_seconds": focus_delay_seconds},
            )
        ]

        dependency_error = self._dependency_error()
        if dependency_error:
            event = diagnostic_event(
                EXP_SELECTED_JOB_ADAPTER_DEPENDENCY_MISSING,
                "Selected-job capture requires experimental local adapter dependencies. Install experimental dependencies from backend/requirements-experimental.txt.",
                level="error",
                details={"dependency_error": dependency_error},
            )
            return ExperimentalCaptureRunPackage(
                run_id=run_id,
                status="failed",
                started_at=started_at,
                finished_at=utc_now_iso(),
                max_pages=max_pages,
                max_jobs=max_jobs,
                diagnostics=[*diagnostics, event],
                warnings=[
                    "Install experimental dependencies from backend/requirements-experimental.txt.",
                ],
                errors=[
                    "Selected-job capture requires experimental local adapter dependencies. Install experimental dependencies from backend/requirements-experimental.txt."
                ],
            )

        try:
            diagnostics.extend(_focus_handoff_events(focus_delay_seconds))
            diagnostics.append(
                diagnostic_event(
                    EXP_FOCUSED_WINDOW_CAPTURE_STARTED,
                    "Focused-window URL/text copy is starting after the focus handoff countdown.",
                )
            )
            snapshot = self.capture_snapshot()
        except Exception as exc:  # pragma: no cover - defensive boundary around OS/browser state.
            event = diagnostic_event(
                EXP_FOCUSED_WINDOW_CAPTURE_FAILED,
                "Selected-job capture failed while reading the focused browser.",
                level="error",
                details={"error": str(exc)},
            )
            return ExperimentalCaptureRunPackage(
                run_id=run_id,
                status="failed",
                started_at=started_at,
                finished_at=utc_now_iso(),
                max_pages=max_pages,
                max_jobs=max_jobs,
                diagnostics=[*diagnostics, event],
                errors=[str(exc)],
            )

        diagnostics.extend(snapshot.diagnostics)
        if snapshot.source_url and not _looks_like_linkedin_jobs_url(snapshot.source_url):
            diagnostics.append(
                diagnostic_event(
                    EXP_NON_LINKEDIN_URL_CAPTURED,
                    "Captured URL does not look like a LinkedIn Jobs URL.",
                    level="warning",
                    details={"url": snapshot.source_url[:160]},
                )
            )
        current_job_id = extract_current_job_id(snapshot.source_url)
        if current_job_id:
            diagnostics.append(
                diagnostic_event(
                    EXP_CURRENT_JOB_ID_EXTRACTED,
                    "currentJobId extracted from focused browser URL.",
                    details={"current_job_id": current_job_id},
                )
            )
        else:
            diagnostics.append(
                diagnostic_event(
                    EXP_CURRENT_JOB_ID_MISSING,
                    "No currentJobId was found in the focused browser URL.",
                    level="warning",
                )
            )

        ready = selected_job_text_ready(snapshot.raw_text)
        if len(snapshot.raw_text.strip()) < MIN_SELECTED_JOB_TEXT_CHARS:
            diagnostics.append(
                diagnostic_event(
                    EXP_VISIBLE_TEXT_TOO_SHORT,
                    "Visible selected-job text is shorter than the readiness threshold.",
                    level="warning",
                    details={"text_length": len(snapshot.raw_text)},
                )
            )
        if ready:
            diagnostics.append(
                diagnostic_event(
                    EXP_DETAIL_TEXT_READY,
                    "Visible selected-job text passed readiness checks.",
                    details={"text_length": len(snapshot.raw_text)},
                )
            )
        else:
            diagnostics.append(
                diagnostic_event(
                    EXP_DETAIL_TEXT_NOT_READY,
                    "Visible selected-job text did not pass readiness checks.",
                    level="warning",
                    details={"text_length": len(snapshot.raw_text)},
                )
            )

        captured_job = ExperimentalCapturedJobRecord(
            sequence=1,
            source_url=snapshot.source_url,
            current_job_id=current_job_id,
            raw_text=snapshot.raw_text,
            capture_state="selected_job_only_ready" if ready else "selected_job_only_unverified",
            page_index=1,
            card_index=None,
            diagnostics=diagnostics,
        )
        diagnostics.append(
            diagnostic_event(
                EXP_SELECTED_JOB_CAPTURE_COMPLETED,
                "Selected-job capture completed for the currently focused browser page.",
                details={"captured_jobs": 1, "ready": ready},
            )
        )
        return ExperimentalCaptureRunPackage(
            run_id=run_id,
            status="completed",
            started_at=started_at,
            finished_at=utc_now_iso(),
            max_pages=max_pages,
            max_jobs=max_jobs,
            captured_jobs=[captured_job],
            diagnostics=diagnostics,
            warnings=[
                *snapshot.warnings,
                "Experimental selected-job capture reads only the focused browser URL and visible copied text.",
                "No job cards were clicked, no panels were scrolled, and no pages were navigated.",
            ],
            errors=snapshot.errors,
        )

    def capture_snapshot(self) -> SelectedJobSnapshot:
        py_auto = importlib.import_module("pyautogui")
        diagnostics: list[ExperimentalCaptureDiagnostic] = []
        warnings: list[str] = []
        errors: list[str] = []

        py_auto.hotkey("ctrl", "l")
        time.sleep(0.15)
        py_auto.hotkey("ctrl", "c")
        time.sleep(0.15)
        source_url = _clipboard_text().strip()
        if source_url:
            diagnostics.append(
                diagnostic_event(
                    EXP_BROWSER_URL_CAPTURED,
                    "Focused browser URL copied from address bar.",
                    details={"url_length": len(source_url)},
                )
            )
        else:
            warnings.append("Focused browser URL could not be copied.")

        py_auto.press("esc")
        time.sleep(0.15)
        raw_text = self._copy_visible_text_with_retry(py_auto, diagnostics)
        return SelectedJobSnapshot(
            source_url=source_url,
            raw_text=raw_text,
            diagnostics=diagnostics,
            warnings=warnings,
            errors=errors,
        )

    def _copy_visible_text_with_retry(self, py_auto, diagnostics: list[ExperimentalCaptureDiagnostic]) -> str:
        best_text = ""
        for attempt in range(1, 3):
            py_auto.hotkey("ctrl", "a")
            time.sleep(0.15)
            py_auto.hotkey("ctrl", "c")
            time.sleep(0.25)
            text = _clipboard_text()
            if len(text) > len(best_text):
                best_text = text
            if text:
                diagnostics.append(
                    diagnostic_event(
                        EXP_VISIBLE_TEXT_CAPTURED,
                        "Visible page text copied from focused browser.",
                        details={"attempt": attempt, "text_length": len(text)},
                    )
                )
            if len(text) >= MIN_SELECTED_JOB_TEXT_CHARS:
                break
            diagnostics.append(
                diagnostic_event(
                    EXP_VISIBLE_TEXT_TOO_SHORT,
                    "Copied visible text was shorter than the selected-job readiness threshold.",
                    level="warning",
                    details={"attempt": attempt, "text_length": len(text)},
                )
            )
            time.sleep(0.4)
        return best_text

    def _dependency_error(self) -> str:
        try:
            importlib.import_module("pyautogui")
        except Exception as exc:
            return str(exc)
        try:
            _clipboard_text()
        except Exception as exc:
            return str(exc)
        return ""


def selected_job_text_ready(raw_text: str) -> bool:
    normalized = raw_text.lower()
    marker_hits = sum(1 for marker in DETAIL_READY_MARKERS if marker in normalized)
    return len(raw_text.strip()) >= MIN_SELECTED_JOB_TEXT_CHARS and marker_hits >= 2


def _looks_like_linkedin_jobs_url(source_url: str) -> bool:
    normalized = source_url.lower()
    return "linkedin." in normalized and "/jobs" in normalized


def _focus_handoff_events(focus_delay_seconds: int) -> list[ExperimentalCaptureDiagnostic]:
    events = [
        diagnostic_event(
            EXP_FOCUS_HANDOFF_STARTED,
            "Focus handoff countdown started. Switch to the LinkedIn tab now.",
            details={"focus_delay_seconds": focus_delay_seconds},
        )
    ]
    for seconds_remaining in range(focus_delay_seconds, 0, -1):
        events.append(
            diagnostic_event(
                EXP_FOCUS_HANDOFF_WAITING,
                "Waiting for user to focus the LinkedIn tab.",
                details={"seconds_remaining": seconds_remaining},
            )
        )
        time.sleep(1)
    events.append(
        diagnostic_event(
            EXP_FOCUS_HANDOFF_COMPLETED,
            "Focus handoff countdown completed.",
            details={"focus_delay_seconds": focus_delay_seconds},
        )
    )
    return events


def _clipboard_text() -> str:
    root = tkinter.Tk()
    root.withdraw()
    try:
        try:
            return root.clipboard_get()
        except tkinter.TclError:
            return ""
    finally:
        root.destroy()

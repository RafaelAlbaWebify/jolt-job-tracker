import time

from app.services.experimental_linkedin_capture.diagnostics import (
    EXP_BROWSER_URL_CAPTURED,
    EXP_CAPTURE_FAILED,
    EXP_CARD_CLICK_ATTEMPTED,
    EXP_CARD_SELECTED,
    EXP_CURRENT_JOB_ID_EXTRACTED,
    EXP_CURRENT_JOB_ID_MISSING,
    EXP_DETAIL_TEXT_NOT_READY,
    EXP_DETAIL_TEXT_READY,
    EXP_DUPLICATE_JOB_ID,
    EXP_JOB_LIMIT_REACHED,
    EXP_LEGACY_BATCH_CAPTURE_COMPLETED,
    EXP_LEGACY_BATCH_CAPTURE_FAILED,
    EXP_LEGACY_BATCH_CAPTURE_STARTED,
    EXP_LEGACY_CARD_CLICK_SKIPPED,
    EXP_LEGACY_CARD_DETECTED,
    EXP_LEGACY_PAGE_TRANSITION_ATTEMPTED,
    EXP_LEGACY_PAGE_TRANSITION_COMPLETED,
    EXP_LEGACY_SCROLL_ATTEMPTED,
    EXP_LEGACY_SCROLL_COMPLETED,
    EXP_LEFT_PANEL_NOT_FOUND,
    EXP_NEXT_PAGE_NOT_FOUND,
    EXP_PAGE_LIMIT_REACHED,
    EXP_SELECTED_JOB_ADAPTER_DEPENDENCY_MISSING,
    EXP_VISIBLE_TEXT_CAPTURED,
    EXP_VISIBLE_TEXT_TOO_SHORT,
    diagnostic_event,
    utc_now_iso,
)
from app.services.experimental_linkedin_capture.legacy_card_detection import (
    LegacyLeftPanelCard,
    parse_left_panel_cards_from_text,
)
from app.services.experimental_linkedin_capture.legacy_clipboard_capture import (
    LegacyClipboardCapture,
    raw_text_has_job_panel,
)
from app.services.experimental_linkedin_capture.legacy_mouse_control import LegacyMouseControl
from app.services.experimental_linkedin_capture.legacy_pagination import next_results_page_url
from app.services.experimental_linkedin_capture.models import (
    ExperimentalCapturedJobRecord,
    ExperimentalCaptureDiagnostic,
    ExperimentalCaptureRunPackage,
)
from app.services.experimental_linkedin_capture.url_utils import extract_current_job_id
from app.services.experimental_linkedin_capture.windows_selected_job_adapter import _focus_handoff_events


class LegacyBatchCaptureAdapter:
    def __init__(
        self,
        *,
        clipboard: LegacyClipboardCapture | None = None,
        mouse: LegacyMouseControl | None = None,
    ) -> None:
        self.clipboard = clipboard or LegacyClipboardCapture()
        self.mouse = mouse or LegacyMouseControl()

    def run(
        self,
        *,
        run_id: str,
        max_pages: int,
        max_jobs: int,
        focus_delay_seconds: int,
        delay_between_cards_seconds: float,
        include_pagination: bool,
        capture_detail_phase: bool,
        debug_screenshots: bool,
        timeout_seconds: int,
        stop_requested,
    ) -> ExperimentalCaptureRunPackage:
        started_at = utc_now_iso()
        diagnostics: list[ExperimentalCaptureDiagnostic] = [
            diagnostic_event(
                EXP_LEGACY_BATCH_CAPTURE_STARTED,
                "Legacy batch capture started; switch focus to the already-open LinkedIn Jobs browser tab.",
                details={
                    "max_pages": max_pages,
                    "max_jobs": max_jobs,
                    "include_pagination": include_pagination,
                    "capture_detail_phase": capture_detail_phase,
                    "debug_screenshots": debug_screenshots,
                },
            )
        ]
        dependency_error = self.clipboard.dependency_error() or self.mouse.dependency_error()
        if dependency_error:
            diagnostics.append(
                diagnostic_event(
                    EXP_SELECTED_JOB_ADAPTER_DEPENDENCY_MISSING,
                    dependency_error,
                    level="error",
                )
            )
            return _package(
                run_id=run_id,
                status="failed",
                started_at=started_at,
                diagnostics=diagnostics,
                max_pages=max_pages,
                max_jobs=max_jobs,
                errors=[dependency_error],
            )

        diagnostics.extend(_focus_handoff_events(focus_delay_seconds))
        captured: list[ExperimentalCapturedJobRecord] = []
        seen_job_ids: dict[str, int] = {}
        warnings: list[str] = []
        base_url = ""
        deadline = time.monotonic() + timeout_seconds

        try:
            for page_index in range(1, max_pages + 1):
                if stop_requested():
                    return _package(
                        run_id=run_id,
                        status="stopped",
                        started_at=started_at,
                        diagnostics=diagnostics,
                        captured_jobs=captured,
                        warnings=warnings,
                        max_pages=max_pages,
                        max_jobs=max_jobs,
                    )
                if time.monotonic() > deadline:
                    warnings.append("Legacy batch capture stopped at timeout_seconds.")
                    diagnostics.append(
                        diagnostic_event(EXP_CAPTURE_FAILED, "Legacy batch capture timeout reached.", level="warning")
                    )
                    break

                page_text = self.clipboard.copy_visible_text()
                diagnostics.append(
                    diagnostic_event(
                        EXP_VISIBLE_TEXT_CAPTURED,
                        "Copied visible page text for left-panel card detection.",
                        details={"page_index": page_index, "characters": len(page_text)},
                    )
                )
                cards = self.detect_cards(page_text, max_cards=max_jobs - len(captured))
                diagnostics.extend(
                    diagnostic_event(
                        EXP_LEGACY_CARD_DETECTED,
                        "Detected a visible left-panel job card candidate.",
                        details={
                            "page_index": page_index,
                            "card_index": card.card_index,
                            "title": card.title,
                            "company": card.company,
                        },
                    )
                    for card in cards
                )
                if not cards:
                    diagnostics.append(
                        diagnostic_event(
                            EXP_LEFT_PANEL_NOT_FOUND,
                            "No left-panel card candidates were detected from copied page text.",
                            level="warning",
                            details={"page_index": page_index},
                        )
                    )
                    break

                for card in cards:
                    if len(captured) >= max_jobs:
                        diagnostics.append(
                            diagnostic_event(EXP_JOB_LIMIT_REACHED, "Legacy batch capture reached max_jobs.")
                        )
                        break
                    if stop_requested():
                        diagnostics.append(
                            diagnostic_event(EXP_LEGACY_CARD_CLICK_SKIPPED, "Stop was requested before next card click.")
                        )
                        return _package(
                            run_id=run_id,
                            status="stopped",
                            started_at=started_at,
                            diagnostics=diagnostics,
                            captured_jobs=captured,
                            warnings=warnings,
                            max_pages=max_pages,
                            max_jobs=max_jobs,
                        )
                    diagnostics.append(
                        diagnostic_event(
                            EXP_CARD_CLICK_ATTEMPTED,
                            "Clicking detected left-panel card candidate.",
                            details={"page_index": page_index, "card_index": card.card_index},
                        )
                    )
                    self.mouse.click_card(card.click_x, card.click_y)
                    time.sleep(delay_between_cards_seconds)
                    diagnostics.append(
                        diagnostic_event(
                            EXP_CARD_SELECTED,
                            "Card click completed; copying URL and detail text.",
                            details={"page_index": page_index, "card_index": card.card_index},
                        )
                    )
                    job = self.capture_selected_card(
                        card=card,
                        sequence=len(captured) + 1,
                        page_index=page_index,
                        seen_job_ids=seen_job_ids,
                        diagnostics=diagnostics,
                    )
                    if job.source_url:
                        base_url = job.source_url
                    captured.append(job)

                if len(captured) >= max_jobs:
                    break
                if page_index >= max_pages:
                    diagnostics.append(diagnostic_event(EXP_PAGE_LIMIT_REACHED, "Legacy batch capture reached max_pages."))
                    break

                diagnostics.append(
                    diagnostic_event(
                        EXP_LEGACY_SCROLL_ATTEMPTED,
                        "Scrolling the left results panel to reveal more cards.",
                        details={"page_index": page_index},
                    )
                )
                self.mouse.scroll_left_panel()
                diagnostics.append(
                    diagnostic_event(EXP_LEGACY_SCROLL_COMPLETED, "Left-panel scroll command completed.")
                )

                if include_pagination and base_url:
                    next_url = next_results_page_url(base_url, page_index)
                    diagnostics.append(
                        diagnostic_event(
                            EXP_LEGACY_PAGE_TRANSITION_ATTEMPTED,
                            "Navigating to the next LinkedIn results page by start offset.",
                            details={"page_index": page_index + 1},
                        )
                    )
                    self.mouse.navigate_to_url(next_url)
                    diagnostics.append(
                        diagnostic_event(
                            EXP_LEGACY_PAGE_TRANSITION_COMPLETED,
                            "Next page URL navigation command completed.",
                            details={"page_index": page_index + 1},
                        )
                    )
                elif page_index + 1 <= max_pages:
                    diagnostics.append(
                        diagnostic_event(
                            EXP_NEXT_PAGE_NOT_FOUND,
                            "Pagination was not enabled, so capture stops after visible/scrollable page pass.",
                            level="warning",
                        )
                    )
                    break

            status = "completed" if captured else "failed"
            diagnostics.append(
                diagnostic_event(
                    EXP_LEGACY_BATCH_CAPTURE_COMPLETED if captured else EXP_LEGACY_BATCH_CAPTURE_FAILED,
                    "Legacy batch capture completed with captured jobs." if captured else "Legacy batch capture finished without captured jobs.",
                    level="info" if captured else "error",
                    details={"captured": len(captured)},
                )
            )
            return _package(
                run_id=run_id,
                status=status,
                started_at=started_at,
                diagnostics=diagnostics,
                captured_jobs=captured,
                warnings=warnings,
                max_pages=max_pages,
                max_jobs=max_jobs,
            )
        except Exception as exc:
            diagnostics.append(
                diagnostic_event(
                    EXP_LEGACY_BATCH_CAPTURE_FAILED,
                    "Legacy batch capture failed while controlling the focused browser.",
                    level="error",
                    details={"error": str(exc)[:300]},
                )
            )
            return _package(
                run_id=run_id,
                status="failed",
                started_at=started_at,
                diagnostics=diagnostics,
                captured_jobs=captured,
                warnings=warnings,
                max_pages=max_pages,
                max_jobs=max_jobs,
                errors=[str(exc)],
            )

    def detect_cards(self, page_text: str, *, max_cards: int) -> list[LegacyLeftPanelCard]:
        return parse_left_panel_cards_from_text(page_text, max_cards=max_cards)

    def capture_selected_card(
        self,
        *,
        card: LegacyLeftPanelCard,
        sequence: int,
        page_index: int,
        seen_job_ids: dict[str, int],
        diagnostics: list[ExperimentalCaptureDiagnostic],
    ) -> ExperimentalCapturedJobRecord:
        source_url = self.clipboard.copy_current_url()
        diagnostics.append(
            diagnostic_event(
                EXP_BROWSER_URL_CAPTURED,
                "Copied browser URL after selecting a card.",
                details={"page_index": page_index, "card_index": card.card_index},
            )
        )
        current_job_id = extract_current_job_id(source_url)
        if current_job_id:
            diagnostics.append(
                diagnostic_event(
                    EXP_CURRENT_JOB_ID_EXTRACTED,
                    "Extracted currentJobId from selected card URL.",
                    details={"current_job_id": current_job_id},
                )
            )
        else:
            diagnostics.append(
                diagnostic_event(
                    EXP_CURRENT_JOB_ID_MISSING,
                    "No currentJobId was present in the selected card URL.",
                    level="warning",
                )
            )

        raw_text = self.clipboard.copy_visible_text()
        diagnostics.append(
            diagnostic_event(
                EXP_VISIBLE_TEXT_CAPTURED,
                "Copied selected job detail text.",
                details={"characters": len(raw_text)},
            )
        )
        ready = raw_text_has_job_panel(raw_text)
        diagnostics.append(
            diagnostic_event(
                EXP_DETAIL_TEXT_READY if ready else EXP_DETAIL_TEXT_NOT_READY,
                "Selected job detail text passed readiness checks."
                if ready
                else "Selected job detail text may be incomplete or stale.",
                level="info" if ready else "warning",
            )
        )
        if len(raw_text) < 600:
            diagnostics.append(
                diagnostic_event(
                    EXP_VISIBLE_TEXT_TOO_SHORT,
                    "Selected job visible text was shorter than expected.",
                    level="warning",
                    details={"characters": len(raw_text)},
                )
            )

        duplicate_of = None
        capture_state = "legacy_batch_captured"
        if current_job_id and current_job_id in seen_job_ids:
            duplicate_of = seen_job_ids[current_job_id]
            capture_state = "legacy_batch_duplicate"
            diagnostics.append(
                diagnostic_event(
                    EXP_DUPLICATE_JOB_ID,
                    "Duplicate currentJobId detected during legacy batch capture.",
                    level="warning",
                    details={"current_job_id": current_job_id, "duplicate_of": duplicate_of},
                )
            )
        elif current_job_id:
            seen_job_ids[current_job_id] = sequence

        job_diagnostics = [event for event in diagnostics[-6:]]
        return ExperimentalCapturedJobRecord(
            sequence=sequence,
            source_url=source_url,
            current_job_id=current_job_id,
            title=card.title,
            company=card.company,
            location=card.location,
            raw_text=raw_text,
            capture_state=capture_state,
            page_index=page_index,
            card_index=card.card_index,
            duplicate_of=duplicate_of,
            diagnostics=job_diagnostics,
        )


def _package(
    *,
    run_id: str,
    status: str,
    started_at: str,
    diagnostics: list[ExperimentalCaptureDiagnostic],
    max_pages: int,
    max_jobs: int,
    captured_jobs: list[ExperimentalCapturedJobRecord] | None = None,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
) -> ExperimentalCaptureRunPackage:
    return ExperimentalCaptureRunPackage(
        run_id=run_id,
        status=status,  # type: ignore[arg-type]
        started_at=started_at,
        finished_at=utc_now_iso(),
        max_pages=max_pages,
        max_jobs=max_jobs,
        captured_jobs=captured_jobs or [],
        diagnostics=diagnostics,
        warnings=warnings or [],
        errors=errors or [],
    )

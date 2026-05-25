# Legacy LinkedIn Capture Port Map

Phase 18 ports the legacy LinkedIn Jobs capture workflow into JOLT as an experimental, disabled-by-default local browser-control mode. This map documents the legacy behavior before implementation so future work can distinguish direct ports from adapted or deferred pieces.

## Source Files Reviewed

- `legacy/streamtlit_pipeline/capture_engine_v35_left_panel_guided.py`: primary automatic capture engine. It focused an already-open browser, detected cards in the left results panel, clicked cards, copied the current URL/currentJobId, captured raw visible text, scrolled the left panel, moved between results pages, and wrote diagnostics/raw outputs.
- `legacy/streamtlit_pipeline/app.py`: Streamlit UI wrapper with setup instructions, page count, countdown, and a raw-text phase toggle.
- `legacy/streamtlit_pipeline/gui_app/runner.py`: subprocess launcher that passed page count/phase options to the capture script and wrote launcher logs.
- `legacy/streamtlit_pipeline/scripts/linkedin_parse_v34_left_panel_state.py`: post-capture parser with right-panel extraction, left-panel state matching, and mismatch diagnostics.
- `legacy/streamtlit_pipeline/scripts/run_after_capture_v34.py`: helper that ran parser and splitter after raw capture.
- `legacy/streamtlit_pipeline/scripts/linkedin_split_parsed_by_page.py`: split parsed output by captured page.

## Function And Step Mapping

| Legacy step/function | What it did | Inputs/outputs | Port decision | JOLT location | Reason |
|---|---|---|---|---|---|
| `main()` user prompts/countdown | Asked user to open LinkedIn Jobs, set filters, place mouse, then counted down before controlling browser. | Console inputs, active browser window; outputs capture run. | Adapted | `legacy_batch_adapter.py` and React About panel | JOLT uses API/UI controls, but preserves explicit manual setup and focus handoff. |
| `get_window_from_mouse()`, `force_foreground()` | Used Windows APIs to identify/focus browser under mouse. | Mouse position/HWND; focused window. | Deferred | Not active in Phase 18 | Current selected-job adapter already uses focused window/keyboard handoff; HWND-specific behavior is kept out until needed. |
| `estimate_left_panel_roi()`, `estimate_left_panel_rois()` | Estimated left result-list region from browser screenshot and mouse. | Window rect, mouse, screenshot; ROI rectangles. | Adapted | `legacy_card_detection.py` | JOLT uses conservative viewport/card target estimation and text signatures; detailed pixel ROI can be expanded later. |
| `detect_blue_title_signals()`, `build_cards_from_title_signals()` | Detected card rectangles from title-colored pixels and built clickable card boxes. | Screenshot pixels; card rectangles/fingerprints. | Adapted | `legacy_card_detection.py` | Full pixel parity is brittle. Phase 18 keeps the card abstraction and click sequencing with conservative estimated targets. |
| `capture_window_image()`, `capture_and_detect()` | Captured screenshot, detected cards/footer/thumb, optionally wrote annotated images. | HWND/window rect; `ViewportResult`. | Adapted | `legacy_batch_adapter.py`, `legacy_card_detection.py` | Debug screenshot support is exposed behind `debug_screenshots`, but tests do not require live screenshots. |
| `copy_visible_page_text_no_content_click()` | Focused page, copied all visible/page text via Ctrl+A/C, read clipboard. | Focused browser; raw page text. | Ported/adapted | `legacy_clipboard_capture.py` | Same keyboard/clipboard pattern, isolated behind experimental dependency checks and feature flag. |
| `copy_current_url()` | Copied address bar via Ctrl+L/C with retries and validation. | Focused browser; URL string. | Ported/adapted | `legacy_clipboard_capture.py` | Preserves current URL/currentJobId identity without credential/session storage. |
| `extract_current_job_id()`, `extract_start_param()`, `set_url_start*()` | Extracted currentJobId/start offset and generated page URLs. | URL strings; IDs/URLs. | Ported/adapted | Existing `url_utils.py`, new `legacy_pagination.py` | CurrentJobId extraction already existed; pagination helpers are added under experimental mode. |
| `click_card_and_read_id()` | Clicked one card, waited, copied URL, extracted currentJobId, retried mismatch. | Card target; URL/job ID/status. | Adapted | `legacy_mouse_control.py`, `legacy_batch_adapter.py` | Preserves click-read-validate sequence; avoids Apply/message controls and stays max-limited. |
| `wait_for_job_url_and_panel_text()` | Waited for expected currentJobId and stable right-panel text. | Expected ID/URL; raw text/status. | Adapted | `legacy_batch_adapter.py` | JOLT keeps stability/readiness checks and mismatch diagnostics; live reload fallback is deferred. |
| `raw_text_has_job_panel()` | Checked raw text length and job-detail markers. | Raw text; readiness bool. | Ported/adapted | `legacy_clipboard_capture.py` | Shared with selected-job concepts, tuned for batch details. |
| Mismatch diagnostics | Emitted URL/text/panel status such as mismatches and stale text. | Events/status strings. | Ported/adapted | `diagnostics.py`, `legacy_diagnostics.py` | Uses stable JOLT diagnostic event codes and package JSONL files. |
| Duplicate detection by `currentJobId` | Marked repeated currentJobIds as duplicates and linked to sequence. | Seen IDs; duplicate status. | Ported | `legacy_batch_adapter.py` | CurrentJobId remains primary identity for experimental batch capture. |
| `drag_scrollbar_to_top()`, `drag_scrollbar_down()` | Dragged left-panel scrollbar to reset/advance visible cards. | Scrollbar thumb/ROI; mouse drag. | Adapted | `legacy_mouse_control.py` | Phase 18 uses conservative wheel/drag helpers; deeper thumb tracking can be restored later. |
| Overlap/fingerprint logic | Avoided re-clicking top repeated cards after scroll. | Card fingerprints/viewport sets. | Adapted | `legacy_card_detection.py`, `legacy_batch_adapter.py` | Uses text signatures and currentJobId duplicates first; image fingerprints are deferred. |
| `open_results_page_direct_v16()`, `click_footer_next_page()` | Moved to later LinkedIn result pages by URL `start=` or visual footer click. | Current URL/page number; navigation result. | Adapted | `legacy_pagination.py`, `legacy_batch_adapter.py` | Direct `start=` navigation is available only when `include_pagination=true`; footer visual clicking remains deferred. |
| `save_outputs()`, `save_raw_text_outputs()` | Wrote markdown/CSV/JSONL raw outputs and summaries. | Records; output paths. | Adapted | `legacy_diagnostics.py`, `runner.py` | JOLT writes ignored local run packages under `backend/data/experimental_capture/`. |
| Debug screenshots | Wrote annotated card/scroll/footer screenshots. | Screenshots; image files. | Deferred/optional | `legacy_batch_adapter.py` placeholder flag | Flag is preserved; robust annotated images need later live-browser QA. |
| `capture_raw_text_phase()` | Navigated to each captured URL and captured full text in a second pass. | Captured IDs/URLs; raw text JSONL. | Adapted | `legacy_batch_adapter.py` | Phase 18 captures right-panel text immediately after card click; explicit second-pass navigation is deferred. |
| `linkedin_parse_v34_left_panel_state.py` parser | Parsed right-panel text and left-card state, emitted parser notes. | Raw JSONL; CSV/JSON. | Replaced by JOLT pipeline | Existing parser/capture review services | JOLT converts records into `CapturedRawJob` and uses current parser/decision engine. |
| `run_after_capture_v34.py` | Chained parser/splitter scripts. | Latest raw JSONL; parsed files. | Replaced | `review-latest` API | JOLT review happens through FastAPI and React review dashboard. |
| `linkedin_split_parsed_by_page.py` | Split CSV by page number or chunks. | CSV; per-page CSVs. | Deferred | Export package can cover page fields | Current workflow favors review/export package over legacy per-page CSV splits. |

## Ported Directly

- Manual setup/focus handoff before browser control.
- Current URL and currentJobId as primary identity.
- Ctrl+A/C visible text capture and Ctrl+L/C URL capture.
- Job-detail readiness checks based on text length and right-panel markers.
- Duplicate detection by currentJobId.
- Max pages, max jobs, stop/timeout-oriented safety limits.
- Local raw package output with diagnostics.

## Adapted

- Card detection is represented by a legacy-compatible card target/signature abstraction, using visible text signatures and conservative estimated click targets rather than copying every screenshot pixel heuristic at once.
- Scrolling uses isolated experimental mouse helpers rather than the full scrollbar thumb pixel detector.
- Pagination uses legacy-style `start=` URL construction only when explicitly enabled.
- Parser handoff uses JOLT's current parser/rule/decision review flow instead of the legacy CSV parser chain.

## Deferred

- Full pixel-perfect title-color card detection and annotated debug screenshots.
- HWND/window-title targeting with pywin32.
- Footer visual next-button clicking.
- Full second-pass detail navigation/reload recovery.
- Left-panel scrollbar thumb tracking and viewport image fingerprinting.

## Risks

- Local browser control is fragile because keyboard/mouse focus, browser chrome, zoom level, layout, and clipboard state can change.
- LinkedIn DOM, visual styling, and URL behavior may change.
- Estimated card targets are less exact than the legacy pixel detector until live-browser QA restores deeper screenshot parity.
- This mode controls only a user-supervised already-open browser; it does not log in, store credentials, bypass CAPTCHA or rate limits, auto-apply, or message recruiters.

## Phase 18A Debugging Notes

The first live legacy batch test showed the LinkedIn page turning blue with no visible mouse movement and zero captured jobs. That matched a sequencing problem in the Phase 18 adapter: it used Ctrl+A/Ctrl+C to copy page text for card detection before any screenshot/card click step. If text-based detection returned zero candidates, the run stopped after selecting the page and never moved the mouse.

Phase 18A changes the runtime order to:

1. focus handoff countdown;
2. dependency diagnostics;
3. active window and screenshot metadata capture;
4. card click candidate generation;
5. card click sequence;
6. URL/currentJobId capture;
7. detail text capture with Ctrl+A/Ctrl+C;
8. duplicate/status diagnostics;
9. scroll/pagination/stop handling.

Phase 18A also adds full diagnostics visibility in the UI and a no-click mouse-control test. The next debugging target is live validation of the estimated card coordinates versus the browser's left result panel. Pixel-perfect legacy screenshot rectangle detection and annotated screenshots remain deferred.

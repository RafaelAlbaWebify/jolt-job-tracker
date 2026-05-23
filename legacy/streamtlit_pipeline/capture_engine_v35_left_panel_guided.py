"""
LinkedIn Visual currentJobId capture v35.7/v20 - fixed raw summary crash
-----------------------------------------------------------

Purpose:
- Reset the LinkedIn left job list to the top.
- Detect visible job cards.
- Click each FULL visible card.
- Read the browser URL.
- Extract currentJobId from the URL.
- Drag the left-panel scrollbar down.
- Repeat until pagination/footer is visible and every card above it is FULL.

Important:
- No job-description parsing.
- No title/company extraction.
- No ATS/job-fit analysis.
- Multi-page navigation uses the visible footer Next control, not constructed start= URLs.
- Identity comes only from currentJobId in the URL.

Output:
- captures_id/linkedin_job_ids_v34_<timestamp>.md
- captures_id/linkedin_job_ids_v34_<timestamp>.csv
- debug_outputs/v29 annotated screenshots
"""

from __future__ import annotations

import csv
import json
import datetime as dt
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

try:
    import pyautogui
except ModuleNotFoundError:
    print("Missing dependency: pyautogui")
    print("Install it with: pip install pyautogui")
    sys.exit(1)

try:
    import win32con
    import win32gui
    import win32clipboard
except ModuleNotFoundError:
    print("Missing dependency: pywin32")
    print("Install it with: pip install pywin32")
    sys.exit(1)

try:
    from PIL import Image, ImageDraw, ImageFont
except ModuleNotFoundError:
    print("Missing dependency: Pillow")
    print("Install it with: pip install pillow")
    sys.exit(1)


COUNTDOWN_SECONDS = 6

DEBUG_OUTPUT_DIR = Path("debug_outputs")
CAPTURE_OUTPUT_DIR = Path("captures_id")
LOG_OUTPUT_DIR = Path("logs")
DIAG_TEXT_LOG_PATH: Optional[Path] = None
DIAG_JSONL_LOG_PATH: Optional[Path] = None


DEFAULT_PAGES_TO_CAPTURE = 2
RESULTS_PER_PAGE = 25
MAX_VIEWPORTS = 30
NO_MOVEMENT_LIMIT = 2
MIN_UNIQUE_TO_ALLOW_RELAXED_NEXT = 20
MIN_LEFT_PANEL_SIGNATURES_TO_ALLOW_RELAXED_NEXT = 20

INITIAL_DRAG_PX = 85
MAX_DRAG_PX = 120
MIN_DRAG_PX = 55
DRAG_WAIT_SECONDS = 1.00
DRAG_DURATION_SECONDS = 0.20

RESET_TOP_EXTRA_MARGIN_PX = 6
FOOTER_TOP_PADDING = 18
FOOTER_MIN_Y_RATIO = 0.52

CLICK_WAIT_SECONDS = 0.45
COPY_WAIT_SECONDS = 0.25


class TeeStream:
    """Mirror stdout/stderr to console and a UTF-8 log file."""
    def __init__(self, original, log_file):
        self.original = original
        self.log_file = log_file

    def write(self, text: str) -> int:
        try:
            self.original.write(text)
        except Exception:
            pass
        try:
            self.log_file.write(text)
            self.log_file.flush()
        except Exception:
            pass
        return len(text)

    def flush(self) -> None:
        try:
            self.original.flush()
        except Exception:
            pass
        try:
            self.log_file.flush()
        except Exception:
            pass

    def isatty(self) -> bool:
        return False


def setup_diagnostic_logging(run_stamp: str) -> Tuple[Path, Path]:
    """Start persistent diagnostic logging for capture optimization."""
    global DIAG_TEXT_LOG_PATH, DIAG_JSONL_LOG_PATH
    LOG_OUTPUT_DIR.mkdir(exist_ok=True)
    DIAG_TEXT_LOG_PATH = LOG_OUTPUT_DIR / f"capture_diagnostic_v35_{run_stamp}.log"
    DIAG_JSONL_LOG_PATH = LOG_OUTPUT_DIR / f"capture_diagnostic_v35_{run_stamp}.jsonl"
    log_file = DIAG_TEXT_LOG_PATH.open("a", encoding="utf-8", buffering=1)
    sys.stdout = TeeStream(sys.stdout, log_file)  # type: ignore[assignment]
    sys.stderr = TeeStream(sys.stderr, log_file)  # type: ignore[assignment]
    diag_event("diagnostic_logging_started", text_log=str(DIAG_TEXT_LOG_PATH.resolve()), jsonl_log=str(DIAG_JSONL_LOG_PATH.resolve()))
    return DIAG_TEXT_LOG_PATH, DIAG_JSONL_LOG_PATH


def _diag_safe(value):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Rect):
        return {"left": value.left, "top": value.top, "right": value.right, "bottom": value.bottom, "width": value.width, "height": value.height}
    if isinstance(value, set):
        return sorted(list(value))[:200]
    if isinstance(value, (list, tuple)):
        return [_diag_safe(v) for v in value[:200]]
    if isinstance(value, dict):
        return {str(k): _diag_safe(v) for k, v in list(value.items())[:200]}
    return value


def diag_event(event: str, **fields) -> None:
    """Append structured JSON diagnostics; never crash capture."""
    if DIAG_JSONL_LOG_PATH is None:
        return
    try:
        payload = {"ts": dt.datetime.now().isoformat(timespec="milliseconds"), "event": event}
        payload.update({k: _diag_safe(v) for k, v in fields.items()})
        with DIAG_JSONL_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass

# v28: after the first viewport, only the lower/newly-revealed band is clicked.
# The top part of each new viewport is intentionally overlapping content from the
# previous viewport, so clicking it causes many duplicate job IDs.
NEWLY_REVEALED_BAND_RATIO = 0.10


# Phase 2 is intentionally slower. Direct URL navigation may update the URL before
# the right/details panel has finished rendering.
PHASE2_NAV_WAIT_SECONDS = 3.5
PHASE2_PANEL_READY_TIMEOUT_SECONDS = 18.0
PHASE2_PANEL_READY_POLL_SECONDS = 1.25
PHASE2_MIN_RAW_TEXT_CHARS = 1800
PHASE2_STABLE_TEXT_DELTA_CHARS = 250
PHASE2_REQUIRED_STABLE_POLLS = 2
PAGE_NAV_WAIT_SECONDS = 3.2
PAGE_READY_TIMEOUT_SECONDS = 16.0
PAGE_READY_POLL_SECONDS = 1.0


@dataclass(frozen=True)
class Rect:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def center_x(self) -> int:
        return (self.left + self.right) // 2

    @property
    def center_y(self) -> int:
        return (self.top + self.bottom) // 2

    def as_tuple(self) -> Tuple[int, int, int, int]:
        return (self.left, self.top, self.right, self.bottom)

    def describe(self) -> str:
        return f"L{self.left},T{self.top},R{self.right},B{self.bottom},W{self.width},H{self.height}"


@dataclass(frozen=True)
class TitleSignal:
    top: int
    bottom: int
    left: int
    right: int
    blue_pixels: int

    @property
    def center_x(self) -> int:
        return (self.left + self.right) // 2

    @property
    def center_y(self) -> int:
        return (self.top + self.bottom) // 2


@dataclass(frozen=True)
class Card:
    index: int
    rect: Rect
    title: TitleSignal
    click_x: int
    click_y: int
    confidence: float
    reason: str
    visibility: str
    fingerprint: str

    def describe(self) -> str:
        return (
            f"CARD {self.index:02d}: {self.visibility}, {self.rect.describe()}, "
            f"title_y={self.title.top}-{self.title.bottom}, click=({self.click_x},{self.click_y}), "
            f"fp={self.fingerprint[:16]}, confidence={self.confidence:.2f}, reason={self.reason}"
        )


@dataclass
class ViewportResult:
    viewport_index: int
    roi: Rect
    card_roi: Rect
    footer_rect: Optional[Rect]
    scrollbar_thumb: Optional[Rect]
    pagination_visible: bool
    cards: List[Card]
    title_signals: List[TitleSignal]
    annotated_path: Optional[Path]
    crop_path: Optional[Path]
    drag_px_used: int = 0
    thumb_before: Optional[Rect] = None
    thumb_after: Optional[Rect] = None
    thumb_delta_px: int = 0
    movement_status: str = ""
    stop_reason: str = ""


@dataclass
class IdRecord:
    sequence: int
    page_number: int
    page_start: int
    viewport_index: int
    card_index: int
    card_visibility: str
    click_x: int
    click_y: int
    current_job_id: str
    url: str
    status: str
    first_seen_sequence: int


@dataclass
class RawJobTextRecord:
    sequence: int
    source_sequence: int
    page_number: int
    page_start: int
    viewport_index: int
    card_index: int
    current_job_id: str
    url: str
    raw_text: str
    status: str
    ready_attempts: int




@dataclass(frozen=True)
class LeftPanelCard:
    title: str
    company: str
    location: str
    workplace_type: str
    state_text: str
    signature: str


LEFT_PANEL_STOP_MARKERS = {
    "are these results helpful?",
    "your feedback helps us improve job recommendations.",
    "are you finding what you're looking for? no are you finding what you're looking for? yes",
    "next",
    "about",
    "accessibility",
    "help center",
}
LEFT_PANEL_STATE_MARKERS = {
    "actively reviewing applicants",
    "viewed",
    "promoted",
    "easy apply",
    "be an early applicant",
    "applied",
    "company review time is typically 1 week",
}


def _clean_text_line(line: str) -> str:
    return re.sub(r"\s+", " ", (line or "").strip())


def _is_left_panel_location(line: str) -> bool:
    l = line.lower()
    return bool(re.search(r"\((remote|hybrid|on-site|onsite)\)", l)) or any(x in l for x in [
        "spain", "madrid", "barcelona", "lisbon", "portugal", "budapest", "hungary",
        "dublin", "ireland", "netherlands", "france", "amsterdam", "paris", "cork",
        "greater madrid", "metropolitan area", "community of madrid", "valencia", "zaragoza",
    ])


def normalize_card_signature(title: str, company: str, location: str) -> str:
    base = f"{company}|{title}|{location}"
    base = base.lower().replace("&", " and ")
    base = re.sub(r"[^a-z0-9áéíóúüñ]+", " ", base, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", base).strip()


def parse_left_panel_cards_from_text(raw_text: str) -> List[LeftPanelCard]:
    """Extract visible/DOM left-panel job cards from a Ctrl+A LinkedIn page text.

    This is used for coverage/audit and for safer page navigation. It deliberately
    avoids fixed card-height assumptions. It reads the text structure LinkedIn
    exposes during Ctrl+A:
      Company logo / Title / Company / Location (Remote/Hybrid/On-site) / states...
    """
    lines = [_clean_text_line(x) for x in (raw_text or "").splitlines()]
    lines = [x for x in lines if x]
    # Start after the results heading to avoid top nav/category chips.
    start = 0
    for i, line in enumerate(lines):
        if re.search(r"\b\d+\s+results\b", line.lower()):
            start = i + 1
            break
    out: List[LeftPanelCard] = []
    i = start
    while i < len(lines) - 3:
        cur = lines[i]
        lc = cur.lower()
        if lc in LEFT_PANEL_STOP_MARKERS or lc.startswith("are you finding what"):
            break
        if cur.endswith(" logo") and i + 3 < len(lines):
            title = lines[i + 1]
            company = lines[i + 2]
            location = lines[i + 3]
            if _is_left_panel_location(location):
                state_lines: List[str] = []
                j = i + 4
                while j < len(lines):
                    nxt = lines[j]
                    nl = nxt.lower()
                    if nxt.endswith(" logo") or nl in LEFT_PANEL_STOP_MARKERS or nl.startswith("are you finding what"):
                        break
                    # keep short status lines; avoid swallowing the right panel
                    if nl in LEFT_PANEL_STATE_MARKERS or "applicants" in nl or "review time" in nl or "school alumni" in nl:
                        state_lines.append(nxt)
                    elif len(state_lines) >= 1 and len(nxt) <= 45:
                        state_lines.append(nxt)
                    else:
                        # Unknown long line usually means card block ended.
                        pass
                    j += 1
                workplace = ""
                m = re.search(r"\((Remote|Hybrid|On-site|Onsite)\)", location, flags=re.IGNORECASE)
                if m:
                    workplace = m.group(1).replace("Onsite", "On-site")
                sig = normalize_card_signature(title, company, location)
                if sig and all(c.signature != sig for c in out):
                    out.append(LeftPanelCard(title=title, company=company, location=location, workplace_type=workplace, state_text="; ".join(dict.fromkeys(state_lines)), signature=sig))
                i = max(j, i + 4)
                continue
        i += 1
    return out


def collect_left_panel_card_signatures(hwnd: int) -> Tuple[List[LeftPanelCard], str]:
    raw = copy_visible_page_text_no_content_click(hwnd)
    cards = parse_left_panel_cards_from_text(raw)
    return cards, raw


@dataclass
class PageCaptureResult:
    sequence: int
    last_valid_job_id: str
    status: str
    stop_reason: str
    records_added: int
    unique_added: int
    duplicates_added: int
    failures_added: int
    viewports_scanned: int
    allow_next_page: bool


def is_failure_status(status: str) -> bool:
    if status == "OK_NEW" or status.startswith("DUPLICATE"):
        return False
    if status.startswith("BOUNDARY_OVERLAP"):
        return False
    return True


def timestamp() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def get_font(size: int = 14):
    for font_name in ("arial.ttf", "segoeui.ttf", "calibri.ttf"):
        try:
            return ImageFont.truetype(font_name, size)
        except Exception:
            pass
    return ImageFont.load_default()


def get_window_from_mouse() -> Tuple[int, str, Rect, Tuple[int, int]]:
    mouse_x, mouse_y = pyautogui.position()
    hwnd = win32gui.WindowFromPoint((mouse_x, mouse_y))
    root = win32gui.GetAncestor(hwnd, win32con.GA_ROOT)
    if root:
        hwnd = root
    title = win32gui.GetWindowText(hwnd)
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    return hwnd, title, Rect(left, top, right, bottom), (mouse_x, mouse_y)


def force_foreground(hwnd: int) -> None:
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.25)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.25)
    except Exception:
        pass


def get_clipboard_text() -> str:
    text = ""
    try:
        win32clipboard.OpenClipboard()
        try:
            if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                text = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
        finally:
            win32clipboard.CloseClipboard()
    except Exception:
        return ""
    return text or ""


def clear_clipboard_text() -> None:
    try:
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
        finally:
            win32clipboard.CloseClipboard()
    except Exception:
        pass


def copy_visible_page_text_no_content_click(hwnd: int) -> str:
    """
    Copy browser-visible page text without clicking inside LinkedIn content.
    Used only in Phase 2, after all IDs/URLs are already captured.
    """
    force_foreground(hwnd)
    pyautogui.press("esc")
    time.sleep(0.15)

    clear_clipboard_text()
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.18)
    pyautogui.hotkey("ctrl", "c")
    time.sleep(0.55)

    raw = get_clipboard_text().strip()
    pyautogui.press("esc")
    time.sleep(0.12)
    return raw


def raw_text_has_job_panel(raw_text: str) -> bool:
    if not raw_text:
        return False

    low = raw_text.lower()
    markers = [
        "about the job",
        "apply",
        "save",
        "job",
        "applicants",
        "skills match",
        "people you can reach out to",
    ]
    marker_hits = sum(1 for m in markers if m in low)
    return len(raw_text) >= PHASE2_MIN_RAW_TEXT_CHARS and marker_hits >= 2


def wait_for_job_url_and_panel_text(
    hwnd: int,
    expected_job_id: str,
    expected_url: str,
) -> Tuple[str, str, str, int]:
    deadline = time.time() + PHASE2_PANEL_READY_TIMEOUT_SECONDS
    attempts = 0
    last_good_text = ""
    last_len = -1
    stable_count = 0
    last_url = ""

    while time.time() < deadline:
        attempts += 1

        last_url = copy_current_url(hwnd)
        current_job_id = extract_current_job_id(last_url)

        if current_job_id != expected_job_id:
            print(
                f"  Panel-ready check {attempts}: URL mismatch "
                f"expected={expected_job_id}, got={current_job_id or 'none'}"
            )
            time.sleep(PHASE2_PANEL_READY_POLL_SECONDS)
            continue

        raw = copy_visible_page_text_no_content_click(hwnd)
        raw_len = len(raw)
        looks_ready = raw_text_has_job_panel(raw)

        if looks_ready:
            if last_len >= 0 and abs(raw_len - last_len) <= PHASE2_STABLE_TEXT_DELTA_CHARS:
                stable_count += 1
            else:
                stable_count = 1

            last_good_text = raw
            last_len = raw_len

            print(
                f"  Panel-ready check {attempts}: chars={raw_len}, "
                f"looks_ready=yes, stable={stable_count}/{PHASE2_REQUIRED_STABLE_POLLS}"
            )

            if stable_count >= PHASE2_REQUIRED_STABLE_POLLS:
                return "OK_RAW_TEXT", last_url, last_good_text, attempts
        else:
            stable_count = 0
            last_len = raw_len
            print(f"  Panel-ready check {attempts}: chars={raw_len}, looks_ready=no")

        time.sleep(PHASE2_PANEL_READY_POLL_SECONDS)

    print("  Panel not ready in time. Reloading expected job URL once...")
    navigate_to_url(hwnd, expected_url)
    time.sleep(PHASE2_NAV_WAIT_SECONDS)

    final_url = copy_current_url(hwnd)
    final_job_id = extract_current_job_id(final_url)
    raw = copy_visible_page_text_no_content_click(hwnd)

    if final_job_id == expected_job_id and raw_text_has_job_panel(raw):
        return "OK_RAW_TEXT_AFTER_RELOAD", final_url, raw, attempts + 1

    if final_job_id != expected_job_id:
        return "URL_JOB_ID_MISMATCH", final_url, raw, attempts + 1

    if not raw:
        return "EMPTY_RAW_TEXT", final_url, raw, attempts + 1

    return "RAW_TEXT_NOT_READY", final_url, raw, attempts + 1


def copy_current_url(hwnd: int) -> str:
    """Copy Chrome's current address bar URL with retries.

    v24: remote-jobs collection exposed a failure where the initial URL copy
    returned an empty string. That made base_results_url empty and page 2 direct
    navigation failed before capture. This helper now clears the clipboard,
    tries both Ctrl+L and Alt+D, validates LinkedIn/HTTP-looking output, and
    retries before returning.
    """
    methods = [("ctrl", "l"), ("alt", "d"), ("ctrl", "l")]
    last = ""
    for method in methods:
        try:
            force_foreground(hwnd)
            time.sleep(0.10)
            clear_clipboard_text()
            pyautogui.hotkey(*method)
            time.sleep(0.18)
            pyautogui.hotkey("ctrl", "c")
            time.sleep(max(COPY_WAIT_SECONDS, 0.28))
            url = get_clipboard_text().strip()
            last = url or last
            pyautogui.press("esc")
            time.sleep(0.08)
            if url.startswith("http") and "linkedin.com/jobs" in url:
                return url
        except Exception:
            try:
                pyautogui.press("esc")
            except Exception:
                pass
            time.sleep(0.12)
    return last


def extract_current_job_id(url: str) -> str:
    match = re.search(r"[?&]currentJobId=(\d+)", url)
    if match:
        return match.group(1)
    return ""


def extract_start_param(url: str) -> int:
    """Return the LinkedIn pagination start offset from the current URL, or 0.

This is metadata only; currentJobId remains the identity key. LinkedIn may use
start=24 or another offset depending on the actual result count/page layout.
"""
    try:
        parts = urlsplit(url)
        for key, value in parse_qsl(parts.query, keep_blank_values=True):
            if key == "start" and value.strip().isdigit():
                return int(value.strip())
    except Exception:
        pass
    return 0

def set_url_start(url: str, start: int, anchor_job_id: str = "") -> str:
    """
    Build a LinkedIn results URL for a specific start offset.

    For LinkedIn recommended jobs, keeping a currentJobId anchor can be necessary
    for the left results panel to render correctly after direct navigation.
    """
    parts = urlsplit(url)
    query_pairs = parse_qsl(parts.query, keep_blank_values=True)

    filtered = []
    had_current_job_id = False

    for key, value in query_pairs:
        if key == "start":
            continue
        if key == "currentJobId":
            had_current_job_id = True
            filtered.append(("currentJobId", anchor_job_id or value))
            continue
        filtered.append((key, value))

    if anchor_job_id and not had_current_job_id:
        filtered.insert(0, ("currentJobId", anchor_job_id))

    if start > 0:
        filtered.append(("start", str(start)))

    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(filtered, doseq=True), parts.fragment))




def set_url_start_for_results_page(url: str, start: int) -> str:
    """Build a LinkedIn results-page URL for a target page start.

    v15 deliberately removes currentJobId for page transitions. Keeping an
    already-selected job ID can leave the left results list on the old page or
    make LinkedIn preserve the previous selection while the script believes it
    moved to the next page. The job ID remains the identity key during capture;
    this helper is only for navigating the results list.
    """
    parts = urlsplit(url)
    query_pairs = parse_qsl(parts.query, keep_blank_values=True)
    filtered = []
    for key, value in query_pairs:
        if key in {"start", "currentJobId"}:
            continue
        filtered.append((key, value))
    if start > 0:
        filtered.append(("start", str(start)))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(filtered, doseq=True), parts.fragment))


def left_panel_signature_set(hwnd: int) -> set[str]:
    try:
        cards, _raw = collect_left_panel_card_signatures(hwnd)
        return {c.signature for c in cards if c.signature}
    except Exception:
        return set()


def signature_overlap_ratio(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / max(1, min(len(a), len(b)))

def navigate_to_url(hwnd: int, url: str) -> None:
    force_foreground(hwnd)
    pyautogui.hotkey("ctrl", "l")
    time.sleep(0.12)
    pyautogui.write(url, interval=0.001)
    pyautogui.press("enter")
    time.sleep(PAGE_NAV_WAIT_SECONDS)




def estimate_left_panel_roi(window: Rect, mouse_xy: Tuple[int, int], screenshot_size: Tuple[int, int]) -> Rect:
    sw, sh = screenshot_size
    mx, _ = mouse_xy

    # v22 ROI guard:
    # Previous versions used mouse_x + 70 and a minimum width of 360 px.
    # That was too sensitive to the exact cursor placement. In a real failure
    # the ROI ended at R496 while the scrollbar area was around x509-518, so
    # cards were detected but the scrollbar was outside the scan region.
    # Keep the cursor hint, but guarantee enough width to include the left-list
    # scrollbar on the common LinkedIn Jobs layout.
    left = max(0, window.left + int(window.width * 0.09))
    mouse_right = mx + 120
    min_right = left + 440
    max_right = window.left + int(window.width * 0.52)
    right = min(max(mouse_right, min_right), max_right, sw)

    top = max(0, window.top + int(window.height * 0.21))
    bottom = min(sh, window.bottom - int(window.height * 0.05))
    return Rect(left, top, right, bottom)


# v23 visual-anchor geometry -------------------------------------------------
# The earlier ROI used the initial mouse position as a hint. That is useful,
# but not reliable enough: if the computed right edge lands on the scrollbar
# itself, the strict scrollbar detector can reject it. The browser screenshot
# already contains better anchors: the left-list scrollbar rail/thumb and its
# top/bottom arrow markers. v23 detects that rail first, then derives two ROIs:
#   - panel_roi: includes the scrollbar and footer/pagination controls.
#   - content_roi: stops before the scrollbar so job-card detection does not
#                  leak into the right job-detail panel.

def _is_neutral_scroll_pixel(r: int, g: int, b: int) -> bool:
    if max(r, g, b) - min(r, g, b) > 26:
        return False
    return 70 <= r <= 215 and 70 <= g <= 215 and 70 <= b <= 215


def _longest_true_run(flags: List[bool]) -> int:
    best = cur = 0
    for flag in flags:
        if flag:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def detect_left_panel_scrollbar_rail(img: Image.Image, window: Rect) -> Optional[Rect]:
    """Detect the vertical scrollbar rail/thumb of the LinkedIn left jobs list.

    This deliberately scans the full screenshot/window, not the estimated ROI.
    It looks for a narrow, right-side neutral-grey vertical cluster inside the
    expected left-list band. It works whether the thumb is near the top, middle,
    or bottom of the list.
    """
    rgb = img.convert("RGB")
    px = rgb.load()
    sw, sh = img.size

    # Candidate band: right edge of the left jobs list, but before the job detail panel.
    band_left = max(0, window.left + int(window.width * 0.34))
    band_right = min(sw - 1, window.left + int(window.width * 0.50))
    scan_top = max(0, window.top + int(window.height * 0.22))
    scan_bottom = min(sh - 1, window.bottom - int(window.height * 0.03))

    columns = []
    for x in range(band_left, band_right):
        flags = []
        neutral_count = 0
        for y in range(scan_top, scan_bottom):
            r, g, b = px[x, y]
            hit = _is_neutral_scroll_pixel(r, g, b)
            flags.append(hit)
            neutral_count += 1 if hit else 0
        longest = _longest_true_run(flags)
        # Thumb columns usually have a long neutral run; top/bottom arrow markers
        # add more evidence when the thumb is at an extreme.
        if longest >= 35 and neutral_count >= 45:
            columns.append((x, neutral_count, longest))

    if not columns:
        return None

    # Group adjacent candidate columns.
    groups = []
    cur = [columns[0]]
    for col in columns[1:]:
        if col[0] <= cur[-1][0] + 2:
            cur.append(col)
        else:
            groups.append(cur)
            cur = [col]
    groups.append(cur)

    plausible = []
    for group in groups:
        x1 = group[0][0]
        x2 = group[-1][0] + 1
        width = x2 - x1
        score = sum(c[1] for c in group) + 5 * sum(c[2] for c in group)
        cx = (x1 + x2) // 2
        # Avoid thin text/vertical artifacts; prefer a narrow rail near the panel edge.
        if 3 <= width <= 24:
            plausible.append((score + cx * 2, Rect(x1, scan_top, x2, scan_bottom)))

    if not plausible:
        return None

    plausible.sort(key=lambda item: item[0], reverse=True)
    return plausible[0][1]


def estimate_left_panel_rois(window: Rect, mouse_xy: Tuple[int, int], img: Image.Image) -> Tuple[Rect, Rect, str]:
    """Return (panel_roi, content_roi, geometry_note)."""
    sw, sh = img.size
    baseline = estimate_left_panel_roi(window, mouse_xy, img.size)
    rail = detect_left_panel_scrollbar_rail(img, window)

    if rail:
        left = max(0, window.left + int(window.width * 0.09))
        top = max(0, window.top + int(window.height * 0.21))
        bottom = min(sh, window.bottom - int(window.height * 0.05))

        # Include the rail and a small safety margin in panel_roi.
        panel_right = min(sw, rail.right + 18)
        # Keep content/card detection before the rail so right-panel blue buttons
        # cannot be misclassified as job titles.
        content_right = max(left + 300, rail.left - 10)
        panel_roi = Rect(left, top, panel_right, bottom)
        content_roi = Rect(left, top, min(content_right, panel_right), bottom)
        return panel_roi, content_roi, f"visual_rail={rail.describe()}"

    # Fallback: use the guarded baseline ROI from v22, but derive a conservative
    # content area from it to reduce leakage into the right job-detail panel.
    content_right = max(baseline.left + 300, baseline.right - 45)
    content_roi = Rect(baseline.left, baseline.top, min(content_right, baseline.right), baseline.bottom)
    return baseline, content_roi, "visual_rail=none_fallback_v22"


def detect_scrollbar_thumb_flexible(img: Image.Image, roi: Rect) -> Optional[Rect]:
    """More tolerant scrollbar detector for the v23 panel ROI.

    The original detector rejected thumbs too close to roi.right. That was one
    of the concrete causes of the R496 failure. This detector scans only the
    rightmost part of panel_roi and allows the thumb to sit very close to the
    edge.
    """
    rgb = img.convert("RGB")
    px = rgb.load()
    scan_left = max(roi.left, roi.right - 42)
    scan_right = max(scan_left + 1, roi.right - 1)
    scan_top = roi.top + 10
    scan_bottom = roi.bottom - 10

    candidates: List[Rect] = []
    for x in range(scan_left, scan_right):
        in_run = False
        run_start = scan_top
        for y in range(scan_top, scan_bottom):
            r, g, b = px[x, y]
            hit = _is_neutral_scroll_pixel(r, g, b)
            if hit and not in_run:
                in_run = True
                run_start = y
            elif not hit and in_run:
                if y - run_start >= 35:
                    candidates.append(Rect(x, run_start, x + 1, y))
                in_run = False
        if in_run and scan_bottom - run_start >= 35:
            candidates.append(Rect(x, run_start, x + 1, scan_bottom))

    if not candidates:
        return None

    merged: List[Rect] = []
    for cand in sorted(candidates, key=lambda r: (r.left, r.top)):
        if not merged:
            merged.append(cand)
            continue
        last = merged[-1]
        y_overlap = min(last.bottom, cand.bottom) - max(last.top, cand.top)
        similar_y = y_overlap >= min(last.height, cand.height) * 0.50
        adjacent_x = cand.left <= last.right + 2
        if adjacent_x and similar_y:
            merged[-1] = Rect(min(last.left, cand.left), min(last.top, cand.top), max(last.right, cand.right), max(last.bottom, cand.bottom))
        else:
            merged.append(cand)

    plausible = [r for r in merged if 2 <= r.width <= 26 and r.height >= 35]
    if not plausible:
        return None
    plausible.sort(key=lambda r: (r.height * 5 + r.center_x), reverse=True)
    return plausible[0]


def is_linkedin_blue(r: int, g: int, b: int) -> bool:
    return b >= 105 and g >= 55 and r <= 115 and (b - r) >= 35 and (b - g) >= -5


def is_dark_active_page_pixel(r: int, g: int, b: int) -> bool:
    return r < 55 and g < 55 and b < 55


def detect_pagination_footer(img: Image.Image, roi: Rect) -> Optional[Rect]:
    rgb = img.convert("RGB")
    px = rgb.load()
    scan_top = roi.top + int(roi.height * FOOTER_MIN_Y_RATIO)
    row_hits = []

    for y in range(scan_top, roi.bottom):
        xs = []
        for x in range(roi.left + 15, roi.right - 15):
            r, g, b = px[x, y]
            if is_dark_active_page_pixel(r, g, b):
                xs.append(x)
        if len(xs) >= 8:
            row_hits.append((y, min(xs), max(xs), len(xs)))

    if not row_hits:
        return None

    groups = []
    cur = [row_hits[0]]
    for row in row_hits[1:]:
        if row[0] - cur[-1][0] <= 2:
            cur.append(row)
        else:
            groups.append(cur)
            cur = [row]
    groups.append(cur)

    candidates = []
    for group in groups:
        y1, y2 = group[0][0], group[-1][0]
        x1, x2 = min(r[1] for r in group), max(r[2] for r in group)
        w, h = x2 - x1 + 1, y2 - y1 + 1
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        if 12 <= w <= 42 and 12 <= h <= 42 and cy >= scan_top and roi.left + 70 <= cx <= roi.right - 70:
            candidates.append(Rect(roi.left, max(roi.top, y1 - 28), roi.right, roi.bottom))

    if not candidates:
        return None
    candidates.sort(key=lambda r: r.top)
    return candidates[0]


def effective_card_roi(roi: Rect, footer_rect: Optional[Rect]) -> Rect:
    if not footer_rect:
        return roi
    new_bottom = max(roi.top + 120, footer_rect.top - FOOTER_TOP_PADDING)
    return Rect(roi.left, roi.top, roi.right, min(roi.bottom, new_bottom))


def is_scrollbar_thumb_pixel(r: int, g: int, b: int) -> bool:
    if not (80 <= r <= 190 and 80 <= g <= 190 and 80 <= b <= 190):
        return False
    if max(r, g, b) - min(r, g, b) > 28:
        return False
    return True


def detect_scrollbar_thumb(img: Image.Image, roi: Rect) -> Optional[Rect]:
    rgb = img.convert("RGB")
    px = rgb.load()

    scan_left = roi.left + int(roi.width * 0.58)
    scan_right = roi.right - 4
    scan_top = roi.top + 20
    scan_bottom = roi.bottom - 20

    candidates: List[Rect] = []

    for x in range(scan_left, scan_right):
        in_run = False
        run_start = scan_top

        for y in range(scan_top, scan_bottom):
            r, g, b = px[x, y]
            hit = is_scrollbar_thumb_pixel(r, g, b)
            if hit and not in_run:
                in_run = True
                run_start = y
            elif not hit and in_run:
                if y - run_start >= 35:
                    candidates.append(Rect(x, run_start, x + 1, y))
                in_run = False

        if in_run and scan_bottom - run_start >= 35:
            candidates.append(Rect(x, run_start, x + 1, scan_bottom))

    if not candidates:
        return None

    candidates.sort(key=lambda r: (r.left, r.top))
    merged: List[Rect] = []

    for cand in candidates:
        if not merged:
            merged.append(cand)
            continue
        last = merged[-1]
        y_overlap = min(last.bottom, cand.bottom) - max(last.top, cand.top)
        similar_y = y_overlap >= min(last.height, cand.height) * 0.55
        adjacent_x = cand.left <= last.right + 2
        if adjacent_x and similar_y:
            merged[-1] = Rect(
                min(last.left, cand.left),
                min(last.top, cand.top),
                max(last.right, cand.right),
                max(last.bottom, cand.bottom),
            )
        else:
            merged.append(cand)

    plausible = []
    for r in merged:
        if 3 <= r.width <= 22 and r.height >= 45:
            if roi.left + int(roi.width * 0.58) <= r.center_x <= roi.right - 8:
                plausible.append(r)

    if not plausible:
        return None

    def score(r: Rect) -> int:
        return r.height * 4 + r.center_x - abs(r.width - 8) * 20

    plausible.sort(key=score, reverse=True)
    return plausible[0]


def detect_blue_title_signals(img: Image.Image, roi: Rect) -> List[TitleSignal]:
    rgb = img.convert("RGB")
    px = rgb.load()
    scan_left = roi.left + int(roi.width * 0.14)
    scan_right = roi.right - int(roi.width * 0.06)
    active_rows = []

    for y in range(roi.top, roi.bottom):
        count, min_x, max_x = 0, 10**9, -1
        for x in range(scan_left, scan_right):
            r, g, b = px[x, y]
            if is_linkedin_blue(r, g, b):
                count += 1
                min_x = min(min_x, x)
                max_x = max(max_x, x)
        if count >= 7 and max_x > min_x:
            active_rows.append((y, min_x, max_x, count))

    if not active_rows:
        return []

    groups = []
    current = [active_rows[0]]
    for row in active_rows[1:]:
        if row[0] - current[-1][0] <= 3:
            current.append(row)
        else:
            groups.append(current)
            current = [row]
    groups.append(current)

    signals = []
    for group in groups:
        y1, y2 = group[0][0], group[-1][0]
        x1, x2 = min(r[1] for r in group), max(r[2] for r in group)
        blue_pixels = sum(r[3] for r in group)
        h, w = y2 - y1 + 1, x2 - x1 + 1
        if h < 4 or h > 42:
            continue
        if w < 45 and blue_pixels < 90:
            continue
        if blue_pixels < 65:
            continue
        signals.append(TitleSignal(y1, y2, x1, x2, blue_pixels))

    signals = sorted(signals, key=lambda s: s.top)
    merged = []
    for sig in signals:
        if not merged:
            merged.append(sig)
            continue
        last = merged[-1]
        vertical_gap = sig.top - last.bottom
        horizontal_overlap = not (sig.right < last.left - 30 or sig.left > last.right + 30)
        if vertical_gap <= 16 and horizontal_overlap:
            merged[-1] = TitleSignal(
                top=last.top,
                bottom=sig.bottom,
                left=min(last.left, sig.left),
                right=max(last.right, sig.right),
                blue_pixels=last.blue_pixels + sig.blue_pixels,
            )
        else:
            merged.append(sig)

    deduped = []
    for sig in merged:
        if deduped and sig.top - deduped[-1].top < 36:
            if sig.blue_pixels > deduped[-1].blue_pixels:
                deduped[-1] = sig
        else:
            deduped.append(sig)
    return deduped


def card_visibility(rect: Rect, roi: Rect) -> str:
    if rect.top < roi.top + 28:
        return "PARTIAL_TOP"
    if rect.bottom > roi.bottom - 35:
        return "PARTIAL_BOTTOM"
    if rect.height < 58:
        return "PARTIAL_SHORT"
    return "FULL"


def average_hash(img: Image.Image, size: Tuple[int, int] = (24, 12)) -> str:
    gray = img.convert("L").resize(size)
    values = list(gray.getdata())
    avg = sum(values) / len(values)
    bits = ''.join('1' if v < avg else '0' for v in values)
    return f"{int(bits, 2):0{len(bits)//4}x}"


def fingerprint_card(img: Image.Image, roi: Rect, rect: Rect, title: TitleSignal) -> str:
    left = max(roi.left, rect.left + 8)
    top = max(roi.top, title.top - 20)
    right = min(roi.right, rect.right - 18)
    bottom = min(roi.bottom, title.bottom + 90)
    if right <= left or bottom <= top:
        return "bad-fingerprint"
    return average_hash(img.crop((left, top, right, bottom)), (24, 12))


def build_cards_from_title_signals(img: Image.Image, roi: Rect, title_signals: List[TitleSignal]) -> List[Card]:
    if not title_signals:
        return []

    title_signals = sorted(title_signals, key=lambda s: s.center_y)
    centers = [s.center_y for s in title_signals]
    cards = []

    for i, sig in enumerate(title_signals):
        if i == 0:
            if len(centers) >= 2:
                top = max(roi.top, centers[0] - int((centers[1] - centers[0]) * 0.50))
            else:
                top = max(roi.top, sig.top - 45)
        else:
            top = (centers[i - 1] + centers[i]) // 2

        if i == len(title_signals) - 1:
            if len(centers) >= 2:
                bottom = min(roi.bottom, centers[-1] + int((centers[-1] - centers[-2]) * 0.55))
            else:
                bottom = min(roi.bottom, sig.bottom + 60)
        else:
            bottom = (centers[i] + centers[i + 1]) // 2

        if bottom - top < 48:
            bottom = min(roi.bottom, top + 58)
        if bottom - top > 155:
            bottom = top + 135
        if bottom <= top:
            continue

        rect = Rect(roi.left + 4, top, roi.right - 4, min(bottom, roi.bottom))
        click_x = max(rect.left + 85, min(sig.center_x, rect.right - 40))
        click_y = sig.center_y
        visibility = card_visibility(rect, roi)
        fp = fingerprint_card(img, roi, rect, sig)
        confidence = 0.80 if sig.blue_pixels >= 150 else 0.72

        cards.append(Card(len(cards) + 1, rect, sig, click_x, click_y, confidence, "title-blue-signal", visibility, fp))
    return cards


def annotate_image(img, roi, card_roi, footer_rect, scrollbar_thumb, cards, title_signals, note=""):
    out = img.copy().convert("RGB")
    draw = ImageDraw.Draw(out)
    font = get_font(14)
    small = get_font(12)

    draw.rectangle(roi.as_tuple(), outline=(255, 0, 0), width=3)
    draw.text((roi.left + 6, roi.top + 6), f"LEFT PANEL ROI {note}", fill=(255, 0, 0), font=font)

    if footer_rect:
        draw.rectangle(footer_rect.as_tuple(), outline=(180, 0, 255), width=4)
        draw.text((footer_rect.left + 6, footer_rect.top + 6), "PAGINATION / FOOTER DETECTED", fill=(180, 0, 255), font=font)

    if scrollbar_thumb:
        draw.rectangle(scrollbar_thumb.as_tuple(), outline=(0, 255, 255), width=5)
        draw.text((max(0, scrollbar_thumb.left - 140), scrollbar_thumb.top), "SCROLLBAR THUMB", fill=(0, 170, 170), font=small)

    draw.rectangle(card_roi.as_tuple(), outline=(0, 180, 0), width=2)

    for i, sig in enumerate(title_signals, start=1):
        draw.rectangle((sig.left, sig.top, sig.right, sig.bottom), outline=(0, 120, 255), width=2)
        draw.text((sig.left, max(0, sig.top - 14)), f"T{i:02d}", fill=(0, 120, 255), font=small)

    for card in cards:
        outline = (255, 230, 0) if card.visibility == "FULL" else (255, 128, 0)
        r = card.rect
        draw.rectangle(r.as_tuple(), outline=outline, width=3)
        draw.ellipse((card.click_x - 5, card.click_y - 5, card.click_x + 5, card.click_y + 5), fill=(255, 0, 0))
        draw.text((r.left + 6, r.top + 6), f"CARD {card.index:02d} {card.visibility}", fill=(255, 0, 0), font=small)

    return out


def capture_and_detect(hwnd, window_rect, mouse_xy, viewport_index, output_dir, run_stamp, save_images=True, note="") -> ViewportResult:
    force_foreground(hwnd)
    screenshot = pyautogui.screenshot()
    if not isinstance(screenshot, Image.Image):
        screenshot = Image.frombytes("RGB", screenshot.size, screenshot.tobytes())

    roi, base_card_roi, geometry_note = estimate_left_panel_rois(window_rect, mouse_xy, screenshot)
    footer_rect = detect_pagination_footer(screenshot, roi)
    card_roi = effective_card_roi(base_card_roi, footer_rect)
    scrollbar_thumb = detect_scrollbar_thumb(screenshot, roi)
    if scrollbar_thumb is None:
        scrollbar_thumb = detect_scrollbar_thumb_flexible(screenshot, roi)
    title_signals = detect_blue_title_signals(screenshot, card_roi)
    cards = build_cards_from_title_signals(screenshot, card_roi, title_signals)

    annotated_path = None
    crop_path = None
    if save_images:
        suffix = f"viewport_{viewport_index:02d}"
        if note:
            safe_note = ''.join(ch if ch.isalnum() or ch in ('_', '-') else '_' for ch in note.lower())
            suffix = f"{safe_note}_{suffix}"
        combined_note = (note + " " + geometry_note).strip()
        annotated = annotate_image(screenshot, roi, card_roi, footer_rect, scrollbar_thumb, cards, title_signals, note=combined_note)
        annotated_path = output_dir / f"id_capture_v26_{run_stamp}_{suffix}_annotated.png"
        crop_path = output_dir / f"id_capture_v26_{run_stamp}_{suffix}_crop.png"
        annotated.save(annotated_path)
        screenshot.crop(roi.as_tuple()).save(crop_path)

    return ViewportResult(
        viewport_index=viewport_index,
        roi=roi,
        card_roi=card_roi,
        footer_rect=footer_rect,
        scrollbar_thumb=scrollbar_thumb,
        pagination_visible=footer_rect is not None,
        cards=cards,
        title_signals=title_signals,
        annotated_path=annotated_path,
        crop_path=crop_path,
    )


def full_cards(r: ViewportResult) -> List[Card]:
    return [c for c in r.cards if c.visibility == "FULL"]


def partial_cards(r: ViewportResult) -> List[Card]:
    return [c for c in r.cards if c.visibility != "FULL"]


def clickable_cards_for_viewport(r: ViewportResult) -> List[Card]:
    """Return cards safe enough to click.

    v14 change:
    The first/top card can be detected as PARTIAL_TOP because LinkedIn's result
    header overlaps the card area. In previous versions that caused the first
    visible offer (often the selected/top recommendation) to be skipped. If the
    title and click point are clearly inside the safe card ROI, click it once and
    let currentJobId/global de-dupe protect us.

    Final pagination/footer rule:
    If the footer is visible, a bottom card can be marked PARTIAL_BOTTOM only
    because the footer reduced the safe card ROI. If its click point is still
    clearly above the footer, it is safe and desirable to click it once before
    stopping.
    """
    cards = full_cards(r)
    existing_keys = {(c.click_x, c.click_y, c.index) for c in cards}

    # v14: recover safe top cards that were previously missed.
    for c in r.cards:
        if c.visibility != "PARTIAL_TOP":
            continue
        safe_top = r.card_roi.top + 10
        if c.click_y > safe_top and c.title.center_y > safe_top and c.rect.bottom > safe_top + 45:
            key = (c.click_x, c.click_y, c.index)
            if key not in existing_keys:
                cards.append(c)
                existing_keys.add(key)

    if r.pagination_visible and r.footer_rect:
        safe_bottom = r.footer_rect.top - 18
        for c in r.cards:
            if c.visibility != "PARTIAL_BOTTOM":
                continue
            if c.click_y < safe_bottom and c.title.center_y < safe_bottom and c.rect.top < safe_bottom - 35:
                key = (c.click_x, c.click_y, c.index)
                if key not in existing_keys:
                    cards.append(c)
                    existing_keys.add(key)

    return sorted(cards, key=lambda c: (c.rect.top, c.index))


def capture_candidates_for_viewport(r: ViewportResult, viewport_index: int) -> Tuple[List[Card], int, int]:
    """Return cards to click for this viewport.

    v28 strategy:
    - Viewport 1: click all full/safe cards.
    - Viewport 2+: click only the lower newly-revealed band. The upper band is
      expected overlap from the previous viewport and was responsible for most
      duplicate clicks in v24/v25.

    Returns: (filtered_cards, raw_candidate_count, top_overlap_skipped_count)
    """
    raw = clickable_cards_for_viewport(r)
    if viewport_index <= 1:
        return raw, len(raw), 0

    cutoff_y = r.card_roi.top + int(r.card_roi.height * NEWLY_REVEALED_BAND_RATIO)
    filtered = []
    skipped = 0
    for c in raw:
        # Use the title center first because it is the most stable part of the card.
        # click_y is kept as a fallback for unusual card geometry.
        if c.title.center_y >= cutoff_y or c.click_y >= cutoff_y:
            filtered.append(c)
        else:
            skipped += 1
    return filtered, len(raw), skipped


def page_complete_by_pagination(r: ViewportResult) -> bool:
    return r.pagination_visible and len(partial_cards(r)) == 0


def viewport_fingerprint_set(r: ViewportResult) -> set:
    return {c.fingerprint for c in clickable_cards_for_viewport(r) if c.fingerprint and c.fingerprint != "bad-fingerprint"}


def fingerprint_overlap_ratio(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / max(1, min(len(a), len(b)))


def scrollbar_near_bottom(r: ViewportResult) -> bool:
    return bool(r.scrollbar_thumb and r.scrollbar_thumb.bottom >= r.roi.bottom - 24)


def calculate_drag_px(result: ViewportResult, last_unique_count: int) -> int:
    # v28: controlled scroll. The old fixed 260 px drag was too aggressive and
    # sometimes jumped over cards or bounced near the footer. A smaller thumb drag
    # gives deliberate overlap; duplicate clicks are controlled by card fingerprints.
    if not result.scrollbar_thumb:
        return INITIAL_DRAG_PX
    base = int(result.scrollbar_thumb.height * 0.62)
    if last_unique_count <= 1:
        base = int(base * 0.85)
    return max(MIN_DRAG_PX, min(MAX_DRAG_PX, base))


def drag_scrollbar_to_top(result: ViewportResult):
    thumb = result.scrollbar_thumb
    if thumb is None:
        return "NO_SCROLLBAR_THUMB_DETECTED", 0

    start_x = thumb.center_x
    start_y = thumb.center_y
    target_y = max(result.roi.top + 25, thumb.height // 2 + result.roi.top + RESET_TOP_EXTRA_MARGIN_PX)
    actual = target_y - start_y

    if abs(actual) <= 8:
        return "ALREADY_NEAR_TOP", 0

    pyautogui.moveTo(start_x, start_y, duration=0.05)
    pyautogui.dragTo(start_x, target_y, duration=DRAG_DURATION_SECONDS, button="left")
    time.sleep(DRAG_WAIT_SECONDS)
    return "DRAGGED_TO_TOP", actual


def drag_scrollbar_down(result: ViewportResult, drag_px: int):
    before = result.scrollbar_thumb
    if before is None:
        return None, 0, "NO_SCROLLBAR_THUMB_DETECTED"

    start_x = before.center_x
    start_y = before.center_y
    end_y = min(start_y + drag_px, result.roi.bottom - 25)
    actual = end_y - start_y

    if actual <= 8:
        return before, 0, "SCROLLBAR_ALREADY_NEAR_BOTTOM"

    pyautogui.moveTo(start_x, start_y, duration=0.05)
    pyautogui.dragTo(start_x, end_y, duration=DRAG_DURATION_SECONDS, button="left")
    time.sleep(DRAG_WAIT_SECONDS)
    return before, actual, "DRAGGED"


def click_card_and_read_id(hwnd: int, card: Card, previous_job_id: str = "", allow_same_job_id: bool = False) -> Tuple[str, str, str]:
    """Click a card and wait for the selected job to change.

    v26 does not blindly trust a fixed sleep after a click. If the currentJobId
    stays the same after clicking a different card, the click probably landed on a
    non-effective area or the right panel has not refreshed. It retries once using
    a slightly different coordinate near the title.
    """
    force_foreground(hwnd)

    # v28: click the title/top content area first. Previous versions often clicked
    # too low in the card, which sometimes left the right panel on the previous job.
    title_x_1 = max(card.rect.left + 72, min(card.title.left + 22, card.rect.right - 92))
    title_x_2 = max(card.rect.left + 84, min(card.title.center_x, card.rect.right - 88))
    title_y = max(card.rect.top + 24, min(card.title.center_y, card.rect.bottom - 42))
    click_points = [
        (title_x_1, title_y),
        (title_x_2, title_y),
        (max(card.rect.left + 76, min(card.title.center_x, card.rect.right - 70)), max(card.rect.top + 30, title_y - 8)),
        (card.click_x, card.click_y),
    ]

    last_url = ""
    last_job_id = ""

    for attempt, (x, y) in enumerate(click_points, start=1):
        pyautogui.moveTo(x, y, duration=0.06)
        pyautogui.click(x, y)

        deadline = time.time() + 2.4
        while time.time() < deadline:
            time.sleep(CLICK_WAIT_SECONDS)
            url = copy_current_url(hwnd)
            job_id = extract_current_job_id(url)
            if url:
                last_url = url
            if job_id:
                last_job_id = job_id

            if not url or not job_id:
                continue

            if allow_same_job_id or not previous_job_id or job_id != previous_job_id:
                return job_id, url, "OK"

        # Try the next point only if we still appear to be on the same job.

    if not last_url:
        return "", "", "NO_URL_COPIED"
    if not last_job_id:
        return "", last_url, "NO_CURRENT_JOB_ID_IN_URL"
    if previous_job_id and last_job_id == previous_job_id and not allow_same_job_id:
        return last_job_id, last_url, "CLICK_NOT_CONFIRMED_SAME_JOB_ID"
    return last_job_id, last_url, "OK"


def save_outputs(
    run_stamp: str,
    records: List[IdRecord],
    window_title: str,
    starting_url: str,
    pages_requested: int,
) -> Tuple[Path, Path]:
    CAPTURE_OUTPUT_DIR.mkdir(exist_ok=True)
    md_path = CAPTURE_OUTPUT_DIR / f"linkedin_job_ids_v34_{run_stamp}.md"
    csv_path = CAPTURE_OUTPUT_DIR / f"linkedin_job_ids_v34_{run_stamp}.csv"

    unique_ids = []
    seen = set()
    duplicates = 0
    failures = 0

    for r in records:
        if r.current_job_id:
            if r.current_job_id not in seen:
                seen.add(r.current_job_id)
                unique_ids.append(r.current_job_id)
            elif r.status.startswith("DUPLICATE"):
                duplicates += 1
        if r.status != "OK_NEW" and not r.status.startswith("DUPLICATE"):
            failures += 1

    md_lines = []
    md_lines.append("# LinkedIn currentJobId capture v29")
    md_lines.append("")
    md_lines.append(f"- Timestamp: `{run_stamp}`")
    md_lines.append(f"- Window: `{window_title}`")
    md_lines.append(f"- Starting URL: `{starting_url}`")
    md_lines.append(f"- Pages requested: `{pages_requested}`")
    md_lines.append(f"- Total card clicks recorded: `{len(records)}`")
    md_lines.append(f"- Unique currentJobIds: `{len(unique_ids)}`")
    boundary_overlaps = len([r for r in records if r.status.startswith("BOUNDARY_OVERLAP")])
    md_lines.append(f"- Duplicate click records: `{duplicates}`")
    md_lines.append(f"- Boundary overlap skips: `{boundary_overlaps}`")
    md_lines.append(f"- Failures: `{failures}`")
    md_lines.append("")
    md_lines.append("## Unique currentJobIds")
    md_lines.append("")
    for job_id in unique_ids:
        md_lines.append(f"- `{job_id}`")
    md_lines.append("")
    md_lines.append("## Records")
    md_lines.append("")
    md_lines.append("| Seq | Page | Start | Viewport | Card | Visibility | Click | currentJobId | Status | First seen | URL |")
    md_lines.append("|---:|---:|---:|---:|---:|---|---|---|---|---:|---|")
    for r in records:
        safe_url = r.url.replace("|", "%7C")
        md_lines.append(
            f"| {r.sequence} | {r.page_number} | {r.page_start} | {r.viewport_index} | {r.card_index} | "
            f"{r.card_visibility} | ({r.click_x},{r.click_y}) | `{r.current_job_id}` | {r.status} | "
            f"{r.first_seen_sequence} | {safe_url} |"
        )

    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "sequence",
                "page_number",
                "page_start",
                "viewport_index",
                "card_index",
                "card_visibility",
                "click_x",
                "click_y",
                "current_job_id",
                "status",
                "first_seen_sequence",
                "url",
            ],
        )
        writer.writeheader()
        for r in records:
            writer.writerow(
                {
                    "sequence": r.sequence,
                    "page_number": r.page_number,
                    "page_start": r.page_start,
                    "viewport_index": r.viewport_index,
                    "card_index": r.card_index,
                    "card_visibility": r.card_visibility,
                    "click_x": r.click_x,
                    "click_y": r.click_y,
                    "current_job_id": r.current_job_id,
                    "status": r.status,
                    "first_seen_sequence": r.first_seen_sequence,
                    "url": r.url,
                }
            )

    return md_path, csv_path


def print_viewport_summary(r: ViewportResult):
    print(f"  ROI: {r.roi.describe()}")
    print(f"  Pagination visible: {r.pagination_visible}")
    if r.footer_rect:
        print(f"  Footer rect: {r.footer_rect.describe()}")
    print(f"  Scrollbar thumb: {r.scrollbar_thumb.describe() if r.scrollbar_thumb else 'none'}")
    print(f"  Cards detected: {len(r.cards)}")
    print(f"  FULL cards to click: {len(full_cards(r))}")
    if r.pagination_visible:
        extra = len(clickable_cards_for_viewport(r)) - len(full_cards(r))
        print(f"  Safe PARTIAL_BOTTOM cards to click on final viewport: {extra}")
    print(f"  PARTIAL cards skipped: {len(partial_cards(r))}")
    print(f"  Page complete by pagination rule: {page_complete_by_pagination(r)}")


def wait_for_left_list_ready(
    hwnd: int,
    window_rect: Rect,
    mouse_xy: Tuple[int, int],
    page_number: int,
    run_stamp: str,
) -> bool:
    """Wait until the left job list is truly usable.

    v20 considered the page ready if it saw cards OR a scrollbar. That is unsafe
    for this visual capturer: if cards are visible but the scrollbar is not
    detected and pagination/footer is not visible, the page may be only partially
    usable. In that state v20 could click the first viewport and then jump to the
    next LinkedIn page, silently missing offers.

    v21 treats cards-without-scrollbar-without-pagination as suspicious and keeps
    waiting. It only returns ready when it sees:
      - cards + scrollbar, or
      - cards + pagination/footer, or
      - scrollbar by itself while cards are still loading.
    """
    deadline = time.time() + PAGE_READY_TIMEOUT_SECONDS
    attempt = 0
    last_cards_count = -1
    stable_cards_polls = 0

    while time.time() < deadline:
        attempt += 1
        result = capture_and_detect(
            hwnd,
            window_rect,
            mouse_xy,
            attempt,
            DEBUG_OUTPUT_DIR,
            run_stamp,
            save_images=(attempt == 1),
            note=f"page_{page_number:02d}_ready_attempt",
        )

        cards_count = len(result.cards)
        has_scrollbar = result.scrollbar_thumb is not None
        has_pagination = result.pagination_visible

        if cards_count == last_cards_count:
            stable_cards_polls += 1
        else:
            stable_cards_polls = 0
            last_cards_count = cards_count

        if cards_count > 0 and has_scrollbar:
            readiness = "READY_CARDS_AND_SCROLLBAR"
            is_ready = True
        elif cards_count > 0 and has_pagination:
            readiness = "READY_CARDS_AND_PAGINATION"
            is_ready = True
        elif cards_count == 0 and has_scrollbar:
            readiness = "WAITING_SCROLLBAR_ONLY"
            is_ready = False
        elif cards_count > 0:
            readiness = "SUSPICIOUS_CARDS_WITHOUT_SCROLLBAR_OR_PAGINATION"
            is_ready = False
        else:
            readiness = "WAITING_NO_CARDS"
            is_ready = False

        print(
            f"  Page-ready check {attempt}: "
            f"cards={cards_count}, scrollbar={'yes' if has_scrollbar else 'no'}, "
            f"pagination={'yes' if has_pagination else 'no'}, "
            f"stable_cards_polls={stable_cards_polls}, readiness={readiness}"
        )

        if is_ready:
            return True

        time.sleep(PAGE_READY_POLL_SECONDS)

    return False


def capture_current_page_ids(
    hwnd: int,
    window_rect: Rect,
    mouse_xy: Tuple[int, int],
    run_stamp: str,
    page_number: int,
    page_start: int,
    records: List[IdRecord],
    seen_job_ids: Dict[str, int],
    first_seen_sequence_by_job_id: Dict[str, int],
    sequence_start: int,
) -> PageCaptureResult:
    """Capture one LinkedIn result page using a controlled single-pass strategy.

    v24 principles:
    - Do not re-click cards already successfully attempted on this page.
    - Do not treat a repeated viewport as new work.
    - Confirm that clicking a card actually changes currentJobId, except for the
      first selected card of the page.
    - Use smaller adaptive scrollbar drags and stop only on trusted completion
      signals: pagination/footer or confirmed bottom/no movement.
    """
    sequence = sequence_start
    last_valid_job_id = ""
    records_before = len(records)
    unique_before = len(seen_job_ids)
    viewports_scanned = 0
    page_status = "INCOMPLETE_UNKNOWN"
    stop_reason = "NOT_SET"
    allow_next_page = False

    page_attempted_fingerprints = set()
    page_seen_left_card_signatures: set[str] = set()
    no_new_left_card_scrolls = 0
    previous_viewport_fps: set = set()
    repeated_viewport_count = 0
    last_unique_count = 99

    print("")
    print(f"========== PAGE {page_number} / start={page_start} ==========")

    print("Pre-reset detection...")
    pre = capture_and_detect(hwnd, window_rect, mouse_xy, 0, DEBUG_OUTPUT_DIR, run_stamp, save_images=True, note=f"page_{page_number:02d}_pre_reset")
    print(f"  Pre-reset scrollbar thumb: {pre.scrollbar_thumb.describe() if pre.scrollbar_thumb else 'none'}")

    reset_status, reset_delta = drag_scrollbar_to_top(pre)
    print(f"Reset-to-top status: {reset_status}, delta_px={reset_delta}")

    print("")
    print("Scanning viewport 1 after reset...")
    current = capture_and_detect(hwnd, window_rect, mouse_xy, 1, DEBUG_OUTPUT_DIR, run_stamp, save_images=True, note=f"page_{page_number:02d}")
    viewports_scanned = 1
    print_viewport_summary(current)

    if not current.cards:
        page_status = "INCOMPLETE_ZERO_CARDS"
        stop_reason = "ZERO_CARDS_AFTER_RESET"
        print("")
        print(f"Stopping page safely: {stop_reason}. No navigation to next page will occur.")
        return PageCaptureResult(
            sequence=sequence,
            last_valid_job_id=last_valid_job_id,
            status=page_status,
            stop_reason=stop_reason,
            records_added=0,
            unique_added=0,
            duplicates_added=0,
            failures_added=0,
            viewports_scanned=viewports_scanned,
            allow_next_page=False,
        )

    for viewport_index in range(1, MAX_VIEWPORTS + 1):
        if viewport_index > 1:
            drag_px = calculate_drag_px(current, last_unique_count)
            print("")
            print(f"Viewport {viewport_index}: controlled scrollbar drag by about {drag_px}px")
            before, actual_drag, status = drag_scrollbar_down(current, drag_px)
            if status != "DRAGGED":
                print(f"  Scrollbar drag status: {status}")
                if current.pagination_visible:
                    page_status = "COMPLETE_BY_PAGINATION"
                    stop_reason = f"SCROLL_NOT_NEEDED_PAGINATION_VISIBLE_{status}"
                    allow_next_page = True
                elif scrollbar_near_bottom(current):
                    page_status = "COMPLETE_BY_BOTTOM_REACHED"
                    stop_reason = f"SCROLLBAR_NEAR_BOTTOM_{status}"
                    allow_next_page = True
                elif viewport_index == 2:
                    page_status = "INCOMPLETE_NO_SCROLLBAR_AFTER_FIRST_VIEWPORT"
                    stop_reason = status
                    allow_next_page = False
                else:
                    page_status = "INCOMPLETE_SCROLL_FAILED_AFTER_MULTIPLE_VIEWPORTS"
                    stop_reason = status
                    allow_next_page = False
                print("")
                print(f"Stopping page with status={page_status}; stop_reason={stop_reason}")
                print("Guardrail: not treating this as completed unless pagination/footer or bottom was detected.")
                break

            nxt = capture_and_detect(hwnd, window_rect, mouse_xy, viewport_index, DEBUG_OUTPUT_DIR, run_stamp, save_images=True, note=f"page_{page_number:02d}")
            viewports_scanned = viewport_index
            nxt.drag_px_used = actual_drag
            nxt.thumb_before = before
            nxt.thumb_after = nxt.scrollbar_thumb
            if before and nxt.scrollbar_thumb:
                nxt.thumb_delta_px = nxt.scrollbar_thumb.center_y - before.center_y

            current_fps_before = viewport_fingerprint_set(current)
            next_fps = viewport_fingerprint_set(nxt)
            overlap = fingerprint_overlap_ratio(current_fps_before, next_fps)

            if nxt.thumb_delta_px <= 3 and overlap >= 0.70 and not nxt.pagination_visible:
                repeated_viewport_count += 1
                nxt.movement_status = f"VIEWPORT_NOT_ADVANCED_{repeated_viewport_count}"
            else:
                repeated_viewport_count = 0
                nxt.movement_status = f"SCROLLBAR_MOVED_DELTA_{nxt.thumb_delta_px}_OVERLAP_{overlap:.2f}"

            current = nxt
            print_viewport_summary(current)
            print(f"  Movement status: {current.movement_status}")

            if repeated_viewport_count >= NO_MOVEMENT_LIMIT:
                print("")
                if current.pagination_visible or scrollbar_near_bottom(current):
                    print("Stopping page: viewport did not advance and footer/bottom is visible.")
                    page_status = "COMPLETE_BY_BOTTOM_REACHED"
                    stop_reason = "REPEATED_VIEWPORT_AT_BOTTOM_OR_FOOTER"
                    allow_next_page = True
                else:
                    print("Stopping page safely: viewport did not advance, but footer/bottom is not confirmed.")
                    page_status = "INCOMPLETE_SCROLL_NOT_ADVANCING"
                    stop_reason = "REPEATED_VIEWPORT_WITHOUT_COMPLETION_SIGNAL"
                    allow_next_page = False
                break

        print("")
        left_cards, _left_raw = collect_left_panel_card_signatures(hwnd)
        new_left_cards = [c for c in left_cards if c.signature not in page_seen_left_card_signatures]
        for c in new_left_cards:
            page_seen_left_card_signatures.add(c.signature)
        if new_left_cards:
            no_new_left_card_scrolls = 0
        else:
            no_new_left_card_scrolls += 1
        print(
            f"Left-panel text coverage: visible_or_dom_cards={len(left_cards)}, "
            f"new_card_signatures={len(new_left_cards)}, total_seen_on_page={len(page_seen_left_card_signatures)}, "
            f"no_new_scrolls={no_new_left_card_scrolls}"
        )
        if new_left_cards[:8]:
            print("  New left-panel cards detected:")
            for c in new_left_cards[:8]:
                print(f"    - {c.company} | {c.title} | {c.location} | {c.state_text}")

        print("")
        print(f"Clicking not-yet-attempted cards in page {page_number}, viewport {viewport_index}...")
        viewport_unique_count = 0
        attempted_this_viewport = 0
        skipped_seen_fingerprint = 0

        candidates, raw_candidate_count, skipped_top_overlap = capture_candidates_for_viewport(current, viewport_index)
        if viewport_index > 1:
            print(
                f"  v28 candidate filter: raw={raw_candidate_count}, "
                f"skipped_top_overlap={skipped_top_overlap}, to_click={len(candidates)}"
            )
        for candidate_pos, card in enumerate(candidates, start=1):
            if card.fingerprint and card.fingerprint in page_attempted_fingerprints:
                skipped_seen_fingerprint += 1
                print(f"  Skipping p{page_number} v{viewport_index} card {card.index:02d}: already attempted card fingerprint on this page.")
                continue

            sequence += 1
            attempted_this_viewport += 1
            allow_same = not bool(last_valid_job_id)
            print(f"  Clicking p{page_number} v{viewport_index} card {card.index:02d} at ({card.click_x},{card.click_y})...")
            job_id, url, raw_status = click_card_and_read_id(
                hwnd,
                card,
                previous_job_id=last_valid_job_id,
                allow_same_job_id=allow_same,
            )

            first_seen_seq = 0
            if raw_status == "OK":
                if card.fingerprint:
                    page_attempted_fingerprints.add(card.fingerprint)
                last_valid_job_id = job_id
                if job_id in seen_job_ids:
                    seen_job_ids[job_id] += 1
                    first_seen_seq = first_seen_sequence_by_job_id[job_id]
                    status = f"DUPLICATE_OF_SEQ_{first_seen_seq}"
                    print(f"    currentJobId: {job_id} ({status})")
                else:
                    seen_job_ids[job_id] = 1
                    first_seen_sequence_by_job_id[job_id] = sequence
                    first_seen_seq = sequence
                    viewport_unique_count += 1
                    status = "OK_NEW"
                    print(f"    currentJobId: {job_id} (OK_NEW)")
            else:
                # v28: in v26 most CLICK_NOT_CONFIRMED events were the first clicked
                # candidate after the top-overlap filter. That card is usually a
                # boundary/overlap card still representing the previous selected job,
                # not a missed offer. Keep the record for auditability, but classify
                # it separately so it does not count as a real failure.
                if (
                    raw_status == "CLICK_NOT_CONFIRMED_SAME_JOB_ID"
                    and viewport_index > 1
                    and candidate_pos == 1
                    and job_id
                    and last_valid_job_id
                    and job_id == last_valid_job_id
                ):
                    status = "BOUNDARY_OVERLAP_SAME_JOB_ID"
                    if card.fingerprint:
                        page_attempted_fingerprints.add(card.fingerprint)
                    print(f"    status: {status}; job_id={job_id} (classified as overlap, not failure)")
                else:
                    status = raw_status
                    print(f"    status: {status}; job_id={job_id or 'none'}")

            records.append(
                IdRecord(
                    sequence=sequence,
                    page_number=page_number,
                    page_start=page_start,
                    viewport_index=viewport_index,
                    card_index=card.index,
                    card_visibility=card.visibility,
                    click_x=card.click_x,
                    click_y=card.click_y,
                    current_job_id=job_id,
                    url=url,
                    status=status,
                    first_seen_sequence=first_seen_seq,
                )
            )

        print(
            f"  Viewport attempt summary: raw_candidates={raw_candidate_count}, filtered_candidates={len(candidates)}, "
            f"attempted={attempted_this_viewport}, skipped_seen_fingerprint={skipped_seen_fingerprint}, "
            f"new_unique={viewport_unique_count}"
        )
        last_unique_count = viewport_unique_count

        current_fps = viewport_fingerprint_set(current)
        if previous_viewport_fps:
            visible_overlap = fingerprint_overlap_ratio(previous_viewport_fps, current_fps)
            print(f"  Visible-card fingerprint overlap vs previous viewport: {visible_overlap:.2f}")
        previous_viewport_fps = current_fps

        if current.pagination_visible:
            print("")
            if page_complete_by_pagination(current) and no_new_left_card_scrolls >= 1:
                print("Stopping page: pagination visible, cards above footer attempted, and left-panel text produced no new card signatures.")
                page_status = "COMPLETE_BY_PAGINATION"
                stop_reason = "PAGINATION_VISIBLE_AND_LEFT_PANEL_STABLE"
                allow_next_page = True
                break
            else:
                print("Pagination is visible, but v35 will continue controlled scrolling until left-panel card signatures stabilize.")

        if attempted_this_viewport == 0 and skipped_seen_fingerprint > 0:
            if scrollbar_near_bottom(current) and no_new_left_card_scrolls >= 2:
                print("")
                print("Stopping page: no new visible cards to attempt, left-panel signatures stable, and scrollbar is near bottom.")
                page_status = "COMPLETE_BY_BOTTOM_REACHED"
                stop_reason = "NO_NEW_CARDS_LEFT_PANEL_STABLE_AND_SCROLLBAR_NEAR_BOTTOM"
                allow_next_page = True
                break
            print("  No new cards were attempted in this viewport; will try one controlled scroll rather than re-clicking.")

    else:
        page_status = "INCOMPLETE_MAX_VIEWPORTS_REACHED"
        stop_reason = "MAX_VIEWPORTS_REACHED_WITHOUT_COMPLETION"
        allow_next_page = False

    if page_status == "INCOMPLETE_UNKNOWN":
        page_status = "INCOMPLETE_STOPPED_WITHOUT_COMPLETION_SIGNAL"
        if stop_reason == "NOT_SET":
            stop_reason = "NO_COMPLETION_SIGNAL"
        allow_next_page = False

    # v14 relaxed navigation guardrail:
    # In real LinkedIn runs, footer/scrollbar completion detection can be slightly
    # less reliable than the text inventory. If we captured a near-full page and
    # saw a near-full left-panel inventory, allow navigation to the next page with
    # a warning instead of stopping the whole multi-page batch. This directly fixes
    # the observed case: 2 pages requested but only page 1 was captured because
    # page 1 ended with an untrusted completion signal despite ~24 offers captured.
    page_unique_added_so_far = len(seen_job_ids) - unique_before
    if (
        not allow_next_page
        and page_unique_added_so_far >= MIN_UNIQUE_TO_ALLOW_RELAXED_NEXT
    ):
        print(
            "v17 relaxed-next guardrail: page did not finish with a perfect completion signal, "
            f"but captured_unique={page_unique_added_so_far} and "
            f"left_panel_signatures={len(page_seen_left_card_signatures)}. "
            "Allowing next direct-URL page because the page produced enough unique jobs."
        )
        page_status = "WARNING_NEAR_COMPLETE_PAGE_ALLOWED_NEXT"
        if stop_reason == "NOT_SET":
            stop_reason = "RELAXED_NEXT_BY_LEFT_PANEL_INVENTORY"
        else:
            stop_reason = f"{stop_reason}; RELAXED_NEXT_BY_LEFT_PANEL_INVENTORY"
        allow_next_page = True

    records_added = len(records) - records_before
    unique_added = len(seen_job_ids) - unique_before
    added_records = records[records_before:]
    duplicates_added = len([r for r in added_records if r.status.startswith("DUPLICATE")])
    failures_added = len([r for r in added_records if is_failure_status(r.status)])

    print("")
    print(
        f"PAGE_RESULT page={page_number} start={page_start} status={page_status} "
        f"stop_reason={stop_reason} records_added={records_added} unique_added={unique_added} "
        f"duplicates_added={duplicates_added} failures_added={failures_added} "
        f"left_panel_signatures={len(page_seen_left_card_signatures)} "
        f"last_valid_job_id={last_valid_job_id or 'none'} allow_next_page={allow_next_page}"
    )

    return PageCaptureResult(
        sequence=sequence,
        last_valid_job_id=last_valid_job_id,
        status=page_status,
        stop_reason=stop_reason,
        records_added=records_added,
        unique_added=unique_added,
        duplicates_added=duplicates_added,
        failures_added=failures_added,
        viewports_scanned=viewports_scanned,
        allow_next_page=allow_next_page,
    )



def _pagination_mask_pixel(r: int, g: int, b: int) -> bool:
    # Text/buttons in the LinkedIn footer pagination are usually dark gray/black,
    # with occasional LinkedIn-blue accents. Keep this broad but restricted to the
    # pagination band so we do not confuse it with job-card text.
    dark = r < 85 and g < 85 and b < 85
    blue = is_linkedin_blue(r, g, b)
    return dark or blue


def _component_rects_from_mask(img: Image.Image, band: Rect) -> List[Rect]:
    """Return small visual components inside a footer pagination band."""
    rgb = img.convert("RGB")
    px = rgb.load()
    w, h = band.width, band.height
    mask = [[False] * w for _ in range(h)]

    for yy, y in enumerate(range(band.top, band.bottom)):
        for xx, x in enumerate(range(band.left, band.right)):
            rr, gg, bb = px[x, y]
            if _pagination_mask_pixel(rr, gg, bb):
                mask[yy][xx] = True

    seen = [[False] * w for _ in range(h)]
    comps: List[Rect] = []
    for yy in range(h):
        for xx in range(w):
            if not mask[yy][xx] or seen[yy][xx]:
                continue
            stack = [(xx, yy)]
            seen[yy][xx] = True
            xs = []
            ys = []
            while stack:
                cx, cy = stack.pop()
                xs.append(cx)
                ys.append(cy)
                for nx in (cx - 1, cx, cx + 1):
                    for ny in (cy - 1, cy, cy + 1):
                        if nx == cx and ny == cy:
                            continue
                        if 0 <= nx < w and 0 <= ny < h and mask[ny][nx] and not seen[ny][nx]:
                            seen[ny][nx] = True
                            stack.append((nx, ny))
            x1, x2 = min(xs) + band.left, max(xs) + band.left + 1
            y1, y2 = min(ys) + band.top, max(ys) + band.top + 1
            rect = Rect(x1, y1, x2, y2)
            # Keep digit/button/label-like components and discard long horizontal
            # separators or single-pixel noise.
            if 2 <= rect.width <= 95 and 5 <= rect.height <= 38:
                comps.append(rect)
    return comps


def _merge_pagination_components(comps: List[Rect]) -> List[Rect]:
    """Group neighboring components on the same pagination row into clickable clusters."""
    if not comps:
        return []

    comps = sorted(comps, key=lambda r: (r.center_y, r.left))
    # Choose the densest row by looking at component center-y values. This avoids
    # the lower About/Accessibility footer links and locks onto the pagination row.
    best_y = None
    best_score = -1
    for c in comps:
        score = sum(1 for o in comps if abs(o.center_y - c.center_y) <= 10)
        if score > best_score:
            best_score = score
            best_y = c.center_y
    row = [c for c in comps if best_y is not None and abs(c.center_y - best_y) <= 13]
    row.sort(key=lambda r: r.left)

    groups: List[Rect] = []
    for comp in row:
        if not groups:
            groups.append(comp)
            continue
        last = groups[-1]
        same_row = abs(comp.center_y - last.center_y) <= 14
        close_x = comp.left <= last.right + 18
        # Merge letters of "Next" and the outline/text of a page button, but keep
        # separate page numbers apart when there is a visible gap.
        if same_row and close_x:
            groups[-1] = Rect(min(last.left, comp.left), min(last.top, comp.top), max(last.right, comp.right), max(last.bottom, comp.bottom))
        else:
            groups.append(comp)

    # Remove very wide footer words if they sneak in; keep page-number circles,
    # digits, and the compact Next label.
    cleaned = [g for g in groups if 3 <= g.width <= 90 and 7 <= g.height <= 42]
    return cleaned


def detect_pagination_click_candidates(img: Image.Image, r: ViewportResult, page_number: int) -> List[Tuple[int, int, str]]:
    """Compute pagination click candidates from the current screenshot at runtime.

    No absolute coordinates are used. We derive a narrow band around the detected
    footer top because the page-number row sits near that upper edge, while the
    lower part of the footer contains non-navigation links such as About/Privacy.
    """
    if not r.footer_rect:
        return []

    x_right_limit = r.scrollbar_thumb.left - 12 if r.scrollbar_thumb else r.roi.right - 18
    band = Rect(
        r.roi.left + 55,
        max(r.roi.top, r.footer_rect.top - 18),
        min(r.roi.right - 18, x_right_limit),
        min(r.roi.bottom, r.footer_rect.top + 58),
    )

    comps = _component_rects_from_mask(img, band)
    groups = _merge_pagination_components(comps)
    # Prefer groups in the right half of the panel-footer band where LinkedIn's
    # page controls sit in this layout. Keep fallback candidates if grouping is
    # imperfect.
    groups = [g for g in groups if g.center_x >= r.roi.left + int(r.roi.width * 0.42)]
    groups.sort(key=lambda g: g.left)

    print(f"  Pagination band: {band.describe()}")
    if groups:
        print("  Runtime pagination visual groups:")
        for idx, g in enumerate(groups, start=1):
            print(f"    group {idx}: {g.describe()}, click=({g.center_x},{g.center_y})")
    else:
        print("  Runtime pagination visual groups: none")

    candidates: List[Tuple[int, int, str]] = []
    # For page 1, groups usually appear as: active 1, 2, Next. The safest target
    # is the first compact group to the right of the active page. If grouping fails,
    # try several runtime-relative y positions near the pagination row.
    if len(groups) >= 2:
        target = groups[1]
        candidates.append((target.center_x, target.center_y, "runtime-next-page-number-group-2"))
    if len(groups) >= 3:
        target = groups[2]
        candidates.append((target.center_x, target.center_y, "runtime-next-label-or-group-3"))
    if len(groups) >= 1:
        # If only one group was found, try just to its right, still within the
        # detected pagination band.
        g = groups[0]
        candidates.append((min(x_right_limit - 8, g.right + 34), g.center_y, "runtime-right-of-active-page"))

    # Dynamic fallbacks: same x-ratios as before, but y is derived from the actual
    # detected pagination row, not from the footer center.
    if groups:
        row_y = int(round(sum(g.center_y for g in groups) / len(groups)))
    else:
        row_y = r.footer_rect.top + 26
    row_y = max(band.top + 8, min(row_y, band.bottom - 8))

    candidates.extend([
        (r.roi.left + int(r.roi.width * 0.63), row_y, "dynamic-band-page-number-ratio-063"),
        (r.roi.left + int(r.roi.width * 0.68), row_y, "dynamic-band-page-number-ratio-068"),
        (min(x_right_limit - 8, r.roi.left + int(r.roi.width * 0.83)), row_y, "dynamic-band-next-ratio-083"),
    ])

    # Deduplicate near-identical candidates while preserving order.
    deduped: List[Tuple[int, int, str]] = []
    for x, y, label in candidates:
        if x < band.left or x > band.right or y < band.top or y > band.bottom:
            continue
        if any(abs(x - ox) <= 6 and abs(y - oy) <= 6 for ox, oy, _ in deduped):
            continue
        deduped.append((int(x), int(y), label))
    return deduped



def capture_window_image(hwnd: int):
    """Return a fresh screenshot of the current desktop/window context.

    The rest of the capture engine already uses full-screen screenshots and
    screen-coordinate ROIs, so this helper intentionally mirrors that behavior
    instead of using fixed browser/window coordinates.
    """
    force_foreground(hwnd)
    time.sleep(0.15)
    return pyautogui.screenshot()


def open_results_page_direct_v16(
    hwnd: int,
    window_rect: Rect,
    mouse_xy: Tuple[int, int],
    run_stamp: str,
    page_number: int,
    target_start: int,
    base_url: str,
    previous_sigs: set[str],
) -> bool:
    """Open one LinkedIn results page as an independent capture unit.

    v16 intentionally avoids the old pattern of capturing page 1 and then trying
    to transition mid-loop via Next/footer. For page N, it builds a clean URL
    with start=(N-1)*25 and no currentJobId, navigates there first, waits for the
    left panel to become usable, and only then lets the normal page inventory
    capture run.
    """
    print("")
    print(f"Preparing v24 independent direct-page open for page {page_number} (target start={target_start})...")
    target_url = set_url_start_for_results_page(base_url, target_start)
    print(f"  v24 direct page URL target: {target_url}")
    diag_event("direct_page_target_url", page_number=page_number, target_start=target_start, base_url=base_url, target_url=target_url)
    if not target_url:
        print("  PAGE_START_FAILED: target URL is empty; cannot navigate.")
        diag_event("direct_page_empty_target_url", page_number=page_number, target_start=target_start, base_url=base_url)
        return False
    before_url = copy_current_url(hwnd)
    before_sigs = set(previous_sigs or left_panel_signature_set(hwnd))
    print(f"  Current URL before direct page open: {before_url}")
    print(f"  Previous visible signatures: {len(before_sigs)}")

    navigate_to_url(hwnd, target_url)

    deadline = time.time() + max(PAGE_READY_TIMEOUT_SECONDS, 10.0)
    attempt = 0
    last_url = ""
    last_start = -1
    last_sigs: set[str] = set()
    while time.time() < deadline:
        attempt += 1
        time.sleep(PAGE_READY_POLL_SECONDS)
        after_url = copy_current_url(hwnd)
        after_start = extract_start_param(after_url)
        after_sigs = left_panel_signature_set(hwnd)
        overlap = signature_overlap_ratio(before_sigs, after_sigs)
        new_count = len(after_sigs - before_sigs)
        start_ok = after_start == target_start or (target_start > 0 and f"start={target_start}" in after_url)
        url_changed = after_url != before_url
        enough_cards = len(after_sigs) >= 3
        sigs_changed = bool(before_sigs) and enough_cards and (new_count >= 2 or overlap <= 0.72)
        print(
            f"  v24 direct-page verify {attempt}: start={after_start}, "
            f"start_ok={start_ok}, url_changed={url_changed}, "
            f"left_sigs={len(after_sigs)}, new_sigs={new_count}, overlap={overlap:.2f}"
        )
        last_url = after_url
        last_start = after_start
        last_sigs = after_sigs
        if enough_cards and (start_ok or sigs_changed or page_number == 1):
            print(f"  v24 direct-page open VERIFIED for page {page_number}.")
            diag_event("direct_page_verified", page_number=page_number, target_start=target_start, after_start=after_start, left_sigs=len(after_sigs), new_sigs=new_count, overlap=round(overlap, 3), after_url=after_url)
            return True

    print(
        f"  PAGE_START_FAILED: expected page {page_number} start={target_start}; "
        f"last_start={last_start}; last_sigs={len(last_sigs)}; last_url={last_url}"
    )
    return False


def click_footer_next_page(hwnd: int, window_rect: Rect, mouse_xy: Tuple[int, int], run_stamp: str, page_number: int) -> bool:
    """Move to the next LinkedIn results page and verify it actually changed.

    v15 changes the priority:
    1. Capture the current left-panel card signatures.
    2. Force a direct results-page URL transition with start=<page_number*25>
       and WITHOUT currentJobId.
    3. Verify either the URL start is correct OR the visible card signatures changed.
    4. Only if direct URL fails, try the older visual footer click candidates.

    This avoids the v14 failure mode where the tool completed page 1 correctly
    but silently failed to enter page 2.
    """
    print("")
    print(f"Preparing legacy forced verified page transition after page {page_number}...")
    target_start = page_number * RESULTS_PER_PAGE
    before_url = copy_current_url(hwnd)
    before_start = extract_start_param(before_url)
    before_sigs = left_panel_signature_set(hwnd)
    print(f"  URL before navigation: {before_url}")
    print(f"  URL start before navigation: {before_start}")
    print(f"  Left-panel signatures before navigation: {len(before_sigs)}")
    print(f"  Target next page start: {target_start}")

    def verify_transition(label: str, expected_start: int, before_url_for_check: str, before_sigs_for_check: set[str]) -> bool:
        deadline = time.time() + PAGE_READY_TIMEOUT_SECONDS
        attempt = 0
        while time.time() < deadline:
            attempt += 1
            time.sleep(PAGE_READY_POLL_SECONDS)
            after_url = copy_current_url(hwnd)
            after_start = extract_start_param(after_url)
            after_sigs = left_panel_signature_set(hwnd)
            overlap = signature_overlap_ratio(before_sigs_for_check, after_sigs)
            new_count = len(after_sigs - before_sigs_for_check)
            start_ok = after_start == expected_start or (expected_start > 0 and f"start={expected_start}" in after_url)
            url_changed = after_url != before_url_for_check
            signatures_changed = bool(after_sigs) and (new_count >= 2 or overlap <= 0.72)
            ready_enough = len(after_sigs) >= 3
            print(
                f"  {label} verify {attempt}: start={after_start}, "
                f"start_ok={start_ok}, url_changed={url_changed}, "
                f"left_sigs={len(after_sigs)}, new_sigs={new_count}, overlap={overlap:.2f}"
            )
            if ready_enough and (start_ok or signatures_changed):
                print(f"  {label} transition VERIFIED.")
                return True
        print(f"  {label} transition NOT verified in time.")
        return False

    # v15 primary path: direct URL, no currentJobId anchor.
    direct_url = set_url_start_for_results_page(before_url, target_start)
    print(f"  v16 direct results URL target: {direct_url}")
    navigate_to_url(hwnd, direct_url)
    if verify_transition("direct-url-no-currentJobId", target_start, before_url, before_sigs):
        return True

    # Secondary path: URL with currentJobId anchor, in case LinkedIn needs it for this collection.
    anchor_job_id = extract_current_job_id(before_url)
    anchored_url = set_url_start(before_url, target_start, anchor_job_id=anchor_job_id)
    print(f"  v16 anchored URL fallback target: {anchored_url}")
    navigate_to_url(hwnd, anchored_url)
    if verify_transition("anchored-url-fallback", target_start, before_url, before_sigs):
        return True

    # Tertiary path: visual footer click, then verify the same way.
    print("  v16 URL navigation did not verify. Trying runtime footer visual click candidates...")
    r = capture_and_detect(
        hwnd,
        window_rect,
        mouse_xy,
        99,
        DEBUG_OUTPUT_DIR,
        run_stamp,
        save_images=True,
        note=f"page_{page_number:02d}_footer_navigation_v15_visual",
    )
    print(f"  Footer navigation ROI: {r.roi.describe()}")
    print(f"  Pagination visible: {r.pagination_visible}")
    print(f"  Footer rect: {r.footer_rect.describe() if r.footer_rect else 'none'}")
    print(f"  Scrollbar thumb: {r.scrollbar_thumb.describe() if r.scrollbar_thumb else 'none'}")

    if not r.pagination_visible or not r.footer_rect:
        print("  Visual footer navigation unavailable: pagination/footer is not visible.")
        print("  PAGE_TRANSITION_FAILED: expected next page, but could not verify direct URL or footer navigation.")
        return False

    screenshot = capture_window_image(hwnd)
    candidates = detect_pagination_click_candidates(screenshot, r, page_number)
    if not candidates:
        print("  Footer visual navigation failed: no runtime pagination candidates detected.")
        print("  PAGE_TRANSITION_FAILED: expected next page, but no visual candidates were found.")
        return False

    before_visual_url = copy_current_url(hwnd)
    before_visual_sigs = left_panel_signature_set(hwnd)
    for attempt_idx, (click_x, click_y, label) in enumerate(candidates, start=1):
        print(f"  Visual navigation attempt {attempt_idx}: clicking {label} at ({click_x},{click_y})...")
        force_foreground(hwnd)
        pyautogui.moveTo(click_x, click_y, duration=0.10)
        pyautogui.click(click_x, click_y)
        if verify_transition(f"visual-click-{attempt_idx}-{label}", target_start, before_visual_url, before_visual_sigs):
            return True

    print("  PAGE_TRANSITION_FAILED: expected next page, but all direct URL and visual attempts failed verification.")
    return False

def unique_ok_new_records(records: List[IdRecord]) -> List[IdRecord]:
    seen = set()
    out: List[IdRecord] = []

    for record in records:
        if record.status != "OK_NEW":
            continue
        if not record.current_job_id:
            continue
        if record.current_job_id in seen:
            continue

        seen.add(record.current_job_id)
        out.append(record)

    return out


def capture_raw_text_phase(
    hwnd: int,
    records: List[IdRecord],
    run_stamp: str,
) -> List[RawJobTextRecord]:
    raw_records: List[RawJobTextRecord] = []
    unique_records = unique_ok_new_records(records)

    print("")
    print("========== PHASE 2: SLOW RAW TEXT CAPTURE ==========")
    print(f"Unique OK_NEW URLs to visit: {len(unique_records)}")
    print("This phase opens each captured URL directly and waits for the job panel.")
    print("It does not use left-panel scrolling and does not click inside the right panel.")

    for idx, record in enumerate(unique_records, start=1):
        print("")
        print(f"Raw capture {idx}/{len(unique_records)}: currentJobId={record.current_job_id}")
        diag_event("raw_capture_begin", raw_index=idx, raw_total=len(unique_records), current_job_id=record.current_job_id, source_sequence=record.sequence, page_number=record.page_number, page_start=record.page_start, url=record.url)
        print(f"  Source: page={record.page_number}, viewport={record.viewport_index}, card={record.card_index}")
        print("  Navigating to captured job URL...")

        navigate_to_url(hwnd, record.url)
        time.sleep(PHASE2_NAV_WAIT_SECONDS)

        status, final_url, raw_text, attempts = wait_for_job_url_and_panel_text(
            hwnd=hwnd,
            expected_job_id=record.current_job_id,
            expected_url=record.url,
        )

        print(f"  Final status: {status}; raw text chars: {len(raw_text)}; attempts: {attempts}")
        diag_event("raw_capture_result", raw_index=idx, current_job_id=record.current_job_id, status=status, raw_text_chars=len(raw_text), attempts=attempts, final_url=final_url or record.url)

        raw_records.append(
            RawJobTextRecord(
                sequence=idx,
                source_sequence=record.sequence,
                page_number=record.page_number,
                page_start=record.page_start,
                viewport_index=record.viewport_index,
                card_index=record.card_index,
                current_job_id=record.current_job_id,
                url=final_url or record.url,
                raw_text=raw_text,
                status=status,
                ready_attempts=attempts,
            )
        )

    return raw_records


def save_raw_text_outputs(run_stamp: str, raw_records: List[RawJobTextRecord]) -> Tuple[Path, Path]:
    CAPTURE_OUTPUT_DIR.mkdir(exist_ok=True)
    jsonl_path = CAPTURE_OUTPUT_DIR / f"linkedin_job_text_v35_{run_stamp}.jsonl"
    md_path = CAPTURE_OUTPUT_DIR / f"linkedin_job_text_v35_{run_stamp}.md"

    with jsonl_path.open("w", encoding="utf-8") as f:
        for r in raw_records:
            f.write(json.dumps({
                "sequence": r.sequence,
                "source_sequence": r.source_sequence,
                "page_number": r.page_number,
                "page_start": r.page_start,
                "viewport_index": r.viewport_index,
                "card_index": r.card_index,
                "current_job_id": r.current_job_id,
                "url": r.url,
                "status": r.status,
                "ready_attempts": r.ready_attempts,
                "raw_text": r.raw_text,
            }, ensure_ascii=False) + "\n")

    ok_statuses = {"OK_RAW_TEXT", "OK_RAW_TEXT_AFTER_RELOAD"}

    lines = []
    lines.append("# LinkedIn raw job text capture v35")
    lines.append("")
    lines.append(f"- Timestamp: `{run_stamp}`")
    lines.append(f"- Raw records: `{len(raw_records)}`")
    lines.append(f"- OK raw records: `{len([r for r in raw_records if r.status in ok_statuses])}`")
    lines.append("")
    for r in raw_records:
        lines.append("---")
        lines.append("")
        lines.append(f"## `{r.current_job_id}`")
        lines.append("")
        lines.append(f"- Status: `{r.status}`")
        lines.append(f"- Attempts: `{r.ready_attempts}`")
        lines.append(f"- Source sequence: `{r.source_sequence}`")
        lines.append(f"- Page: `{r.page_number}`")
        lines.append(f"- Viewport: `{r.viewport_index}`")
        lines.append(f"- Card: `{r.card_index}`")
        lines.append(f"- URL: {r.url}")
        lines.append("")
        lines.append("```text")
        lines.append(r.raw_text)
        lines.append("```")
        lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return jsonl_path, md_path


def main() -> int:
    DEBUG_OUTPUT_DIR.mkdir(exist_ok=True)
    CAPTURE_OUTPUT_DIR.mkdir(exist_ok=True)

    print("LinkedIn Visual currentJobId capture v35.10/v24 - collection-aware pagination + diagnostics")
    print("----------------------------------------------------------------")
    print("Phase 1 WILL click detected FULL cards to capture IDs/URLs.")
    print("It will NOT parse job descriptions, extract titles/companies, or analyze offers.")
    print("Phase 2 raw text capture is optional and disabled by default during testing.")
    print("")
    print("Deduplication rule:")
    print("- currentJobId is the real identity key.")
    print("- Duplicates are recorded as DUPLICATE_OF_SEQ_<n>, but only OK_NEW counts as new.")
    print("- Page 2+ is opened as an independent direct URL page with start=(page-1)*25 before capture.")
    print("- On the final footer viewport, safe PARTIAL_BOTTOM cards are clicked once.")
    print("- Guardrail: if scrolling fails before page completion, it stops instead of skipping ahead.")
    print("- v35.10/v24: collection-aware capture, base URL recovery, crash-safe diagnostics, and stable raw summary.")
    print("")
    print("Open LinkedIn Jobs with the left list and right panel visible.")
    print("Place the mouse over the RIGHT side of the FIRST visible card in the LEFT panel.")
    print("Then leave mouse/keyboard untouched during capture.")
    print("")

    run_stamp = timestamp()
    text_log_path, jsonl_log_path = setup_diagnostic_logging(run_stamp)
    print(f"Diagnostic text log: {text_log_path.resolve()}")
    print(f"Diagnostic JSONL log: {jsonl_log_path.resolve()}")
    diag_event("capture_bootstrap", version="v35.10/v24", cwd=str(Path.cwd()), script=str(Path(__file__).resolve()))

    pages_raw = input(f"Pages to capture [{DEFAULT_PAGES_TO_CAPTURE}]: ").strip()
    if not pages_raw:
        pages_to_capture = DEFAULT_PAGES_TO_CAPTURE
    else:
        try:
            pages_to_capture = max(1, min(10, int(pages_raw)))
        except ValueError:
            print("Invalid number. Using default 2 pages.")
            pages_to_capture = DEFAULT_PAGES_TO_CAPTURE

    diag_event("capture_config", pages_to_capture=pages_to_capture, results_per_page=RESULTS_PER_PAGE, max_viewports=MAX_VIEWPORTS, raw_phase_prompt=True)

    confirm = input(f"Run ID capture for {pages_to_capture} page(s) now? [Y/n]: ").strip().lower()
    diag_event("user_confirmation", confirmed=(confirm != "n"), raw_response=confirm)
    if confirm == "n":
        print("Cancelled.")
        diag_event("capture_cancelled")
        return 0

    for i in range(COUNTDOWN_SECONDS, 0, -1):
        print(f"Starting in {i}...")
        time.sleep(1)

    hwnd, window_title, window_rect, mouse_xy = get_window_from_mouse()
    if "linkedin" not in window_title.lower():
        print("")
        print(f"WARNING: Detected window title does not look like LinkedIn: {window_title!r}")
        return 2

    force_foreground(hwnd)

    diag_event("window_detected", title=window_title, rect=window_rect, mouse_xy=mouse_xy)
    starting_url = copy_current_url(hwnd)
    base_results_url = set_url_start_for_results_page(starting_url, 0)
    print("")
    print(f"Starting URL: {starting_url}")
    print(f"v24 base results URL: {base_results_url}")
    diag_event("starting_url", starting_url=starting_url, base_results_url=base_results_url)

    records: List[IdRecord] = []
    seen_job_ids: Dict[str, int] = {}
    first_seen_sequence_by_job_id: Dict[str, int] = {}
    sequence = 0
    previous_page_sigs: set[str] = set()

    for page_number in range(1, pages_to_capture + 1):
        target_start = (page_number - 1) * RESULTS_PER_PAGE
        print("")
        print("=" * 64)
        print(f"v24 independent page unit: page {page_number}/{pages_to_capture}, target_start={target_start}")
        print("=" * 64)
        diag_event("page_begin", page_number=page_number, pages_to_capture=pages_to_capture, target_start=target_start)

        if page_number == 1:
            print("Waiting for LinkedIn left list to be ready on page 1...")
            ready = wait_for_left_list_ready(hwnd, window_rect, mouse_xy, 1, run_stamp)
            diag_event("page_ready", page_number=page_number, target_start=target_start, ready=ready)
            if not ready:
                print("PAGE_NOT_READY: page 1 did not become safely usable in time.")
                print("Guardrail: stopping before clicking any cards, because cards without a detected scrollbar/pagination are suspicious.")
                return 3
        else:
            _, window_title, window_rect, _ = get_window_from_mouse()
            transition_ok = open_results_page_direct_v16(
                hwnd=hwnd,
                window_rect=window_rect,
                mouse_xy=mouse_xy,
                run_stamp=run_stamp,
                page_number=page_number,
                target_start=target_start,
                base_url=base_results_url,
                previous_sigs=previous_page_sigs,
            )
            diag_event("page_transition_result", page_number=page_number, target_start=target_start, ok=transition_ok)
            if not transition_ok:
                print("Stopping multi-page capture: direct page open failed before capture.")
                diag_event("multi_page_stop", page_number=page_number, reason="direct_page_open_failed")
                break
            _, window_title, window_rect, _ = get_window_from_mouse()
            print(f"Waiting for LinkedIn left list to be ready on page {page_number} after direct page open...")
            ready = wait_for_left_list_ready(hwnd, window_rect, mouse_xy, page_number, run_stamp)
            diag_event("page_ready", page_number=page_number, target_start=target_start, ready=ready)
            if not ready:
                print(f"PAGE_NOT_READY: page {page_number} did not show cards or scrollbar in time after direct URL navigation.")
                print("Stopping multi-page capture here. Previous page data remains valid.")
                break

        _, window_title, window_rect, _ = get_window_from_mouse()
        page_start = target_start

        page_result = capture_current_page_ids(
            hwnd=hwnd,
            window_rect=window_rect,
            mouse_xy=mouse_xy,
            run_stamp=run_stamp,
            page_number=page_number,
            page_start=page_start,
            records=records,
            seen_job_ids=seen_job_ids,
            first_seen_sequence_by_job_id=first_seen_sequence_by_job_id,
            sequence_start=sequence,
        )
        sequence = page_result.sequence
        previous_page_sigs = left_panel_signature_set(hwnd)
        diag_event(
            "page_result",
            page_number=page_number,
            page_start=page_start,
            status=page_result.status,
            stop_reason=page_result.stop_reason,
            records_added=page_result.records_added,
            unique_added=page_result.unique_added,
            duplicates_added=page_result.duplicates_added,
            failures_added=page_result.failures_added,
            viewports_scanned=page_result.viewports_scanned,
            allow_next_page=page_result.allow_next_page,
            visible_sigs_after_capture=len(previous_page_sigs),
        )
        print(f"v24 page {page_number} finished. Stored page_start={page_start}; visible_sigs_after_capture={len(previous_page_sigs)}")

        # v24: if the initial address-bar copy failed, recover the base URL from
        # a captured job URL before trying page 2+. This is especially important
        # for /jobs/collections/remote-jobs/, where the first copy sometimes
        # returned an empty string even though raw captures later had valid URLs.
        if page_number == 1 and not base_results_url and records:
            for rec in records:
                if rec.url and "linkedin.com/jobs" in rec.url:
                    recovered_base_url = set_url_start_for_results_page(rec.url, 0)
                    if recovered_base_url:
                        base_results_url = recovered_base_url
                        print(f"v24 recovered base results URL from first captured record: {base_results_url}")
                        diag_event("base_results_url_recovered", source="first_page_record", base_results_url=base_results_url, source_url=rec.url)
                        break

        if page_number < pages_to_capture and not page_result.allow_next_page:
            if page_result.unique_added >= MIN_UNIQUE_TO_ALLOW_RELAXED_NEXT:
                print("")
                print(
                    f"v24 continue override after page {page_number}: "
                    f"status={page_result.status}, stop_reason={page_result.stop_reason}, "
                    f"unique_added={page_result.unique_added}."
                )
                print("The page captured enough unique jobs, so v24 will continue to the next direct URL page instead of stopping.")
                diag_event("continue_override", page_number=page_number, unique_added=page_result.unique_added, status=page_result.status, stop_reason=page_result.stop_reason)
            else:
                print("")
                print(
                    f"Stopping multi-page capture after page {page_number}: "
                    f"status={page_result.status}, stop_reason={page_result.stop_reason}, "
                    f"unique_added={page_result.unique_added}"
                )
                print("Guardrail: this page did not capture enough unique jobs, so no further direct pages will be attempted.")
                diag_event("multi_page_stop", page_number=page_number, reason="insufficient_unique_jobs", unique_added=page_result.unique_added, status=page_result.status, stop_reason=page_result.stop_reason)
                break

    md_path, csv_path = save_outputs(run_stamp, records, window_title, starting_url, pages_to_capture)

    raw_records: List[RawJobTextRecord] = []
    raw_jsonl_path: Optional[Path] = None
    raw_md_path: Optional[Path] = None

    print("")
    run_raw = input("Run Phase 2 raw text capture now? [y/N]: ").strip().lower()
    if run_raw == "y":
        raw_records = capture_raw_text_phase(hwnd, records, run_stamp)
        raw_jsonl_path, raw_md_path = save_raw_text_outputs(run_stamp, raw_records)
    else:
        print("Skipping Phase 2 raw text capture. ID/URL outputs have been saved.")


    duplicate_records = len([r for r in records if r.status.startswith("DUPLICATE")])
    failures = len([r for r in records if is_failure_status(r.status)])

    print("")
    diag_event("capture_summary", pages_requested=pages_to_capture, total_card_clicks=len(records), unique_current_job_ids=len(seen_job_ids), duplicate_records=duplicate_records, failures=failures, raw_records=len(raw_records), raw_ok=len([r for r in raw_records if r.status in ok_raw_statuses]), text_log=str(DIAG_TEXT_LOG_PATH.resolve()) if DIAG_TEXT_LOG_PATH else "", jsonl_log=str(DIAG_JSONL_LOG_PATH.resolve()) if DIAG_JSONL_LOG_PATH else "")
    print("ID capture complete.")
    print(f"Pages requested: {pages_to_capture}")
    print(f"Total card clicks recorded: {len(records)}")
    print(f"Unique currentJobIds: {len(seen_job_ids)}")
    print(f"Duplicate click records: {duplicate_records}")
    print(f"Failures: {failures}")
    ok_raw_statuses = {"OK_RAW_TEXT", "OK_RAW_TEXT_AFTER_RELOAD"}
    print(f"Raw text captures: {len(raw_records)}")
    print(f"Raw text OK: {len([r for r in raw_records if r.status in ok_raw_statuses])}")
    print("")
    print("Output files:")
    print(f"  Markdown: {md_path.resolve()}")
    print(f"  CSV:      {csv_path.resolve()}")
    if raw_jsonl_path and raw_md_path:
        print(f"  Raw JSONL:{raw_jsonl_path.resolve()}")
        print(f"  Raw MD:   {raw_md_path.resolve()}")
    else:
        print("  Raw JSONL: skipped")
        print("  Raw MD:   skipped")
    print(f"  Debug images folder: {DEBUG_OUTPUT_DIR.resolve()}")
    if DIAG_TEXT_LOG_PATH and DIAG_JSONL_LOG_PATH:
        print(f"  Diagnostic log: {DIAG_TEXT_LOG_PATH.resolve()}")
        print(f"  Diagnostic JSONL: {DIAG_JSONL_LOG_PATH.resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

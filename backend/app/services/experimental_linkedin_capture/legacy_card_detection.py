from dataclasses import dataclass
import re
from typing import Any


_LOCATION_HINTS = (
    "remote",
    "hybrid",
    "on-site",
    "onsite",
    "united states",
    "spain",
    "canada",
    "uk",
    "ireland",
    "germany",
    "france",
)

_STATE_LINES = {
    "viewed",
    "promoted",
    "easy apply",
    "applied",
    "actively reviewing",
    "be an early applicant",
}


@dataclass(frozen=True)
class LegacyLeftPanelCard:
    title: str
    company: str
    location: str
    signature: str
    card_index: int
    click_x: int
    click_y: int
    confidence: float = 0.0
    visibility: str = ""
    reason: str = ""
    fingerprint: str = ""


@dataclass(frozen=True)
class LegacyScreenContext:
    screenshot_width: int = 0
    screenshot_height: int = 0
    active_window_title: str = ""
    active_window_left: int = 0
    active_window_top: int = 0
    active_window_width: int = 0
    active_window_height: int = 0
    mouse_x: int = 0
    mouse_y: int = 0
    screenshot: Any = None


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

    def as_tuple(self) -> tuple[int, int, int, int]:
        return self.left, self.top, self.right, self.bottom

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
class LegacyVisualCard:
    index: int
    rect: Rect
    title: TitleSignal
    click_x: int
    click_y: int
    confidence: float
    reason: str
    visibility: str
    fingerprint: str


NEWLY_REVEALED_BAND_RATIO = 0.42
FOOTER_TOP_PADDING = 18
FOOTER_MIN_Y_RATIO = 0.52


def estimate_cards_from_screen_context(
    context: LegacyScreenContext,
    *,
    max_cards: int,
) -> list[LegacyLeftPanelCard]:
    """Port of legacy v35 visual card detection: ROI -> blue title signals -> card rectangles."""
    if context.screenshot is None:
        return []
    window = Rect(
        context.active_window_left,
        context.active_window_top,
        context.active_window_left + context.active_window_width,
        context.active_window_top + context.active_window_height,
    )
    panel_roi, content_roi, geometry_note = estimate_left_panel_rois(
        window,
        (context.mouse_x, context.mouse_y),
        context.screenshot,
    )
    footer_rect = detect_pagination_footer(context.screenshot, panel_roi)
    card_roi = effective_card_roi(content_roi, footer_rect)
    title_signals = detect_blue_title_signals(context.screenshot, card_roi)
    visual_cards = build_cards_from_title_signals(context.screenshot, card_roi, title_signals)
    candidates = clickable_cards_for_viewport(visual_cards, card_roi, footer_rect is not None, footer_rect)
    mapped: list[LegacyLeftPanelCard] = []
    for card in candidates[:max_cards]:
        mapped.append(
            LegacyLeftPanelCard(
                title=f"visual_title_signal_{card.index}",
                company="",
                location="",
                signature=f"visual_card_{card.fingerprint[:24]}",
                card_index=card.index,
                click_x=card.click_x,
                click_y=card.click_y,
                confidence=card.confidence,
                visibility=card.visibility,
                reason=f"{card.reason}; {geometry_note}; roi={card_roi.describe()}",
                fingerprint=card.fingerprint,
            )
        )
    return mapped


def screen_context_from_pyautogui(py_auto: Any) -> LegacyScreenContext:
    screenshot = py_auto.screenshot()
    screenshot_width, screenshot_height = getattr(screenshot, "size", (0, 0))
    active_window_title = ""
    active_window_left = 0
    active_window_top = 0
    active_window_width = screenshot_width
    active_window_height = screenshot_height
    mouse_x = 0
    mouse_y = 0
    try:
        position = py_auto.position()
        mouse_x = int(position.x)
        mouse_y = int(position.y)
    except Exception:
        pass
    try:
        active_window = py_auto.getActiveWindow()
        if active_window is not None:
            active_window_title = getattr(active_window, "title", "") or ""
            active_window_left = int(getattr(active_window, "left", 0) or 0)
            active_window_top = int(getattr(active_window, "top", 0) or 0)
            active_window_width = int(getattr(active_window, "width", screenshot_width) or screenshot_width)
            active_window_height = int(getattr(active_window, "height", screenshot_height) or screenshot_height)
    except Exception:
        pass
    return LegacyScreenContext(
        screenshot_width=screenshot_width,
        screenshot_height=screenshot_height,
        active_window_title=active_window_title,
        active_window_left=active_window_left,
        active_window_top=active_window_top,
        active_window_width=active_window_width,
        active_window_height=active_window_height,
        mouse_x=mouse_x,
        mouse_y=mouse_y,
        screenshot=screenshot,
    )


def _is_neutral_scroll_pixel(r: int, g: int, b: int) -> bool:
    if max(r, g, b) - min(r, g, b) > 26:
        return False
    return 70 <= r <= 215 and 70 <= g <= 215 and 70 <= b <= 215


def _longest_true_run(flags: list[bool]) -> int:
    best = cur = 0
    for flag in flags:
        if flag:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def estimate_left_panel_roi(window: Rect, mouse_xy: tuple[int, int], screenshot_size: tuple[int, int]) -> Rect:
    sw, sh = screenshot_size
    mx, _ = mouse_xy
    left = max(0, window.left + int(window.width * 0.09))
    mouse_right = mx + 120
    min_right = left + 440
    max_right = window.left + int(window.width * 0.52)
    right = min(max(mouse_right, min_right), max_right, sw)
    top = max(0, window.top + int(window.height * 0.21))
    bottom = min(sh, window.bottom - int(window.height * 0.05))
    return Rect(left, top, right, bottom)


def detect_left_panel_scrollbar_rail(img: Any, window: Rect) -> Rect | None:
    rgb = img.convert("RGB")
    px = rgb.load()
    sw, sh = img.size
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
        if longest >= 35 and neutral_count >= 45:
            columns.append((x, neutral_count, longest))
    if not columns:
        return None
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
        if 3 <= width <= 24:
            plausible.append((score + cx * 2, Rect(x1, scan_top, x2, scan_bottom)))
    if not plausible:
        return None
    plausible.sort(key=lambda item: item[0], reverse=True)
    return plausible[0][1]


def estimate_left_panel_rois(window: Rect, mouse_xy: tuple[int, int], img: Any) -> tuple[Rect, Rect, str]:
    sw, sh = img.size
    baseline = estimate_left_panel_roi(window, mouse_xy, img.size)
    rail = detect_left_panel_scrollbar_rail(img, window)
    if rail:
        left = max(0, window.left + int(window.width * 0.09))
        top = max(0, window.top + int(window.height * 0.21))
        bottom = min(sh, window.bottom - int(window.height * 0.05))
        panel_right = min(sw, rail.right + 18)
        content_right = max(left + 300, rail.left - 10)
        panel_roi = Rect(left, top, panel_right, bottom)
        content_roi = Rect(left, top, min(content_right, panel_right), bottom)
        return panel_roi, content_roi, f"visual_rail={rail.describe()}"
    content_right = max(baseline.left + 300, baseline.right - 45)
    content_roi = Rect(baseline.left, baseline.top, min(content_right, baseline.right), baseline.bottom)
    return baseline, content_roi, "visual_rail=none_fallback_v22"


def is_linkedin_blue(r: int, g: int, b: int) -> bool:
    return b >= 105 and g >= 55 and r <= 115 and (b - r) >= 35 and (b - g) >= -5


def is_dark_active_page_pixel(r: int, g: int, b: int) -> bool:
    return r < 55 and g < 55 and b < 55


def detect_pagination_footer(img: Any, roi: Rect) -> Rect | None:
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


def effective_card_roi(roi: Rect, footer_rect: Rect | None) -> Rect:
    if not footer_rect:
        return roi
    new_bottom = max(roi.top + 120, footer_rect.top - FOOTER_TOP_PADDING)
    return Rect(roi.left, roi.top, roi.right, min(roi.bottom, new_bottom))


def detect_blue_title_signals(img: Any, roi: Rect) -> list[TitleSignal]:
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


def average_hash(img: Any, size: tuple[int, int] = (24, 12)) -> str:
    gray = img.convert("L").resize(size)
    values = list(gray.getdata())
    avg = sum(values) / len(values)
    bits = "".join("1" if v < avg else "0" for v in values)
    return f"{int(bits, 2):0{len(bits)//4}x}"


def fingerprint_card(img: Any, roi: Rect, rect: Rect, title: TitleSignal) -> str:
    left = max(roi.left, rect.left + 8)
    top = max(roi.top, title.top - 20)
    right = min(roi.right, rect.right - 18)
    bottom = min(roi.bottom, title.bottom + 90)
    if right <= left or bottom <= top:
        return "bad-fingerprint"
    return average_hash(img.crop((left, top, right, bottom)), (24, 12))


def build_cards_from_title_signals(img: Any, roi: Rect, title_signals: list[TitleSignal]) -> list[LegacyVisualCard]:
    if not title_signals:
        return []
    title_signals = sorted(title_signals, key=lambda s: s.center_y)
    centers = [s.center_y for s in title_signals]
    cards = []
    for i, sig in enumerate(title_signals):
        if i == 0:
            top = max(roi.top, centers[0] - int((centers[1] - centers[0]) * 0.50)) if len(centers) >= 2 else max(roi.top, sig.top - 45)
        else:
            top = (centers[i - 1] + centers[i]) // 2
        if i == len(title_signals) - 1:
            bottom = min(roi.bottom, centers[-1] + int((centers[-1] - centers[-2]) * 0.55)) if len(centers) >= 2 else min(roi.bottom, sig.bottom + 60)
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
        cards.append(LegacyVisualCard(len(cards) + 1, rect, sig, click_x, click_y, confidence, "title-blue-signal", visibility, fp))
    return cards


def clickable_cards_for_viewport(
    cards: list[LegacyVisualCard],
    card_roi: Rect,
    pagination_visible: bool,
    footer_rect: Rect | None,
    *,
    viewport_index: int = 1,
) -> list[LegacyVisualCard]:
    clickable = [c for c in cards if c.visibility == "FULL"]
    existing_keys = {(c.click_x, c.click_y, c.index) for c in clickable}
    for c in cards:
        if c.visibility != "PARTIAL_TOP":
            continue
        safe_top = card_roi.top + 10
        if c.click_y > safe_top and c.title.center_y > safe_top and c.rect.bottom > safe_top + 45:
            key = (c.click_x, c.click_y, c.index)
            if key not in existing_keys:
                clickable.append(c)
                existing_keys.add(key)
    if pagination_visible and footer_rect:
        safe_bottom = footer_rect.top - 18
        for c in cards:
            if c.visibility != "PARTIAL_BOTTOM":
                continue
            if c.click_y < safe_bottom and c.title.center_y < safe_bottom and c.rect.top < safe_bottom - 35:
                key = (c.click_x, c.click_y, c.index)
                if key not in existing_keys:
                    clickable.append(c)
                    existing_keys.add(key)
    if viewport_index > 1:
        cutoff_y = card_roi.top + int(card_roi.height * NEWLY_REVEALED_BAND_RATIO)
        clickable = [c for c in clickable if c.title.center_y >= cutoff_y or c.click_y >= cutoff_y]
    return sorted(clickable, key=lambda c: (c.rect.top, c.index))


def normalize_card_signature(title: str, company: str, location: str) -> str:
    compact = " ".join(f"{company} {title} {location}".lower().split())
    return re.sub(r"[^a-z0-9]+", "|", compact).strip("|")


def parse_left_panel_cards_from_text(raw_text: str, *, max_cards: int = 25) -> list[LegacyLeftPanelCard]:
    """Adapted from legacy parse_left_panel_cards_from_text for copied page text."""
    lines = [_clean_text_line(line) for line in raw_text.splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        return []

    start_index = _left_panel_start(lines)
    cards: list[LegacyLeftPanelCard] = []
    seen: set[str] = set()
    index = start_index
    while index + 2 < len(lines) and len(cards) < max_cards:
        if _is_stop_line(lines[index]):
            break
        if lines[index].lower() == "company logo":
            title_index = index + 1
        else:
            title_index = index

        title = lines[title_index]
        company = lines[title_index + 1] if title_index + 1 < len(lines) else ""
        location = lines[title_index + 2] if title_index + 2 < len(lines) else ""
        if _looks_like_card(title, company, location):
            signature = normalize_card_signature(title, company, location)
            if signature and signature not in seen:
                seen.add(signature)
                card_number = len(cards)
                cards.append(
                    LegacyLeftPanelCard(
                        title=title,
                        company=company,
                        location=location,
                        signature=signature,
                        card_index=card_number,
                        click_x=340,
                        click_y=190 + card_number * 92,
                    )
                )
            index = title_index + 3
            while index < len(lines) and lines[index].lower() in _STATE_LINES:
                index += 1
            continue
        index += 1
    return cards


def _clean_text_line(line: str) -> str:
    return " ".join(line.replace("\xa0", " ").split())


def _left_panel_start(lines: list[str]) -> int:
    for index, line in enumerate(lines[:80]):
        lowered = line.lower()
        if " results" in lowered or "resultados" in lowered:
            return index + 1
    return 0


def _looks_like_card(title: str, company: str, location: str) -> bool:
    if len(title) < 3 or len(company) < 2 or len(location) < 2:
        return False
    lowered = f"{title} {company} {location}".lower()
    if any(marker in lowered for marker in ("about the job", "job details", "show more")):
        return False
    return _is_left_panel_location(location) or len(cards_words(title, company, location)) >= 6


def _is_left_panel_location(line: str) -> bool:
    lowered = line.lower()
    return any(hint in lowered for hint in _LOCATION_HINTS) or bool(re.search(r",\s*[A-Z]{2}\b", line))


def _is_stop_line(line: str) -> bool:
    lowered = line.lower()
    return any(
        marker in lowered
        for marker in (
            "are these results helpful",
            "about the job",
            "recommended jobs",
            "similar jobs",
            "jobs you may be interested",
        )
    )


def cards_words(*parts: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9]+", " ".join(parts))

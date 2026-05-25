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


@dataclass(frozen=True)
class LegacyScreenContext:
    screenshot_width: int = 0
    screenshot_height: int = 0
    active_window_title: str = ""
    active_window_left: int = 0
    active_window_top: int = 0
    active_window_width: int = 0
    active_window_height: int = 0


def estimate_cards_from_screen_context(
    context: LegacyScreenContext,
    *,
    max_cards: int,
) -> list[LegacyLeftPanelCard]:
    """Generate left-panel click candidates before clipboard text capture.

    The legacy tool used screenshot/pixel card rectangles. Phase 18A keeps that
    ordering and produces conservative candidates from active-window geometry so
    Ctrl+A is not sent until after a card click.
    """
    width = context.active_window_width or context.screenshot_width
    height = context.active_window_height or context.screenshot_height
    if width < 700 or height < 500:
        return []

    left = context.active_window_left
    top = context.active_window_top
    click_x = left + max(250, min(430, int(width * 0.22)))
    first_y = top + max(180, int(height * 0.20))
    spacing = 96
    bottom_limit = top + height - 120
    candidates: list[LegacyLeftPanelCard] = []
    for index in range(max_cards):
        click_y = first_y + index * spacing
        if click_y >= bottom_limit:
            break
        candidates.append(
            LegacyLeftPanelCard(
                title=f"visible_card_candidate_{index + 1}",
                company="",
                location="",
                signature=f"screen_candidate_{index + 1}_{click_x}_{click_y}",
                card_index=index,
                click_x=click_x,
                click_y=click_y,
            )
        )
    return candidates


def screen_context_from_pyautogui(py_auto: Any) -> LegacyScreenContext:
    screenshot = py_auto.screenshot()
    screenshot_width, screenshot_height = getattr(screenshot, "size", (0, 0))
    active_window_title = ""
    active_window_left = 0
    active_window_top = 0
    active_window_width = screenshot_width
    active_window_height = screenshot_height
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
    )


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

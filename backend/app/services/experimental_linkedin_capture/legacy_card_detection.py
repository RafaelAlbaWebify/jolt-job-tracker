from dataclasses import dataclass
import re


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

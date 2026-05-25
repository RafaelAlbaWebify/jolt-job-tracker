import html
import re

from app.models import CaptureDiagnostics, CaptureRunRequest, CapturedRawJob

FIELD_LABELS = r"job\s+title|title|role|company|employer|organization|organisation|location|office|based in|work\s+mode|url|link"
TITLE_PATTERN = re.compile(r"^(?:job\s+title|title|role)\s*[:\-]\s*(.+)$", re.IGNORECASE | re.MULTILINE)
COMPANY_PATTERN = re.compile(
    r"^(?:company|employer|organization|organisation)\s*[:\-]\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)
LOCATION_PATTERN = re.compile(r"^(?:location|office|based in)\s*[:\-]\s*(.+)$", re.IGNORECASE | re.MULTILINE)
WORK_MODE_PATTERN = re.compile(r"^(?:work\s+mode)\s*[:\-]\s*(.+)$", re.IGNORECASE | re.MULTILINE)
URL_FIELD_PATTERN = re.compile(r"^(?:url|link)\s*[:\-]\s*(https?://[^\s\"'<>]+)", re.IGNORECASE | re.MULTILINE)
LINK_PATTERN = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
ANCHOR_PATTERN = re.compile(
    r"<a\b[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>",
    re.IGNORECASE | re.DOTALL,
)
HTML_NOISE_PATTERN = re.compile(
    r"<(script|style|nav|footer|header|aside)[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)
ARTICLE_BOUNDARY_PATTERN = re.compile(r"</?(?:article|section|li)\b[^>]*>", re.IGNORECASE)
LINE_BREAK_TAG_PATTERN = re.compile(r"</?(?:br|p|div|h[1-6])\b[^>]*>", re.IGNORECASE)
TAG_PATTERN = re.compile(r"<[^>]+>")
TITLE_START_PATTERN = re.compile(rf"^(?:job\s+title|title|role)\s*[:\-]", re.IGNORECASE)
SEPARATOR_LINE_PATTERN = re.compile(
    r"^(?:-{3,}|job\s*(?:card|listing)?\s*\d*|listing\s*\d*)$",
    re.IGNORECASE,
)
NOISE_LINE_PATTERN = re.compile(r"^(?:view\s+job|apply|promoted|easy\s+apply|actively\s+recruiting)$", re.IGNORECASE)
LEFT_PANEL_STOP_LINES = {
    "are these results helpful?",
    "your feedback helps us improve job recommendations.",
    "next",
    "previous",
    "about",
    "accessibility",
    "help center",
}
LEFT_PANEL_STATE_MARKERS = (
    "actively reviewing applicants",
    "viewed",
    "promoted",
    "easy apply",
    "applied",
    "be an early applicant",
    "company review time",
)

ROLE_WORDS = (
    "administrator",
    "analyst",
    "consultant",
    "developer",
    "engineer",
    "manager",
    "specialist",
    "support",
    "technician",
)
LOCATION_WORDS = (
    "barcelona",
    "hybrid",
    "madrid",
    "on-site",
    "onsite",
    "remote",
    "spain",
    "vigo",
    "portugal",
    "lisbon",
    "europe",
    "ireland",
    "dublin",
    "france",
    "paris",
    "germany",
)
JOB_LINK_HINTS = ("job", "jobs", "career", "careers", "position", "posting", "view")


def _looks_like_html(content: str) -> bool:
    return bool(re.search(r"</?(?:html|body|article|section|div|li|a|p|br|h[1-6])\b", content, re.IGNORECASE))


def _anchor_replacement(match: re.Match[str]) -> str:
    href = match.group(1).strip()
    label = _strip_tags(match.group(2))
    parts = [label] if label else []
    if href:
        parts.append(f"URL: {href}")
    return "\n".join(parts)


def _strip_tags(content: str) -> str:
    return html.unescape(TAG_PATTERN.sub(" ", content))


def _strip_html(content: str) -> str:
    without_noise = HTML_NOISE_PATTERN.sub("\n", content)
    with_anchor_urls = ANCHOR_PATTERN.sub(_anchor_replacement, without_noise)
    with_article_breaks = ARTICLE_BOUNDARY_PATTERN.sub("\n---\n", with_anchor_urls)
    with_line_breaks = LINE_BREAK_TAG_PATTERN.sub("\n", with_article_breaks)
    without_tags = TAG_PATTERN.sub(" ", with_line_breaks)
    return html.unescape(without_tags)


def _normalize_lines(content: str) -> list[str]:
    lines = [" ".join(line.strip().split()) for line in content.replace("\r\n", "\n").split("\n")]
    return [line for line in lines if line]


def _normalize_text(content: str) -> str:
    return "\n".join(_normalize_lines(content)).strip()


def _extract_field(pattern: re.Pattern[str], text: str) -> str:
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def _clean_url(url: str) -> str:
    return url.rstrip(").,]")


def _links_in_block(block: str) -> list[str]:
    links: list[str] = []
    for pattern in (URL_FIELD_PATTERN, LINK_PATTERN):
        for match in pattern.finditer(block):
            value = _clean_url(match.group(1) if pattern is URL_FIELD_PATTERN else match.group(0))
            if value and value not in links:
                links.append(value)
    return links


def _source_url_for_block(block: str, fallback_url: str) -> tuple[str, list[str]]:
    links = _links_in_block(block)
    if not links:
        return fallback_url, ["Used supplied source URL as fallback."] if fallback_url else []

    likely_links = [link for link in links if any(hint in link.lower() for hint in JOB_LINK_HINTS)]
    selected = likely_links[0] if likely_links else links[0]
    notes = ["Source URL inferred from block."]
    if len(links) > 1:
        notes.append("Multiple links found; selected the first likely job link.")
    return selected, notes


def _label_count(block: str) -> int:
    return sum(
        1
        for pattern in [TITLE_PATTERN, COMPANY_PATTERN, LOCATION_PATTERN, WORK_MODE_PATTERN, URL_FIELD_PATTERN]
        if pattern.search(block)
    )


def _has_job_shape(block: str) -> bool:
    return _label_count(block) >= 2


def _looks_like_role(line: str) -> bool:
    lower = line.lower()
    return any(word in lower for word in ROLE_WORDS) and not LINK_PATTERN.search(line)


def _looks_like_location(line: str) -> bool:
    lower = line.lower()
    return any(word in lower for word in LOCATION_WORDS) or bool(
        re.search(r"\((remote|hybrid|on-site|onsite)\)", lower)
    )


def _is_noise_line(line: str) -> bool:
    return bool(SEPARATOR_LINE_PATTERN.match(line) or NOISE_LINE_PATTERN.match(line))


def _is_useful_block(block: str) -> bool:
    if _has_job_shape(block):
        return True
    words = re.findall(r"\w+", block)
    lines = _normalize_lines(block)
    return len(words) >= 18 and any(_looks_like_role(line) for line in lines)


def _split_on_separator_lines(lines: list[str]) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []
    for line in lines:
        if SEPARATOR_LINE_PATTERN.match(line):
            if current:
                blocks.append("\n".join(current).strip())
                current = []
            continue
        if NOISE_LINE_PATTERN.match(line):
            continue
        current.append(line)
    if current:
        blocks.append("\n".join(current).strip())
    return [block for block in blocks if block]


def _split_candidates_on_separator_lines(lines: list[str]) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []
    for line in lines:
        if SEPARATOR_LINE_PATTERN.match(line):
            if current:
                blocks.append("\n".join(current).strip())
                current = []
            continue
        current.append(line)
    if current:
        blocks.append("\n".join(current).strip())
    return [block for block in blocks if block]


def _split_on_repeated_titles(text: str) -> list[str]:
    matches = list(TITLE_START_PATTERN.finditer(text))
    if len(matches) < 2:
        return []

    blocks: list[str] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[start:end].strip()
        if block:
            blocks.append(block)
    return blocks


def _split_compact_blocks(lines: list[str]) -> list[str]:
    starts: list[int] = []
    for index in range(len(lines) - 2):
        if _looks_like_role(lines[index]) and not _is_noise_line(lines[index + 1]) and _looks_like_location(lines[index + 2]):
            starts.append(index)

    if len(starts) < 2:
        return []

    blocks: list[str] = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(lines)
        chunk = lines[start:end]
        if len(chunk) >= 3:
            labelled = [
                f"Title: {chunk[0]}",
                f"Company: {chunk[1]}",
                f"Location: {chunk[2]}",
                *chunk[3:],
            ]
            blocks.append("\n".join(labelled).strip())
    return blocks


def _normalize_signature(title: str, company: str, location: str) -> str:
    base = f"{company}|{title}|{location}".lower().replace("&", " and ")
    base = re.sub(r"[^a-z0-9]+", " ", base)
    return re.sub(r"\s+", " ", base).strip()


def _extract_left_panel_style_blocks(lines: list[str]) -> list[tuple[str, list[str]]]:
    blocks: list[tuple[str, list[str]]] = []
    seen: set[str] = set()
    start = 0
    for index, line in enumerate(lines):
        if re.search(r"\b\d+\s+results\b", line.lower()):
            start = index + 1
            break

    index = start
    while index < len(lines) - 3:
        line = lines[index]
        lower = line.lower()
        if lower in LEFT_PANEL_STOP_LINES or lower.startswith("are you finding what"):
            break
        if line.lower().endswith(" logo") and index + 3 < len(lines):
            title = lines[index + 1]
            company = lines[index + 2]
            location = lines[index + 3]
            if _looks_like_role(title) and _looks_like_location(location):
                state_lines: list[str] = []
                cursor = index + 4
                while cursor < len(lines):
                    next_line = lines[cursor]
                    next_lower = next_line.lower()
                    if next_lower.endswith(" logo") or next_lower in LEFT_PANEL_STOP_LINES:
                        break
                    if any(marker in next_lower for marker in LEFT_PANEL_STATE_MARKERS):
                        state_lines.append(next_line)
                    cursor += 1

                signature = _normalize_signature(title, company, location)
                if signature and signature not in seen:
                    seen.add(signature)
                    workplace_match = re.search(r"\((Remote|Hybrid|On-site|Onsite)\)", location, flags=re.IGNORECASE)
                    workplace = workplace_match.group(1).replace("Onsite", "On-site") if workplace_match else ""
                    block_lines = [
                        f"Title: {title}",
                        f"Company: {company}",
                        f"Location: {location}",
                    ]
                    if workplace:
                        block_lines.append(f"Work mode: {workplace}")
                    if state_lines:
                        block_lines.append("Card state: " + "; ".join(dict.fromkeys(state_lines)))
                    notes = ["Extracted from copied left-panel style card text."]
                    if state_lines:
                        notes.append("Card state markers preserved for review.")
                    blocks.append(("\n".join(block_lines), notes))
                index = max(cursor, index + 4)
                continue
        index += 1

    return blocks


def _dedupe_blocks(blocks: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for block in blocks:
        key = re.sub(r"\s+", " ", block).strip().lower()
        if key and key not in seen:
            seen.add(key)
            result.append(block)
    return result


def _capture_confidence(accepted_count: int, rejected_count: int, fallback_used: bool) -> str:
    if fallback_used:
        return "low"
    if accepted_count > 0 and rejected_count == 0:
        return "high"
    return "medium"


def _extract_blocks(text: str, is_html: bool) -> tuple[list[tuple[str, list[str]]], list[str], int, int, list[str]]:
    lines = _normalize_lines(text)
    warnings: list[str] = []
    rejection_reasons: list[str] = []

    separated_blocks = _split_candidates_on_separator_lines(lines)
    if len(separated_blocks) > 1:
        accepted: list[tuple[str, list[str]]] = []
        rejected_count = 0
        for block in _dedupe_blocks(separated_blocks):
            if _is_useful_block(block):
                note = (
                    "Extracted from HTML block."
                    if is_html
                    else "Extracted from labelled job block."
                    if _has_job_shape(block)
                    else "Extracted from separated job block."
                )
                accepted.append((block, [note]))
            else:
                rejected_count += 1
                rejection_reasons.append("Rejected short/noisy candidate card from separated page text.")

        if accepted:
            if rejected_count:
                warnings.append(f"Rejected {rejected_count} short/noisy candidate card(s).")
            return accepted, warnings, len(separated_blocks), rejected_count, rejection_reasons

    labelled_blocks = [block for block in _split_on_separator_lines(lines) if _has_job_shape(block)]
    if len(labelled_blocks) > 1:
        note = "Extracted from HTML block." if is_html else "Extracted from labelled job block."
        return [(block, [note]) for block in _dedupe_blocks(labelled_blocks)], warnings, len(labelled_blocks), 0, []

    repeated_title_blocks = [block for block in _split_on_repeated_titles(text) if _has_job_shape(block)]
    if len(repeated_title_blocks) > 1:
        note = "Extracted from HTML block." if is_html else "Extracted from labelled job block."
        return [(block, [note]) for block in _dedupe_blocks(repeated_title_blocks)], warnings, len(repeated_title_blocks), 0, []

    left_panel_blocks = _extract_left_panel_style_blocks(lines)
    if left_panel_blocks:
        return left_panel_blocks, warnings, len(left_panel_blocks), 0, []

    compact_blocks = [block for block in _split_compact_blocks(lines) if _is_useful_block(block)]
    if compact_blocks:
        note = "Extracted from HTML block." if is_html else "Extracted from compact job-board-like lines."
        return [(block, [note]) for block in _dedupe_blocks(compact_blocks)], warnings, len(compact_blocks), 0, []

    single_useful_blocks = [block for block in _split_on_separator_lines(lines) if _is_useful_block(block)]
    if len(single_useful_blocks) == 1:
        note = "Extracted from HTML block." if is_html else "Extracted from labelled job block."
        return [(single_useful_blocks[0], [note])], warnings, 1, 0, []

    fallback_text = "\n".join(line for line in lines if not _is_noise_line(line)).strip() or text
    warning = "Page text structure was unclear; captured the full content as one job."
    if len(lines) > 8:
        warning = "Content looked like a full page, but no clear job cards were found; captured one fallback item."
    warnings.append(warning)
    return [(fallback_text, [warning])], warnings, 1, 0, []


def capture_from_page_content(request: CaptureRunRequest) -> tuple[list[CapturedRawJob], list[str], CaptureDiagnostics]:
    raw_content = request.uploaded_html_content.strip() or request.html_content.strip() or request.page_text.strip()
    diagnostics = CaptureDiagnostics(
        capture_mode_used=request.capture_mode,
        input_size=len(raw_content),
        warnings=[],
    )
    if not raw_content:
        warning = "No page_text, html_content, or uploaded_html_content was provided for capture extraction."
        diagnostics.warnings.append(warning)
        diagnostics.capture_confidence = "low"
        return [], [warning], diagnostics

    is_html = bool(request.html_content.strip() or request.uploaded_html_content.strip() or request.capture_mode in {"html_fragment", "uploaded_html_content"}) or _looks_like_html(raw_content)
    normalized = _normalize_text(_strip_html(raw_content) if is_html else raw_content)
    if not normalized:
        warning = "Page content was empty after normalization."
        diagnostics.warnings.append(warning)
        diagnostics.capture_confidence = "low"
        return [], [warning], diagnostics

    blocks_with_notes, warnings, candidate_count, rejected_count, rejection_reasons = _extract_blocks(normalized, is_html)
    diagnostics.candidate_cards_found = candidate_count
    diagnostics.cards_rejected = rejected_count
    diagnostics.rejection_reasons = rejection_reasons
    if request.max_results < 1:
        warning = "max_results was below 1; no page text jobs were processed."
        diagnostics.warnings.extend([*warnings, warning])
        diagnostics.capture_confidence = "low"
        return [], [warning], diagnostics

    if len(blocks_with_notes) > request.max_results:
        max_note = (
            f"page_text extraction found {len(blocks_with_notes)} item(s); "
            f"only the first {request.max_results} were processed."
        )
        warnings.append(max_note)
        diagnostics.warnings.append(max_note)
        blocks_with_notes = blocks_with_notes[: request.max_results]
        blocks_with_notes = [
            (block, [*notes, "max_results applied; additional extracted jobs were skipped."])
            for block, notes in blocks_with_notes
        ]

    raw_jobs: list[CapturedRawJob] = []
    for index, (block, block_notes) in enumerate(blocks_with_notes, start=1):
        notes = ["Captured from pasted page text/HTML.", *block_notes]

        title = _extract_field(TITLE_PATTERN, block)
        company = _extract_field(COMPANY_PATTERN, block)
        location = _extract_field(LOCATION_PATTERN, block)
        if title or company or location:
            hints = [
                f"title={title}" if title else "",
                f"company={company}" if company else "",
                f"location={location}" if location else "",
            ]
            notes.append("Extractor hints: " + ", ".join(value for value in hints if value))

        source_url, url_notes = _source_url_for_block(block, request.source_url)
        notes.extend(url_notes)
        diagnostics.source_url_extraction_notes.extend(url_notes)

        raw_jobs.append(
            CapturedRawJob(
                source=request.source or "page_text",
                source_url=source_url,
                raw_text=block,
                external_id=f"page_text_{index}",
                capture_notes=notes,
            )
        )

    diagnostics.cards_accepted = len(raw_jobs)
    diagnostics.capture_confidence = _capture_confidence(
        diagnostics.cards_accepted,
        diagnostics.cards_rejected,
        any("fallback" in warning.lower() or "unclear" in warning.lower() for warning in warnings),
    )
    diagnostics.warnings.extend(warnings)
    return raw_jobs, warnings, diagnostics

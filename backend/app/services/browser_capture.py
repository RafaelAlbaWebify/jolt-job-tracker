import html
import re

from app.models import CaptureRunRequest, CapturedRawJob

JOB_BLOCK_SEPARATOR = re.compile(
    r"(?:^|\n)\s*(?:---+\s*)?(?:job\s*(?:card|listing)?|listing)\s*\d*\s*(?:---+)?\s*(?:\n|$)",
    re.IGNORECASE,
)
TITLE_PATTERN = re.compile(r"^(?:job\s+title|title|role)\s*[:\-]\s*(.+)$", re.IGNORECASE | re.MULTILINE)
COMPANY_PATTERN = re.compile(r"^(?:company|employer|organization|organisation)\s*[:\-]\s*(.+)$", re.IGNORECASE | re.MULTILINE)
LOCATION_PATTERN = re.compile(r"^(?:location|office|based in)\s*[:\-]\s*(.+)$", re.IGNORECASE | re.MULTILINE)
LINK_PATTERN = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)


def _strip_html(content: str) -> str:
    without_scripts = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", content, flags=re.IGNORECASE | re.DOTALL)
    with_line_breaks = re.sub(r"</(?:p|div|section|article|li|h[1-6]|br)>", "\n", without_scripts, flags=re.IGNORECASE)
    without_tags = re.sub(r"<[^>]+>", " ", with_line_breaks)
    return html.unescape(without_tags)


def _normalize_text(content: str) -> str:
    lines = [" ".join(line.strip().split()) for line in content.replace("\r\n", "\n").split("\n")]
    compact_lines = [line for line in lines if line]
    return "\n".join(compact_lines).strip()


def _extract_field(pattern: re.Pattern[str], text: str) -> str:
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def _source_url_for_block(block: str, fallback_url: str) -> str:
    match = LINK_PATTERN.search(block)
    return match.group(0).rstrip(").,") if match else fallback_url


def _has_job_shape(block: str) -> bool:
    field_hits = sum(
        1
        for pattern in [TITLE_PATTERN, COMPANY_PATTERN, LOCATION_PATTERN]
        if pattern.search(block)
    )
    return field_hits >= 2


def _split_blocks(text: str) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    separated = [block.strip() for block in JOB_BLOCK_SEPARATOR.split(text) if block.strip()]
    shaped_blocks = [block for block in separated if _has_job_shape(block)]
    if len(shaped_blocks) > 1:
        return shaped_blocks, warnings

    title_matches = list(TITLE_PATTERN.finditer(text))
    if len(title_matches) > 1:
        blocks: list[str] = []
        for index, match in enumerate(title_matches):
            start = match.start()
            end = title_matches[index + 1].start() if index + 1 < len(title_matches) else len(text)
            block = text[start:end].strip()
            if block:
                blocks.append(block)
        return blocks, warnings

    warnings.append("Page text structure was unclear; captured the full content as one job.")
    return [text], warnings


def capture_from_page_content(request: CaptureRunRequest) -> tuple[list[CapturedRawJob], list[str]]:
    source_content = request.html_content.strip() or request.page_text.strip()
    if not source_content:
        return [], ["No page_text or html_content was provided for page_text capture mode."]

    normalized = _normalize_text(_strip_html(source_content) if request.html_content.strip() else source_content)
    if not normalized:
        return [], ["Page content was empty after normalization."]

    blocks, warnings = _split_blocks(normalized)
    raw_jobs: list[CapturedRawJob] = []
    for index, block in enumerate(blocks[: max(request.max_results, 0)], start=1):
        notes = ["Captured from pasted page text/HTML."]
        if warnings:
            notes.extend(warnings)

        title = _extract_field(TITLE_PATTERN, block)
        company = _extract_field(COMPANY_PATTERN, block)
        location = _extract_field(LOCATION_PATTERN, block)
        if title or company or location:
            notes.append(
                "Extractor hints: "
                + ", ".join(
                    value for value in [f"title={title}" if title else "", f"company={company}" if company else "", f"location={location}" if location else ""] if value
                )
            )

        raw_jobs.append(
            CapturedRawJob(
                source=request.source or "page_text",
                source_url=_source_url_for_block(block, request.source_url),
                raw_text=block,
                external_id=f"page_text_{index}",
                capture_notes=notes,
            )
        )

    if len(blocks) > request.max_results:
        warnings.append(
            f"page_text extraction found {len(blocks)} item(s); only the first {request.max_results} were processed."
        )

    return raw_jobs, warnings

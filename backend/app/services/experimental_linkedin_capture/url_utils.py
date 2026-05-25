from urllib.parse import parse_qs, urlparse


_VIEW_ID_MARKERS = (
    "/jobs/view/",
    "/jobs/collections/",
)


def extract_current_job_id(url: str | None) -> str | None:
    """Extract LinkedIn currentJobId from query parameters."""
    if not url:
        return None
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return None
    values = parse_qs(parsed.query).get("currentJobId", [])
    for value in values:
        if value and value.isdigit():
            return value
    return None


def extract_linkedin_job_id(url: str | None) -> str | None:
    """Extract a stable LinkedIn job id from common job URL variants."""
    current_job_id = extract_current_job_id(url)
    if current_job_id:
        return current_job_id
    if not url:
        return None
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return None
    if "linkedin." not in parsed.netloc.lower():
        return None

    path_parts = [part for part in parsed.path.split("/") if part]
    if "view" in path_parts:
        view_index = path_parts.index("view")
        if view_index + 1 < len(path_parts):
            candidate = path_parts[view_index + 1]
            if candidate.isdigit():
                return candidate
            if "jobPosting:" in candidate:
                suffix = candidate.rsplit("jobPosting:", 1)[-1]
                if suffix.isdigit():
                    return suffix
    return None


def normalize_linkedin_job_url(url: str | None) -> str:
    """Return a stable URL for identity comparison without preserving tracking noise."""
    if not url:
        return ""
    raw_url = url.strip()
    if not raw_url:
        return ""
    job_id = extract_linkedin_job_id(raw_url)
    if job_id:
        return f"https://www.linkedin.com/jobs/view/{job_id}/"
    try:
        parsed = urlparse(raw_url)
    except ValueError:
        return raw_url
    if not parsed.scheme or not parsed.netloc:
        return raw_url
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/") or "/"
    return f"{scheme}://{netloc}{path}"


def same_linkedin_job(left_url: str | None, right_url: str | None) -> bool:
    left_id = extract_linkedin_job_id(left_url)
    right_id = extract_linkedin_job_id(right_url)
    if left_id and right_id:
        return left_id == right_id
    left_normalized = normalize_linkedin_job_url(left_url)
    right_normalized = normalize_linkedin_job_url(right_url)
    return bool(left_normalized and right_normalized and left_normalized == right_normalized)


def is_duplicate_job_reference(
    *,
    source_url: str | None = None,
    current_job_id: str | None = None,
    seen_urls: set[str] | None = None,
    seen_job_ids: set[str] | None = None,
) -> bool:
    job_id = current_job_id or extract_linkedin_job_id(source_url)
    if job_id and seen_job_ids and job_id in seen_job_ids:
        return True
    normalized_url = normalize_linkedin_job_url(source_url)
    return bool(normalized_url and seen_urls and normalized_url in seen_urls)


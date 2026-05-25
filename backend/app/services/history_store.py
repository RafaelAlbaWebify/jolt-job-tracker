import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import uuid4

from app.models import (
    ApplicationStatus,
    CaptureRunResult,
    CapturedRawJob,
    HistoryJobEntry,
    NormalizedJob,
    SaveCaptureResultHistoryResponse,
)

BACKEND_ROOT = Path(__file__).resolve().parents[2]
HISTORY_ROOT = BACKEND_ROOT / "data" / "history"
HISTORY_FILE = HISTORY_ROOT / "jobs.jsonl"
LEGACY_NEW_STATUSES = {"", "not started", "new", "watchlist"}
REVIEWED_STATUSES = {
    "applied",
    "waiting",
    "follow up",
    "interview",
    "rejected",
    "discarded",
    "archived",
    "duplicate",
    "already reviewed",
}
LEGACY_STATUS_MAP: dict[str, ApplicationStatus] = {
    "": "New",
    "not started": "New",
    "watchlist": "Follow Up",
    "discarded": "Rejected",
    "interview": "Waiting",
}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _normalize(value: str) -> str:
    return " ".join(value.lower().strip().split())


def _normalize_url(value: str) -> str:
    if not value:
        return ""
    try:
        parts = urlsplit(value.strip())
    except ValueError:
        return value.strip()
    query = [
        (key, val)
        for key, val in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in {"trk", "ref", "refid"}
    ]
    normalized = parts._replace(query=urlencode(query, doseq=True), fragment="")
    return urlunsplit(normalized).rstrip("/")


def _fallback_key(entry: HistoryJobEntry) -> str:
    return "|".join([_normalize(entry.title), _normalize(entry.company), _normalize(entry.location)])


def _title_company_key(title: str, company: str) -> str:
    return "|".join([_normalize(title), _normalize(company)])


def _is_reviewed_status(status: str) -> bool:
    normalized = _normalize(status)
    return bool(normalized and normalized not in LEGACY_NEW_STATUSES) or normalized in REVIEWED_STATUSES


def normalize_application_status(status: str) -> ApplicationStatus:
    normalized = _normalize(status)
    return LEGACY_STATUS_MAP.get(normalized, status)  # type: ignore[return-value]


def _same_job(existing: HistoryJobEntry, candidate: HistoryJobEntry) -> bool:
    if candidate.source_url and _normalize_url(existing.source_url) == _normalize_url(candidate.source_url):
        return True
    if candidate.external_id and existing.external_id == candidate.external_id:
        return True
    if candidate.title and candidate.company and _fallback_key(existing) == _fallback_key(candidate):
        return True
    return bool(
        candidate.title
        and candidate.company
        and _title_company_key(existing.title, existing.company) == _title_company_key(candidate.title, candidate.company)
    )


def find_duplicate_history_match(
    parsed_job: NormalizedJob,
    raw_job: CapturedRawJob,
) -> tuple[HistoryJobEntry | None, str]:
    source_url = raw_job.source_url or parsed_job.source_url
    external_id = raw_job.external_id or parsed_job.job_id or ""
    fallback_key = "|".join([_normalize(parsed_job.title), _normalize(parsed_job.company), _normalize(parsed_job.location)])
    title_company_key = _title_company_key(parsed_job.title, parsed_job.company)

    for entry in list_history_entries():
        already_reviewed_note = " with an actioned status" if _is_reviewed_status(entry.application_status) else ""
        if source_url and _normalize_url(entry.source_url) == _normalize_url(source_url):
            return entry, f"same source_url as saved history item{already_reviewed_note}"
        if external_id and entry.external_id == external_id:
            return entry, f"same external_id as saved history item{already_reviewed_note}"
        if parsed_job.title and parsed_job.company and _fallback_key(entry) == fallback_key:
            return entry, f"same title, company, and location as saved history item{already_reviewed_note}"
        if parsed_job.title and parsed_job.company and _title_company_key(entry.title, entry.company) == title_company_key:
            return entry, f"same title and company as saved history item{already_reviewed_note}"

    return None, ""


def _ensure_history_root() -> None:
    HISTORY_ROOT.mkdir(parents=True, exist_ok=True)


def _write_entries(entries: list[HistoryJobEntry]) -> None:
    _ensure_history_root()
    payload = "".join(f"{entry.model_dump_json()}\n" for entry in entries)
    HISTORY_FILE.write_text(payload, encoding="utf-8")


def list_history_entries() -> list[HistoryJobEntry]:
    if not HISTORY_FILE.exists():
        return []

    entries: list[HistoryJobEntry] = []
    for line_number, line in enumerate(HISTORY_FILE.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            entry = HistoryJobEntry.model_validate(json.loads(line))
            entries.append(
                entry.model_copy(update={"application_status": normalize_application_status(entry.application_status)})
            )
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"Malformed history record at line {line_number}: {exc}") from exc
    return entries


def get_history_entry(history_id: str) -> HistoryJobEntry | None:
    return next((entry for entry in list_history_entries() if entry.history_id == history_id), None)


def save_capture_result_entries(
    capture_result: CaptureRunResult,
    include_raw_text: bool = False,
    default_application_status: ApplicationStatus = "New",
    include_duplicates: bool = False,
) -> SaveCaptureResultHistoryResponse:
    existing_entries = list_history_entries()
    new_entries: list[HistoryJobEntry] = []
    errors: list[str] = []
    duplicate_count = 0
    skipped_duplicate_count = 0
    already_reviewed_count = 0
    saved_new_count = 0
    normalized_default_status = normalize_application_status(default_application_status)

    for index, result in enumerate(capture_result.results, start=1):
        if result.parsed_job is None or result.decision is None:
            errors.append(f"Result {index} was not saved because it has no parsed job or decision.")
            continue

        raw_text = result.raw_job.raw_text if include_raw_text else None
        candidate = HistoryJobEntry(
            history_id=f"hist_{uuid4().hex}",
            saved_at=_utc_now(),
            run_id=capture_result.run_id,
            profile_id=capture_result.profile_id,
            source=result.raw_job.source,
            source_url=result.raw_job.source_url or result.parsed_job.source_url,
            external_id=result.raw_job.external_id or result.parsed_job.job_id or "",
            title=result.parsed_job.title,
            company=result.parsed_job.company,
            location=result.parsed_job.location,
            work_mode=result.parsed_job.work_mode,
            decision=result.decision.decision,
            priority=result.decision.priority,
            score=result.decision.score,
            parser_confidence=result.decision.parser_confidence,
            reasons=result.decision.reasons,
            warnings=result.decision.warnings,
            missing_information=result.decision.missing_information,
            matched_positive_keywords=result.decision.matched_positive_keywords,
            matched_risk_keywords=result.decision.matched_risk_keywords,
            raw_text_included=include_raw_text,
            raw_text=raw_text,
            application_status=normalized_default_status,
        )

        duplicate_entry = next(
            (existing for existing in [*existing_entries, *new_entries] if _same_job(existing, candidate)),
            None,
        )
        if duplicate_entry is not None:
            duplicate_count += 1
            duplicate_status: ApplicationStatus = (
                "Already Reviewed" if _is_reviewed_status(duplicate_entry.application_status) else "Duplicate"
            )
            if not include_duplicates:
                if duplicate_status == "Already Reviewed":
                    already_reviewed_count += 1
                else:
                    skipped_duplicate_count += 1
                continue
            duplicate_warning = (
                f"Saved as {duplicate_status} because it matches history item {duplicate_entry.history_id}."
            )
            candidate = candidate.model_copy(
                update={
                    "decision": duplicate_status,
                    "application_status": duplicate_status,
                    "warnings": [*candidate.warnings, duplicate_warning],
                }
            )
        else:
            saved_new_count += 1

        new_entries.append(candidate)

    if new_entries:
        _write_entries([*existing_entries, *new_entries])

    return SaveCaptureResultHistoryResponse(
        saved_count=len(new_entries),
        duplicate_count=duplicate_count,
        updated_count=0,
        saved_new_count=saved_new_count,
        skipped_duplicate_count=skipped_duplicate_count,
        already_reviewed_count=already_reviewed_count,
        updated_existing_count=0,
        total_input_count=len(capture_result.results),
        errors=errors,
        history_ids=[entry.history_id for entry in new_entries],
    )


def update_application_status(history_id: str, application_status: ApplicationStatus) -> HistoryJobEntry | None:
    entries = list_history_entries()
    updated_entry: HistoryJobEntry | None = None

    for index, entry in enumerate(entries):
        if entry.history_id == history_id:
            updated_entry = entry.model_copy(update={"application_status": application_status})
            entries[index] = updated_entry
            break

    if updated_entry is None:
        return None

    _write_entries(entries)
    return updated_entry

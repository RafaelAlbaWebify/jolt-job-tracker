import json
from datetime import UTC, datetime
from pathlib import Path
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


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _normalize(value: str) -> str:
    return " ".join(value.lower().strip().split())


def _fallback_key(entry: HistoryJobEntry) -> str:
    return "|".join([_normalize(entry.title), _normalize(entry.company), _normalize(entry.location)])


def _same_job(existing: HistoryJobEntry, candidate: HistoryJobEntry) -> bool:
    if candidate.source_url and existing.source_url == candidate.source_url:
        return True
    if candidate.external_id and existing.external_id == candidate.external_id:
        return True
    return bool(candidate.title and candidate.company and _fallback_key(existing) == _fallback_key(candidate))


def find_duplicate_history_match(
    parsed_job: NormalizedJob,
    raw_job: CapturedRawJob,
) -> tuple[HistoryJobEntry | None, str]:
    source_url = raw_job.source_url or parsed_job.source_url
    external_id = raw_job.external_id or parsed_job.job_id or ""
    fallback_key = "|".join([_normalize(parsed_job.title), _normalize(parsed_job.company), _normalize(parsed_job.location)])

    for entry in list_history_entries():
        if source_url and entry.source_url == source_url:
            return entry, "same source_url as saved history item"
        if external_id and entry.external_id == external_id:
            return entry, "same external_id as saved history item"
        if parsed_job.title and parsed_job.company and _fallback_key(entry) == fallback_key:
            return entry, "same title, company, and location as saved history item"

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
            entries.append(HistoryJobEntry.model_validate(json.loads(line)))
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"Malformed history record at line {line_number}: {exc}") from exc
    return entries


def get_history_entry(history_id: str) -> HistoryJobEntry | None:
    return next((entry for entry in list_history_entries() if entry.history_id == history_id), None)


def save_capture_result_entries(
    capture_result: CaptureRunResult,
    include_raw_text: bool = False,
    default_application_status: ApplicationStatus = "Not started",
) -> SaveCaptureResultHistoryResponse:
    existing_entries = list_history_entries()
    new_entries: list[HistoryJobEntry] = []
    errors: list[str] = []
    duplicate_count = 0

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
            application_status=default_application_status,
        )

        if any(_same_job(existing, candidate) for existing in [*existing_entries, *new_entries]):
            duplicate_count += 1
            continue

        new_entries.append(candidate)

    if new_entries:
        _write_entries([*existing_entries, *new_entries])

    return SaveCaptureResultHistoryResponse(
        saved_count=len(new_entries),
        duplicate_count=duplicate_count,
        updated_count=0,
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

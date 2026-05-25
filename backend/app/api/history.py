from fastapi import APIRouter, HTTPException

from app.models import (
    HistoryJobEntry,
    SaveCaptureResultHistoryRequest,
    SaveCaptureResultHistoryResponse,
    UpdateApplicationStatusRequest,
)
from app.services.history_store import (
    get_history_entry,
    list_history_entries,
    save_capture_result_entries,
    update_application_status,
)

router = APIRouter(prefix="/api/history", tags=["history"])


@router.post("/save-capture-result", response_model=SaveCaptureResultHistoryResponse)
def save_capture_result(request: SaveCaptureResultHistoryRequest) -> SaveCaptureResultHistoryResponse:
    return save_capture_result_entries(
        request.capture_result,
        include_raw_text=request.include_raw_text,
        default_application_status=request.default_application_status,
        include_duplicates=request.include_duplicates,
    )


@router.get("/jobs", response_model=list[HistoryJobEntry])
def list_jobs() -> list[HistoryJobEntry]:
    return list_history_entries()


@router.get("/jobs/{history_id}", response_model=HistoryJobEntry)
def get_job(history_id: str) -> HistoryJobEntry:
    entry = get_history_entry(history_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="History job not found")
    return entry


@router.patch("/jobs/{history_id}/status", response_model=HistoryJobEntry)
def update_job_status(history_id: str, request: UpdateApplicationStatusRequest) -> HistoryJobEntry:
    entry = update_application_status(history_id, request.application_status)
    if entry is None:
        raise HTTPException(status_code=404, detail="History job not found")
    return entry

from fastapi import APIRouter

from app.models import ExportCaptureResultRequest, ExportCaptureResultResponse, ExportHistoryRequest
from app.services.export_package import export_capture_result, export_history_entries
from app.services.history_store import list_history_entries

router = APIRouter(prefix="/api/export", tags=["export"])


@router.post("/capture-result", response_model=ExportCaptureResultResponse)
def export_capture_review_result(request: ExportCaptureResultRequest) -> ExportCaptureResultResponse:
    return export_capture_result(
        capture_result=request.capture_result,
        export_format=request.export_format,
        include_raw_text=request.include_raw_text,
    )


@router.post("/history", response_model=ExportCaptureResultResponse)
def export_saved_tracker_history(request: ExportHistoryRequest) -> ExportCaptureResultResponse:
    return export_history_entries(
        entries=list_history_entries(),
        export_format=request.export_format,
        include_raw_text=request.include_raw_text,
    )

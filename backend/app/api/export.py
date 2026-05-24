from fastapi import APIRouter

from app.models import ExportCaptureResultRequest, ExportCaptureResultResponse
from app.services.export_package import export_capture_result

router = APIRouter(prefix="/api/export", tags=["export"])


@router.post("/capture-result", response_model=ExportCaptureResultResponse)
def export_capture_review_result(request: ExportCaptureResultRequest) -> ExportCaptureResultResponse:
    return export_capture_result(
        capture_result=request.capture_result,
        export_format=request.export_format,
        include_raw_text=request.include_raw_text,
    )

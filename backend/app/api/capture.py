from fastapi import APIRouter, HTTPException

from app.models import CaptureHealthStatus, CaptureRunRequest, CaptureRunResult
from app.services.capture_runner import get_capture_health, run_capture
from app.services.profiles import get_profile

router = APIRouter(prefix="/api/capture", tags=["capture"])


@router.get("/health", response_model=CaptureHealthStatus)
def capture_health() -> CaptureHealthStatus:
    return get_capture_health()


@router.post("/run", response_model=CaptureRunResult)
def run_capture_boundary(request: CaptureRunRequest) -> CaptureRunResult:
    profile = get_profile(request.profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    return run_capture(request, profile)

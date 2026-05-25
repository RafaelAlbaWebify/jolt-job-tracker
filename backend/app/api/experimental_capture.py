from fastapi import APIRouter, HTTPException

from app.models import CaptureRunResult
from app.services.experimental_linkedin_capture.models import (
    ExperimentalCaptureReviewRequest,
    ExperimentalCaptureResponse,
    ExperimentalCaptureStartRequest,
)
from app.services.experimental_linkedin_capture.runner import (
    health_response,
    review_latest_capture,
    start_capture,
    status_response,
    stop_capture,
    test_mouse_control,
)
from app.services.profiles import get_profile

router = APIRouter(prefix="/api/experimental-capture/linkedin", tags=["experimental capture"])


@router.get("/health", response_model=ExperimentalCaptureResponse)
def experimental_linkedin_health() -> ExperimentalCaptureResponse:
    return health_response()


@router.post("/start", response_model=ExperimentalCaptureResponse)
def experimental_linkedin_start(request: ExperimentalCaptureStartRequest) -> ExperimentalCaptureResponse:
    return start_capture(request)


@router.post("/stop", response_model=ExperimentalCaptureResponse)
def experimental_linkedin_stop() -> ExperimentalCaptureResponse:
    return stop_capture()


@router.get("/status", response_model=ExperimentalCaptureResponse)
def experimental_linkedin_status() -> ExperimentalCaptureResponse:
    return status_response()


@router.post("/test-mouse-control", response_model=ExperimentalCaptureResponse)
def experimental_linkedin_test_mouse_control() -> ExperimentalCaptureResponse:
    return test_mouse_control()


@router.post("/review-latest", response_model=CaptureRunResult)
def experimental_linkedin_review_latest(request: ExperimentalCaptureReviewRequest) -> CaptureRunResult:
    profile = get_profile(request.profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    try:
        return review_latest_capture(profile)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

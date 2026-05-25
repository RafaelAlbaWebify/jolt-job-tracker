from fastapi import APIRouter

from app.services.experimental_linkedin_capture.models import (
    ExperimentalCaptureResponse,
    ExperimentalCaptureStartRequest,
)
from app.services.experimental_linkedin_capture.runner import (
    health_response,
    start_capture,
    status_response,
    stop_capture,
)

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


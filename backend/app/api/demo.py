from app.models import DemoCleanupResponse
from app.services.demo_cleanup import cleanup_demo_data

from fastapi import APIRouter

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.post("/cleanup", response_model=DemoCleanupResponse)
def cleanup_local_demo_data() -> DemoCleanupResponse:
    return cleanup_demo_data()

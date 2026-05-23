from fastapi import APIRouter, HTTPException

from app.models import ClassifyJobRequest, DecisionResult
from app.services.decision_engine import classify_job
from app.services.profiles import get_profile

router = APIRouter(prefix="/api/classify", tags=["classification"])


@router.post("/job", response_model=DecisionResult)
def classify_single_job(request: ClassifyJobRequest) -> DecisionResult:
    profile = get_profile(request.profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    return classify_job(request.job, profile)

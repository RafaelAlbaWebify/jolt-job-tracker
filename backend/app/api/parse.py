from fastapi import APIRouter, HTTPException

from app.models import (
    NormalizedJob,
    ParseAndClassifyJobRequest,
    ParseAndClassifyJobResult,
    ParseJobRequest,
)
from app.services.decision_engine import classify_job
from app.services.parser import parse_job
from app.services.profiles import get_profile

router = APIRouter(prefix="/api/parse", tags=["parsing"])


@router.post("/job", response_model=NormalizedJob)
def parse_single_job(request: ParseJobRequest) -> NormalizedJob:
    return parse_job(request.raw_text, request.source_url)


@router.post("-and-classify/job", response_model=ParseAndClassifyJobResult)
def parse_and_classify_single_job(request: ParseAndClassifyJobRequest) -> ParseAndClassifyJobResult:
    profile = get_profile(request.profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    job = parse_job(request.raw_text, request.source_url)
    decision = classify_job(job, profile)
    return ParseAndClassifyJobResult(job=job, decision=decision)

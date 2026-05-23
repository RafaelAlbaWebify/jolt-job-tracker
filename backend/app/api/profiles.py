from fastapi import APIRouter, HTTPException

from app.models import RuleProfile, RuleProfileSummary
from app.services.profiles import get_profile, list_profile_summaries

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


@router.get("", response_model=list[RuleProfileSummary])
def list_profiles() -> list[RuleProfileSummary]:
    return list_profile_summaries()


@router.get("/{profile_id}", response_model=RuleProfile)
def read_profile(profile_id: str) -> RuleProfile:
    profile = get_profile(profile_id)

    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    return profile

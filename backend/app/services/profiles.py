import json
from functools import lru_cache
from pathlib import Path

from app.models import RuleProfile, RuleProfileSummary

DEFAULT_PROFILES_PATH = Path(__file__).resolve().parents[1] / "config" / "default_profiles.json"


@lru_cache
def load_profiles() -> dict[str, RuleProfile]:
    with DEFAULT_PROFILES_PATH.open("r", encoding="utf-8") as profile_file:
        raw_profiles = json.load(profile_file)

    profiles = [RuleProfile.model_validate(profile) for profile in raw_profiles]
    return {profile.profile_id: profile for profile in profiles}


def list_profile_summaries() -> list[RuleProfileSummary]:
    return [
        RuleProfileSummary(
            profile_id=profile.profile_id,
            display_name=profile.display_name,
            description=profile.description,
            portfolio_safe=profile.portfolio_safe,
        )
        for profile in load_profiles().values()
    ]


def get_profile(profile_id: str) -> RuleProfile | None:
    return load_profiles().get(profile_id)

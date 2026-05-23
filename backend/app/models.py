from pydantic import BaseModel


class RuleProfile(BaseModel):
    profile_id: str
    display_name: str
    description: str
    accepted_languages: list[str]
    mandatory_language_mode: str
    base_location: str
    max_distance_km_for_hybrid_onsite: int
    remote_ignores_distance: bool
    preferred_work_modes: list[str]
    acceptable_work_modes: list[str]
    positive_keywords: list[str]
    risk_keywords: list[str]
    discard_keywords: list[str]
    stretch_skills: list[str]
    risk_severity_settings: dict[str, str]
    portfolio_safe: bool


class RuleProfileSummary(BaseModel):
    profile_id: str
    display_name: str
    description: str
    portfolio_safe: bool

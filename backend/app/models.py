from typing import Literal

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


DecisionLabel = Literal["Apply", "Maybe", "Discard", "Manual Review", "Duplicate"]
PriorityLabel = Literal["High", "Medium", "Low"]
ParserConfidence = Literal["high", "medium", "low"]


class NormalizedJob(BaseModel):
    job_id: str | None = None
    title: str = ""
    company: str = ""
    location: str = ""
    work_mode: str = "unknown"
    source_url: str = ""
    description: str = ""
    languages_detected: list[str] = []
    mandatory_languages: list[str] = []
    employment_type: str = ""
    shift_indicators: list[str] = []
    on_call_indicators: list[str] = []
    positive_keywords: list[str] = []
    risk_keywords: list[str] = []
    parser_confidence: ParserConfidence = "medium"
    parser_notes: list[str] = []
    already_reviewed: bool = False
    duplicate_of: str | None = None
    distance_km: float | None = None


class DecisionResult(BaseModel):
    decision: DecisionLabel
    score: int
    priority: PriorityLabel
    reasons: list[str]
    triggered_rules: list[str]
    warnings: list[str]
    missing_information: list[str]
    matched_positive_keywords: list[str]
    matched_risk_keywords: list[str]
    parser_confidence: ParserConfidence
    profile_id: str


class ClassifyJobRequest(BaseModel):
    profile_id: str
    job: NormalizedJob


class ParseJobRequest(BaseModel):
    raw_text: str
    source_url: str = ""


class ParseAndClassifyJobRequest(ParseJobRequest):
    profile_id: str


class ParseAndClassifyJobResult(BaseModel):
    job: NormalizedJob
    decision: DecisionResult

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
CaptureRunStatus = Literal["completed", "completed_with_errors", "failed"]
ExportFormat = Literal["json", "csv", "xlsx"]
ExportStatus = Literal["completed", "failed"]


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


class CapturedRawJob(BaseModel):
    source: str = "manual_raw_jobs"
    source_url: str = ""
    raw_text: str = ""
    captured_at: str = ""
    external_id: str = ""
    capture_notes: list[str] = []


class CaptureHealthStatus(BaseModel):
    capture_mode: str = "manual_raw_jobs"
    browser_automation_enabled: bool = False
    last_run_status: str | None = None
    warnings: list[str] = []


class CaptureRunRequest(BaseModel):
    profile_id: str
    source: str = "manual_raw_jobs"
    query: str = ""
    location: str = ""
    work_mode_filter: str = ""
    max_results: int = 25
    dry_run: bool = False
    raw_jobs: list[CapturedRawJob] = []


class CaptureJobResult(BaseModel):
    raw_job: CapturedRawJob
    parsed_job: NormalizedJob | None = None
    decision: DecisionResult | None = None
    errors: list[str] = []


class CaptureRunResult(BaseModel):
    run_id: str
    status: CaptureRunStatus
    profile_id: str
    total_captured: int
    parsed_count: int
    classified_count: int
    failed_count: int
    results: list[CaptureJobResult]
    warnings: list[str]
    capture_health: CaptureHealthStatus


class ExportCaptureResultRequest(BaseModel):
    export_format: ExportFormat
    include_raw_text: bool = False
    capture_result: CaptureRunResult


class ExportCaptureResultResponse(BaseModel):
    export_id: str
    status: ExportStatus
    files: list[str]
    warnings: list[str]

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


DecisionLabel = Literal["Apply", "Maybe", "Discard", "Manual Review", "Duplicate", "Already Reviewed"]
PriorityLabel = Literal["High", "Medium", "Low"]
ParserConfidence = Literal["high", "medium", "low"]
CaptureRunStatus = Literal["completed", "completed_with_errors", "failed"]
CaptureMode = Literal[
    "manual_raw_jobs",
    "page_text",
    "html_fragment",
    "uploaded_html_content",
    "browser_assisted",
]
ExportFormat = Literal["json", "csv", "xlsx"]
ExportStatus = Literal["completed", "failed"]
ApplicationStatus = Literal[
    "New",
    "Apply Today",
    "Manual Review",
    "Waiting",
    "Follow Up",
    "Applied",
    "Rejected",
    "Archived",
    "Duplicate",
    "Already Reviewed",
    "Not started",
    "Interview",
    "Watchlist",
    "Discarded",
]


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
    capture_mode: str = "manual_raw_jobs,page_text,html_fragment,uploaded_html_content"
    browser_automation_enabled: bool = False
    last_run_status: str | None = None
    warnings: list[str] = []


class CaptureDiagnostics(BaseModel):
    capture_mode_used: str
    input_size: int = 0
    candidate_cards_found: int = 0
    cards_accepted: int = 0
    cards_rejected: int = 0
    rejection_reasons: list[str] = []
    source_url_extraction_notes: list[str] = []
    capture_confidence: ParserConfidence = "medium"
    warnings: list[str] = []


class CaptureRunRequest(BaseModel):
    profile_id: str
    capture_mode: CaptureMode = "manual_raw_jobs"
    source: str = "manual_raw_jobs"
    source_url: str = ""
    query: str = ""
    location: str = ""
    work_mode_filter: str = ""
    max_results: int = 25
    dry_run: bool = False
    page_text: str = ""
    html_content: str = ""
    uploaded_html_content: str = ""
    raw_jobs: list[CapturedRawJob] = []


class CaptureJobResult(BaseModel):
    raw_job: CapturedRawJob
    parsed_job: NormalizedJob | None = None
    decision: DecisionResult | None = None
    errors: list[str] = []
    duplicate_preview: bool = False
    duplicate_reason: str = ""
    duplicate_history_id: str = ""


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
    capture_diagnostics: CaptureDiagnostics


class ExportCaptureResultRequest(BaseModel):
    export_format: ExportFormat
    include_raw_text: bool = False
    capture_result: CaptureRunResult


class ExportHistoryRequest(BaseModel):
    export_format: ExportFormat
    include_raw_text: bool = False


class ExportCaptureResultResponse(BaseModel):
    export_id: str
    status: ExportStatus
    files: list[str]
    warnings: list[str]


class HistoryJobEntry(BaseModel):
    history_id: str
    saved_at: str
    run_id: str
    profile_id: str
    source: str
    source_url: str = ""
    external_id: str = ""
    title: str = ""
    company: str = ""
    location: str = ""
    work_mode: str = "unknown"
    decision: DecisionLabel
    priority: PriorityLabel
    score: int
    parser_confidence: ParserConfidence
    reasons: list[str] = []
    warnings: list[str] = []
    missing_information: list[str] = []
    matched_positive_keywords: list[str] = []
    matched_risk_keywords: list[str] = []
    raw_text_included: bool = False
    raw_text: str | None = None
    application_status: ApplicationStatus = "Not started"


class SaveCaptureResultHistoryRequest(BaseModel):
    capture_result: CaptureRunResult
    include_raw_text: bool = False
    default_application_status: ApplicationStatus = "New"
    include_duplicates: bool = False


class SaveCaptureResultHistoryResponse(BaseModel):
    saved_count: int
    duplicate_count: int
    updated_count: int
    saved_new_count: int
    skipped_duplicate_count: int
    already_reviewed_count: int
    updated_existing_count: int
    total_input_count: int
    errors: list[str]
    history_ids: list[str]


class UpdateApplicationStatusRequest(BaseModel):
    application_status: ApplicationStatus


class DemoCleanupResponse(BaseModel):
    status: str
    exports_files_deleted: int
    history_files_deleted: int
    directories_deleted: int
    warnings: list[str]

from typing import Literal

from pydantic import BaseModel, Field


ExperimentalCaptureStatus = Literal["disabled", "idle", "running", "completed", "failed", "stopped"]
ExperimentalCaptureMode = Literal["experimental_local_capture"]
ExperimentalCapturePlatform = Literal["linkedin_jobs"]


class ExperimentalCaptureDiagnostic(BaseModel):
    code: str
    message: str
    level: Literal["info", "warning", "error"] = "info"
    timestamp: str
    details: dict[str, str | int | bool | None] = Field(default_factory=dict)


class ExperimentalCapturedJobRecord(BaseModel):
    sequence: int
    source_url: str = ""
    current_job_id: str | None = None
    title: str = ""
    company: str = ""
    location: str = ""
    raw_text: str = ""
    capture_state: str = "dry_run"
    page_index: int | None = None
    card_index: int | None = None
    duplicate_of: int | None = None
    diagnostics: list[ExperimentalCaptureDiagnostic] = Field(default_factory=list)


class ExperimentalCaptureRunPackage(BaseModel):
    run_id: str
    status: ExperimentalCaptureStatus
    started_at: str | None = None
    finished_at: str | None = None
    source_platform: ExperimentalCapturePlatform = "linkedin_jobs"
    mode: ExperimentalCaptureMode = "experimental_local_capture"
    max_pages: int = 0
    max_jobs: int = 0
    captured_jobs: list[ExperimentalCapturedJobRecord] = Field(default_factory=list)
    diagnostics: list[ExperimentalCaptureDiagnostic] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class ExperimentalCaptureStartRequest(BaseModel):
    max_pages: int = Field(default=1, ge=1, le=10)
    max_jobs: int = Field(default=25, ge=1, le=250)
    dry_run: bool = True


class ExperimentalCaptureResponse(BaseModel):
    enabled: bool
    status: ExperimentalCaptureStatus
    message: str
    run: ExperimentalCaptureRunPackage | None = None
    diagnostics: list[ExperimentalCaptureDiagnostic] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

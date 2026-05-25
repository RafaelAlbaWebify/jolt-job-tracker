export type HealthResponse = {
  status: string;
  service: string;
  message: string;
};

export type RuleProfileSummary = {
  profile_id: string;
  display_name: string;
  description: string;
  portfolio_safe: boolean;
};

export type RuleProfile = RuleProfileSummary & {
  accepted_languages: string[];
  mandatory_language_mode: string;
  base_location: string;
  max_distance_km_for_hybrid_onsite: number;
  remote_ignores_distance: boolean;
  preferred_work_modes: string[];
  acceptable_work_modes: string[];
  positive_keywords: string[];
  risk_keywords: string[];
  discard_keywords: string[];
  stretch_skills: string[];
  risk_severity_settings: Record<string, string>;
};

export type CaptureHealthStatus = {
  capture_mode: string;
  browser_automation_enabled: boolean;
  last_run_status: string | null;
  warnings: string[];
};

export type CaptureDiagnostics = {
  capture_mode_used: string;
  input_size: number;
  candidate_cards_found: number;
  cards_accepted: number;
  cards_rejected: number;
  rejection_reasons: string[];
  source_url_extraction_notes: string[];
  capture_confidence: 'high' | 'medium' | 'low';
  warnings: string[];
};

export type CapturedRawJob = {
  source?: string;
  source_url?: string;
  raw_text: string;
  captured_at?: string;
  external_id?: string;
  capture_notes?: string[];
};

export type NormalizedJob = {
  job_id: string | null;
  title: string;
  company: string;
  location: string;
  work_mode: string;
  source_url: string;
  description: string;
  languages_detected: string[];
  mandatory_languages: string[];
  employment_type: string;
  shift_indicators: string[];
  on_call_indicators: string[];
  positive_keywords: string[];
  risk_keywords: string[];
  parser_confidence: 'high' | 'medium' | 'low';
  parser_notes: string[];
  already_reviewed: boolean;
  duplicate_of: string | null;
  distance_km: number | null;
};

export type DecisionResult = {
  decision: 'Apply' | 'Maybe' | 'Discard' | 'Manual Review' | 'Duplicate' | 'Already Reviewed';
  score: number;
  priority: 'High' | 'Medium' | 'Low';
  reasons: string[];
  triggered_rules: string[];
  warnings: string[];
  missing_information: string[];
  matched_positive_keywords: string[];
  matched_risk_keywords: string[];
  parser_confidence: 'high' | 'medium' | 'low';
  profile_id: string;
};

export type CaptureJobResult = {
  raw_job: CapturedRawJob;
  parsed_job: NormalizedJob | null;
  decision: DecisionResult | null;
  errors: string[];
  duplicate_preview: boolean;
  duplicate_reason: string;
  duplicate_history_id: string;
};

export type CaptureRunRequest = {
  profile_id: string;
  capture_mode?: 'manual_raw_jobs' | 'page_text' | 'html_fragment' | 'uploaded_html_content' | 'browser_assisted';
  source: string;
  source_url?: string;
  query?: string;
  location?: string;
  work_mode_filter?: string;
  max_results?: number;
  dry_run: boolean;
  page_text?: string;
  html_content?: string;
  uploaded_html_content?: string;
  raw_jobs: CapturedRawJob[];
};

export type CaptureRunResult = {
  run_id: string;
  status: 'completed' | 'completed_with_errors' | 'failed';
  profile_id: string;
  total_captured: number;
  parsed_count: number;
  classified_count: number;
  failed_count: number;
  results: CaptureJobResult[];
  warnings: string[];
  capture_health: CaptureHealthStatus;
  capture_diagnostics: CaptureDiagnostics;
};

export type ExportFormat = 'json' | 'csv' | 'xlsx';

export type ExportCaptureResultRequest = {
  export_format: ExportFormat;
  include_raw_text: boolean;
  capture_result: CaptureRunResult;
};

export type ExportHistoryRequest = {
  export_format: ExportFormat;
  include_raw_text: boolean;
};

export type ExportCaptureResultResponse = {
  export_id: string;
  status: 'completed' | 'failed';
  files: string[];
  warnings: string[];
};

export type ApplicationStatus =
  | 'New'
  | 'Apply Today'
  | 'Manual Review'
  | 'Waiting'
  | 'Follow Up'
  | 'Not started'
  | 'Applied'
  | 'Interview'
  | 'Rejected'
  | 'Archived'
  | 'Watchlist'
  | 'Discarded'
  | 'Duplicate'
  | 'Already Reviewed';

export type HistoryJobEntry = {
  history_id: string;
  saved_at: string;
  run_id: string;
  profile_id: string;
  source: string;
  source_url: string;
  external_id: string;
  title: string;
  company: string;
  location: string;
  work_mode: string;
  decision: DecisionResult['decision'];
  priority: DecisionResult['priority'];
  score: number;
  parser_confidence: NormalizedJob['parser_confidence'];
  reasons: string[];
  warnings: string[];
  missing_information: string[];
  matched_positive_keywords: string[];
  matched_risk_keywords: string[];
  raw_text_included: boolean;
  raw_text: string | null;
  application_status: ApplicationStatus;
};

export type SaveCaptureResultHistoryRequest = {
  capture_result: CaptureRunResult;
  include_raw_text: boolean;
  default_application_status?: ApplicationStatus;
  include_duplicates?: boolean;
};

export type SaveCaptureResultHistoryResponse = {
  saved_count: number;
  duplicate_count: number;
  updated_count: number;
  saved_new_count: number;
  skipped_duplicate_count: number;
  already_reviewed_count: number;
  updated_existing_count: number;
  total_input_count: number;
  errors: string[];
  history_ids: string[];
};

export type DemoCleanupResponse = {
  status: string;
  exports_files_deleted: number;
  history_files_deleted: number;
  directories_deleted: number;
  warnings: string[];
};

export type ExperimentalCaptureStatus =
  | 'disabled'
  | 'idle'
  | 'running'
  | 'completed'
  | 'failed'
  | 'stopped';

export type ExperimentalCaptureDiagnostic = {
  code: string;
  message: string;
  level: 'info' | 'warning' | 'error';
  timestamp: string;
  details: Record<string, string | number | boolean | null>;
};

export type ExperimentalCaptureRunPackage = {
  run_id: string;
  status: ExperimentalCaptureStatus;
  started_at: string | null;
  finished_at: string | null;
  source_platform: 'linkedin_jobs';
  mode: 'experimental_local_capture';
  max_pages: number;
  max_jobs: number;
  captured_jobs: unknown[];
  diagnostics: ExperimentalCaptureDiagnostic[];
  warnings: string[];
  errors: string[];
};

export type ExperimentalCaptureResponse = {
  enabled: boolean;
  status: ExperimentalCaptureStatus;
  message: string;
  run: ExperimentalCaptureRunPackage | null;
  diagnostics: ExperimentalCaptureDiagnostic[];
  warnings: string[];
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);

  if (!response.ok) {
    throw new Error(`Request to ${path} failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function fetchBackendHealth(): Promise<HealthResponse> {
  return fetchJson<HealthResponse>('/api/health');
}

export async function fetchProfiles(): Promise<RuleProfileSummary[]> {
  return fetchJson<RuleProfileSummary[]>('/api/profiles');
}

export async function fetchProfile(profileId: string): Promise<RuleProfile> {
  return fetchJson<RuleProfile>(`/api/profiles/${profileId}`);
}

export async function fetchCaptureHealth(): Promise<CaptureHealthStatus> {
  return fetchJson<CaptureHealthStatus>('/api/capture/health');
}

export async function fetchExperimentalLinkedInCaptureHealth(): Promise<ExperimentalCaptureResponse> {
  return fetchJson<ExperimentalCaptureResponse>('/api/experimental-capture/linkedin/health');
}

export async function runCaptureReview(request: CaptureRunRequest): Promise<CaptureRunResult> {
  return fetchJson<CaptureRunResult>('/api/capture/run', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}

export async function exportCaptureResult(
  request: ExportCaptureResultRequest,
): Promise<ExportCaptureResultResponse> {
  return fetchJson<ExportCaptureResultResponse>('/api/export/capture-result', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}

export async function exportHistoryTracker(
  request: ExportHistoryRequest,
): Promise<ExportCaptureResultResponse> {
  return fetchJson<ExportCaptureResultResponse>('/api/export/history', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}

export async function saveCaptureResultToHistory(
  request: SaveCaptureResultHistoryRequest,
): Promise<SaveCaptureResultHistoryResponse> {
  return fetchJson<SaveCaptureResultHistoryResponse>('/api/history/save-capture-result', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}

export async function fetchHistoryJobs(): Promise<HistoryJobEntry[]> {
  return fetchJson<HistoryJobEntry[]>('/api/history/jobs');
}

export async function updateHistoryJobStatus(
  historyId: string,
  applicationStatus: ApplicationStatus,
): Promise<HistoryJobEntry> {
  return fetchJson<HistoryJobEntry>(`/api/history/jobs/${historyId}/status`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ application_status: applicationStatus }),
  });
}

export async function cleanupDemoData(): Promise<DemoCleanupResponse> {
  return fetchJson<DemoCleanupResponse>('/api/demo/cleanup', {
    method: 'POST',
  });
}

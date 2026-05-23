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
  decision: 'Apply' | 'Maybe' | 'Discard' | 'Manual Review' | 'Duplicate';
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
};

export type CaptureRunRequest = {
  profile_id: string;
  source: string;
  query?: string;
  location?: string;
  work_mode_filter?: string;
  max_results?: number;
  dry_run: boolean;
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

export async function runCaptureReview(request: CaptureRunRequest): Promise<CaptureRunResult> {
  return fetchJson<CaptureRunResult>('/api/capture/run', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}

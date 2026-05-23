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

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);

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

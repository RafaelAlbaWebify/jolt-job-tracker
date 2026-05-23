export type HealthResponse = {
  status: string;
  service: string;
  message: string;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export async function fetchBackendHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/health`);

  if (!response.ok) {
    throw new Error(`Backend health check failed with ${response.status}`);
  }

  return response.json() as Promise<HealthResponse>;
}

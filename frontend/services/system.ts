import { API_BASE_URL } from "@/lib/api";
import type {
  Evaluation,
  FeedbackResponse,
  Investigation,
  Issue,
  PolicySettings,
  PullRequest,
  Release,
  Repository,
  RepositoryHealth,
  SearchResult,
  SystemStatus,
  WeeklyBrief
} from "@/types/system";

export async function fetchSystemStatus(): Promise<SystemStatus> {
  const response = await fetch(`${API_BASE_URL}/api/system/status`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Unable to load system status");
  }
  return response.json() as Promise<SystemStatus>;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function fetchRepositories(): Promise<Repository[]> {
  return request<Repository[]>("/api/repositories");
}

export function connectRepository(repository: string): Promise<{ repository: Repository; created: boolean; status: string }> {
  return request("/api/repositories/connect", { method: "POST", body: JSON.stringify({ repository }) });
}

export function syncRepository(repositoryId: number): Promise<Record<string, number | string>> {
  return request(`/api/repositories/${repositoryId}/sync`, { method: "POST" });
}

export function fetchIssues(repositoryId: number): Promise<Issue[]> {
  return request<Issue[]>(`/api/repositories/${repositoryId}/issues`);
}

export function fetchPullRequests(repositoryId: number): Promise<PullRequest[]> {
  return request<PullRequest[]>(`/api/repositories/${repositoryId}/pull-requests`);
}

export function fetchReleases(repositoryId: number): Promise<Release[]> {
  return request<Release[]>(`/api/repositories/${repositoryId}/releases`);
}

export function searchRepository(repositoryId: number, query: string): Promise<SearchResult[]> {
  return request<SearchResult[]>(`/api/repositories/${repositoryId}/search`, { method: "POST", body: JSON.stringify({ query, top_k: 5 }) });
}

export function investigateIssue(issueId: number): Promise<Investigation> {
  return request<Investigation>(`/api/issues/${issueId}/investigate`, { method: "POST" });
}

export function fetchRepositoryHealth(repositoryId: number): Promise<RepositoryHealth> {
  return request<RepositoryHealth>(`/api/repositories/${repositoryId}/health`);
}

export function fetchWeeklyBrief(repositoryId: number): Promise<WeeklyBrief> {
  return request<WeeklyBrief>(`/api/repositories/${repositoryId}/brief/weekly`);
}

export function fetchEvaluation(repositoryId: number): Promise<Evaluation> {
  return request<Evaluation>(`/api/repositories/${repositoryId}/evaluation`);
}

export function fetchPolicySettings(): Promise<PolicySettings> {
  return request<PolicySettings>("/api/settings/policy");
}

export function submitFeedback(
  investigationId: number,
  body: { target_type: string; original_value: string; feedback_status: string; corrected_value?: string; comment?: string }
): Promise<FeedbackResponse> {
  return request<FeedbackResponse>(`/api/investigations/${investigationId}/feedback`, { method: "POST", body: JSON.stringify(body) });
}

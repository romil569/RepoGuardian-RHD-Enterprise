import { API_BASE_URL } from "@/lib/api";
import type {
  Evaluation,
  FeedbackResponse,
  Investigation,
  ActionRecommendation,
  AuditLogResponse,
  Issue,
  IssueHistory,
  PolicySettings,
  PullRequest,
  Release,
  Repository,
  RepositoryHealth,
  MLModelCard,
  ModelProviderStatus,
  RHDToolSpec,
  EnterpriseReadiness,
  RHDInitialScan,
  RHDJobStatus,
  RHDOnboardingResponse,
  RHDQueryResponse,
  RHDReview,
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

export function fetchIssueHistory(issueId: number): Promise<IssueHistory> {
  return request<IssueHistory>(`/api/issues/${issueId}/history`);
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

export function fetchReviewQueue(filter?: string): Promise<ActionRecommendation[]> {
  const query = filter ? `?filter=${encodeURIComponent(filter)}` : "";
  return request<ActionRecommendation[]>(`/api/review-queue${query}`);
}

export function fetchActionRecommendation(id: number): Promise<ActionRecommendation> {
  return request<ActionRecommendation>(`/api/action-recommendations/${id}`);
}

export function approveActionRecommendation(id: number): Promise<ActionRecommendation> {
  return request<ActionRecommendation>(`/api/action-recommendations/${id}/approve`, { method: "POST", body: JSON.stringify({ actor: "local-maintainer" }) });
}

export function rejectActionRecommendation(id: number, reason?: string): Promise<ActionRecommendation> {
  return request<ActionRecommendation>(`/api/action-recommendations/${id}/reject`, { method: "POST", body: JSON.stringify({ actor: "local-maintainer", reason }) });
}

export function executeActionRecommendation(id: number): Promise<ActionRecommendation> {
  return request<ActionRecommendation>(`/api/action-recommendations/${id}/execute`, { method: "POST", body: JSON.stringify({ actor: "local-maintainer" }) });
}

export function fetchAuditLog(params?: { repository_id?: number; issue_id?: number; event_type?: string; limit?: number }): Promise<AuditLogResponse> {
  const query = new URLSearchParams();
  if (params?.repository_id) query.set("repository_id", String(params.repository_id));
  if (params?.issue_id) query.set("issue_id", String(params.issue_id));
  if (params?.event_type) query.set("event_type", params.event_type);
  if (params?.limit) query.set("limit", String(params.limit));
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<AuditLogResponse>(`/api/audit-log${suffix}`);
}

export function onboardRepositoryWithRHD(repository: string, runSync = true): Promise<RHDOnboardingResponse> {
  return request<RHDOnboardingResponse>("/api/rhd/onboard", { method: "POST", body: JSON.stringify({ repository, run_sync: runSync }) });
}

export function fetchRHDJob(jobId: string): Promise<RHDJobStatus> {
  return request<RHDJobStatus>(`/api/jobs/${jobId}`);
}

export function advanceRHDJob(jobId: string): Promise<RHDJobStatus> {
  return request<RHDJobStatus>(`/api/jobs/${jobId}/advance`, { method: "POST" });
}

export function fetchRHDInitialScan(repositoryId: number): Promise<RHDInitialScan> {
  return request<RHDInitialScan>(`/api/rhd/repositories/${repositoryId}/initial-scan`);
}

export function fetchRHDReview(repositoryId: number): Promise<RHDReview> {
  return request<RHDReview>(`/api/rhd/repositories/${repositoryId}/review`);
}

export function askRHD(repositoryId: number, question: string, sessionContext?: Record<string, unknown>): Promise<RHDQueryResponse> {
  return request<RHDQueryResponse>("/api/rhd/query", { method: "POST", body: JSON.stringify({ repository_id: repositoryId, question, session_context: sessionContext, session_id: sessionContext?.session_id }) });
}

export function fetchModelGatewayStatus(): Promise<{ providers: ModelProviderStatus[]; priority: string[] }> {
  return request<{ providers: ModelProviderStatus[]; priority: string[] }>("/api/platform/model-gateway");
}

export function fetchMLModels(): Promise<{ models: MLModelCard[] }> {
  return request<{ models: MLModelCard[] }>("/api/platform/ml-models");
}

export function fetchRHDTools(): Promise<{ tools: RHDToolSpec[] }> {
  return request<{ tools: RHDToolSpec[] }>("/api/platform/tools");
}

export function fetchEnterpriseReadiness(): Promise<EnterpriseReadiness> {
  return request<EnterpriseReadiness>("/api/platform/enterprise-readiness");
}

export function fetchV4MissionControl(): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>("/api/v4/mission-control");
}

export function fetchV4AgentMesh(): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>("/api/v4/agent-mesh");
}

export function fetchV4RagPipeline(): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>("/api/v4/rag/pipeline");
}

export function fetchV4NeuralMap(repositoryId: number): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`/api/v4/graph/neural-map/${repositoryId}`);
}

export function fetchV4ModelLab(): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>("/api/v4/models/lab");
}

export function fetchV4Observatory(): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>("/api/v4/observatory");
}

export function fetchV5Workspace(): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>("/api/v5/workspace");
}

export function fetchV5Architecture(repositoryId: number): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`/api/v5/repositories/${repositoryId}/architecture`);
}

export function fetchV5Capabilities(): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>("/api/v5/capabilities");
}

export type SystemStatus = {
  backend: string;
  database: string;
  app_env: string;
  demo_repository?: string;
  data_backend?: string;
  vector_backend?: string;
  ai_provider?: string;
};

export type Repository = {
  id: number;
  full_name: string;
  description?: string | null;
  html_url: string;
  default_branch: string;
  language?: string | null;
  stars: number;
  last_synced_at?: string | null;
};

export type Issue = {
  id: number;
  repository_id: number;
  github_issue_number: number;
  title: string;
  state: string;
  labels: string[];
  html_url: string;
  analysis_status: string;
  classification?: string | null;
  priority?: string | null;
  escalation?: string | null;
};

export type PullRequest = {
  id: number;
  github_pr_number: number;
  title: string;
  state: string;
  html_url: string;
};

export type Release = {
  id: number;
  tag: string;
  name?: string | null;
  html_url: string;
};

export type SearchResult = {
  repository_id: number;
  source_type: string;
  source_id: number;
  github_number?: number | null;
  title: string;
  snippet: string;
  source_url?: string | null;
  relevance_score: number;
};

export type Investigation = {
  issue: { id: number; number: number; title: string; html_url: string };
  classification: { category: string; confidence: number; explanation: string };
  completeness: { score: number; available_information: string[]; missing_information: string[]; recommended_follow_up: string };
  similar_issues: SearchResult[];
  repository_context: SearchResult[];
  related_pull_requests: PullRequest[];
  recent_releases: Release[];
  priority: { level: string; confidence: number; signals: string[] };
  escalation: { decision: string; confidence: number; reason_codes: string[]; recommended_action: string };
  evidence: Array<{ source_type: string; github_number?: number | null; title: string; source_url?: string | null; retrieval_score: number; why_relevant: string }>;
  recommended_action: string;
  summary: string;
  investigation_trace: Array<{ step_number: number; tool_name: string; status: string; duration_ms: number; summary: string }>;
};

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
  investigation_id: number;
  issue: { id: number; number: number; title: string; html_url: string };
  classification: { category: string; confidence: number; explanation: string };
  completeness: { score: number; completeness_score?: number; available_information: string[]; missing_information: string[]; recommended_follow_up: string; recommended_follow_up_questions?: string[]; issue_type_specific_requirements?: string[]; confidence?: number };
  duplicate_analysis?: { duplicate_candidates: DuplicateCandidate[]; top_score: number; duplicate_state: string };
  similar_issues: DuplicateCandidate[];
  repository_context: SearchResult[];
  related_pull_requests: RelatedPullRequest[];
  recent_releases: Release[];
  security_analysis?: { security_state: string; confidence: number; signals: string[]; recommended_handling: string };
  release_regression_analysis?: { regression_state: string; confidence: number; explanation: string; matching_releases: Array<{ tag: string; title: string; url: string }> };
  priority: { level: string; priority?: string; confidence: number; priority_score?: number; signals: string[]; explanation?: string };
  priority_analysis?: { priority: string; level: string; confidence: number; priority_score: number; signals: string[]; explanation: string };
  escalation: { decision: string; confidence: number; reason_codes: string[]; recommended_action: string };
  evidence: Array<{ source_type: string; github_number?: number | null; title: string; source_url?: string | null; retrieval_score: number; why_relevant: string }>;
  recommended_action: string;
  summary: string;
  investigation_trace: Array<{ step_number: number; tool_name: string; status: string; duration_ms: number; summary: string }>;
  telemetry?: { duration_ms: number; agent_steps: number; retrieval_calls: number; github_calls: number; ai_provider_calls: number; retrieved_evidence_sources: number; error_count: number; final_status: string; token_usage?: number | null };
};

export type DuplicateCandidate = {
  candidate_issue_id: number;
  github_issue_number: number;
  title: string;
  url: string;
  semantic_similarity: number;
  keyword_overlap: number;
  category_match: boolean;
  final_duplicate_score: number;
  duplicate_state: string;
  why_similar: string;
};

export type RelatedPullRequest = {
  number: number;
  title: string;
  url: string;
  relevance_score: number;
  why_relevant: string;
};

export type RepositoryHealth = {
  overall_score: number;
  dimension_scores: Record<string, number>;
  signals: Record<string, number | null>;
  health_state: string;
  distributions: { classification: Record<string, number>; priority: Record<string, number> };
  history: { issue_creation_vs_closure: Array<{ label: string; created: number; closed: number }>; insufficient_history: boolean };
};

export type WeeklyBrief = {
  period: string;
  ai_provider: string;
  summary: string;
  statistics: Record<string, number | null>;
  high_priority_items: Array<{ issue_id: number; priority: string; escalation: string }>;
  possible_duplicates: number;
  needs_information: number;
  recent_pr_activity: number;
  release_activity: number;
  important_escalations: Array<{ issue_id: number; decision: string }>;
};

export type Evaluation = {
  status: string;
  labeled_count: number;
  metrics: Record<string, number>;
  confusion_matrix: Array<{ predicted: string; actual: string; count: number }>;
};

export type PolicySettings = {
  duplicate_possible_threshold: number;
  duplicate_very_likely_threshold: number;
  security_escalation_threshold: number;
  stale_issue_days: number;
  high_priority_score_threshold: number;
  critical_priority_score_threshold: number;
  repo_sync_interval_minutes: number;
};

export type FeedbackResponse = {
  id: number;
  repository_id: number;
  issue_id: number;
  investigation_id: number;
  target_type: string;
  original_value: string;
  feedback_status: string;
  corrected_value?: string | null;
  comment?: string | null;
  created_at: string;
};

export type SystemStatus = {
  backend: string;
  database: string;
  app_env: string;
  demo_repository?: string;
  data_backend?: string;
  vector_backend?: string;
  ai_provider?: string;
  ai_provider_mode?: string;
  live_ai_provider?: string;
  deterministic_intelligence?: string;
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
  action_recommendations?: ActionRecommendation[];
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
  allow_label_actions: boolean;
  allow_comment_actions: boolean;
  require_human_approval: boolean;
  allowed_write_repository: string;
  max_comment_length: number;
  duplicate_comment_threshold: number;
  needs_info_comment_threshold: number;
  security_actions_require_manual_review: boolean;
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

export type ActionRecommendation = {
  id: number;
  repository_id: number;
  repository?: string | null;
  issue_id: number;
  issue_number?: number | null;
  issue_title?: string | null;
  issue_url?: string | null;
  investigation_id: number;
  investigation_summary?: string | null;
  priority?: string | null;
  escalation?: string | null;
  action_type: string;
  status: string;
  recommended_payload: Record<string, unknown>;
  reason: string;
  confidence: number;
  policy_decision: string;
  created_at: string;
  updated_at: string;
  approved_by?: string | null;
  approved_at?: string | null;
  rejected_by?: string | null;
  rejected_at?: string | null;
  executed_at?: string | null;
  execution_status?: string | null;
  execution_result?: Record<string, unknown> | null;
  failure_reason?: string | null;
  security_signal?: string | null;
  duplicate_state?: string | null;
  policy_validation?: { decision: string; reason: string };
};

export type AuditLogEvent = {
  id: number;
  repository_id?: number | null;
  issue_id?: number | null;
  investigation_id?: number | null;
  action_recommendation_id?: number | null;
  actor: string;
  event_type: string;
  safe_summary: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AuditLogResponse = {
  total: number;
  limit: number;
  offset: number;
  items: AuditLogEvent[];
};

export type IssueHistory = {
  recommendations: ActionRecommendation[];
  feedback: Array<{
    id: number;
    target_type: string;
    original_value: string;
    feedback_status: string;
    corrected_value?: string | null;
    comment?: string | null;
    created_at: string;
  }>;
};

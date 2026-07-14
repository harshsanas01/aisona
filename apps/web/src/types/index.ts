export interface Citation {
  call_id: string;
  patient_id: string;
  patient_name: string;
  date: string;
  turn_start: number;
  turn_end: number;
  quote: string;
}

export interface AskFilters {
  patient_id: string | null;
  start_date: string | null;
  end_date: string | null;
}

export interface AskResponse {
  question: string;
  answer: string;
  answerable: boolean;
  confidence: string;
  citations: Citation[];
  retrieval_debug: {
    mode: string;
    candidate_count: number;
  };
  filters: AskFilters;
  request_id?: string | null;
}

export interface QuestionAuditRecord {
  request_id: string;
  created_at: string;
  question_hash: string;
  question_preview: string | null;
  filters: AskFilters;
  storage_mode: string;
  retrieval_mode: string;
  lexical_weight: number;
  semantic_weight: number;
  top_k: number;
  relevance_threshold: number;
  candidate_chunk_ids: string[];
  selected_evidence_ids: string[];
  answer_mode: string;
  provider: string;
  model_name: string | null;
  prompt_version: string;
  token_usage: Record<string, number> | null;
  latency_ms: number;
  answerable: boolean;
  confidence: string;
  final_citation_call_ids: string[];
  grounding_checks: Record<string, boolean>;
  fallback_used: boolean;
  error_category: string | null;
  feedback_summary: Record<string, unknown>;
}

export interface TranscriptTurn {
  turn_number: number;
  speaker: string;
  text: string;
}

export interface TranscriptCall {
  call_id: string;
  date: string;
  patient: {
    id: string;
    name: string;
    age: number;
  };
  duration_seconds: number;
  turns: TranscriptTurn[];
}

export interface Patient {
  id: string;
  name: string;
  age: number;
}

export interface CallSummary {
  call_id: string;
  date: string;
  patient_name: string;
}

export interface SafetyEvent {
  category: string;
  severity: string;
  call_id: string;
  turn_number: number;
  matched_text: string;
  explanation: string;
  classifier_type: string;
}

export interface PatientSummary {
  id: string;
  name: string;
  age: number;
  timeline_event_count: number;
  unreviewed_event_count: number;
  pattern_count: number;
  attention_pattern_count: number;
}

export type TimelineReviewStatus = 'unreviewed' | 'confirmed' | 'corrected' | 'dismissed';

export interface TimelineEvent {
  event_id: string;
  patient_id: string;
  event_type: string;
  title: string;
  description: string;
  observed_date: string;
  source_call_id: string;
  source_turn_start: number;
  source_turn_end: number;
  quote: string;
  confidence: string;
  extraction_method: string;
  review_status: TimelineReviewStatus;
  created_at: string;
  updated_at: string;
}

export type PatternStatus = 'active' | 'resolved' | 'uncertain';
export type PatternSeverity = 'informational' | 'attention' | 'high_attention';
export type PatternReviewStatus = 'unreviewed' | 'confirmed' | 'corrected' | 'dismissed';

export interface PatternEvidenceRef {
  timeline_event_id: string;
  call_id: string;
  turn_start: number;
  turn_end: number;
  quote: string;
}

export interface PatientPattern {
  pattern_id: string;
  patient_id: string;
  pattern_type: string;
  title: string;
  summary: string;
  status: PatternStatus;
  severity: PatternSeverity;
  first_observed_date: string;
  latest_observed_date: string;
  related_timeline_event_ids: string[];
  related_call_ids: string[];
  evidence: PatternEvidenceRef[];
  detector_version: string;
  reviewed_status: PatternReviewStatus;
  created_at: string;
  updated_at: string;
}

export type PersonMentionReviewStatus = 'unreviewed' | 'confirmed' | 'corrected' | 'dismissed';
export type PersonRelationshipType = 'participant' | 'family' | 'neighbor' | 'staff' | 'unknown';

export interface PersonMention {
  mention_id: string;
  patient_id: string;
  source_call_id: string;
  source_turn: number;
  quote: string;
  role_label: string;
  relationship_type: PersonRelationshipType;
  mentioned_name: string | null;
  confidence: string;
  extraction_method: string;
  review_status: PersonMentionReviewStatus;
  created_at: string;
  updated_at: string;
}

export type TaskPriority = 'low' | 'normal' | 'high' | 'urgent';
export type TaskStatus = 'open' | 'in_progress' | 'blocked' | 'completed' | 'dismissed';
export type TaskCategory =
  | 'nurse_follow_up' | 'transportation' | 'medication_review' | 'appointment'
  | 'meal_support' | 'home_safety' | 'general_outreach';

export interface CoordinatorTask {
  task_id: string;
  title: string;
  description: string;
  patient_id: string;
  priority: TaskPriority;
  status: TaskStatus;
  category: TaskCategory;
  is_suggested: boolean;
  created_by: string;
  source_event_id: string | null;
  source_call_id: string | null;
  source_turn_start: number | null;
  source_turn_end: number | null;
  assignee: string | null;
  due_date: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskActivityEntry {
  activity_id: string;
  task_id: string;
  action: string;
  actor: string;
  from_status: string | null;
  to_status: string | null;
  note: string | null;
  created_at: string;
}

export type BriefType = 'daily' | 'weekly';

export interface BriefEvidenceRef {
  timeline_event_id: string;
  call_id: string;
  turn_start: number;
  turn_end: number;
  quote: string;
}

export interface BriefBullet {
  bullet_id: string;
  section: string;
  patient_id: string;
  patient_name: string;
  summary: string;
  related_timeline_event_ids: string[];
  related_pattern_id: string | null;
  related_task_id: string | null;
  evidence: BriefEvidenceRef[];
}

export type FeedbackTargetType = 'answer' | 'timeline_event' | 'pattern' | 'person_mention';

export type AnswerFeedbackCategory =
  | 'correct' | 'partially_correct' | 'incorrect' | 'missing_source'
  | 'wrong_source' | 'irrelevant_answer' | 'unsupported_claim';

export type ReviewFeedbackCategory = 'confirm' | 'correct' | 'dismiss' | 'merge_duplicate';

export interface FeedbackRecord {
  feedback_id: string;
  target_type: FeedbackTargetType;
  target_id: string;
  category: string;
  actor: string;
  created_at: string;
  comment: string | null;
  corrected_value: string | null;
  prompt_version: string | null;
  retrieval_version: string | null;
  model_version: string | null;
}

export interface FeedbackSummary {
  total: number;
  by_target_type: Record<string, number>;
  by_category: Record<string, number>;
}

export interface Brief {
  brief_id: string;
  brief_type: BriefType;
  start_date: string;
  end_date: string;
  patient_id: string | null;
  include_resolved: boolean;
  model_version: string;
  prompt_version: string;
  generated_at: string;
  created_at: string;
  updated_at: string;
  bullets: BriefBullet[];
}

export type RetrievalMode = 'lexical' | 'semantic' | 'hybrid' | 'hybrid_rerank';

export interface RetrievalModeCandidate {
  chunk_id: string;
  call_id: string;
  patient_id: string;
  patient_name: string;
  date: string;
  turn_start: number;
  turn_end: number;
  quote: string;
  score: number;
}

export interface RetrievalModeResult {
  mode: RetrievalMode;
  lexical_weight: number;
  semantic_weight: number;
  reranked: boolean;
  candidates: RetrievalModeCandidate[];
}

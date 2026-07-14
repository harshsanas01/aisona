const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

export const ROLE_STORAGE_KEY = 'carecall.role';
export const ROLE_HEADER_NAME = 'X-CareCall-Role';

/**
 * Local-dev/demo identity: there is no real login flow, so the acting role
 * travels as a plain request header, read fresh from localStorage on every
 * call rather than duplicated into separate module state. A user who has
 * never picked a role sends no header at all, which the API treats as the
 * same default role every endpoint used before RBAC existed.
 */
export function roleHeaders(): Record<string, string> {
  const role = localStorage.getItem(ROLE_STORAGE_KEY);
  return role ? { [ROLE_HEADER_NAME]: role } : {};
}

export interface AskParams {
  question: string;
  patientId?: string | null;
  startDate?: string | null;
  endDate?: string | null;
}

export async function askQuestion({ question, patientId, startDate, endDate }: AskParams) {
  const response = await fetch(`${API_BASE}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question,
      patient_id: patientId || null,
      start_date: startDate || null,
      end_date: endDate || null,
    }),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || 'Failed to get an answer');
  }
  return response.json();
}

export interface StreamCallbacks {
  onRetrievalStarted?: () => void;
  onRetrievalCompleted?: (data: { candidate_count: number }) => void;
  onAnswerDelta?: (text: string) => void;
  onCitations?: (citations: unknown[]) => void;
  onCompleted?: (data: { answerable: boolean; confidence: string }) => void;
  onError?: (detail: string) => void;
}

export async function streamAskQuestion(
  { question, patientId, startDate, endDate }: AskParams,
  callbacks: StreamCallbacks,
  signal: AbortSignal,
) {
  const response = await fetch(`${API_BASE}/ask/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question,
      patient_id: patientId || null,
      start_date: startDate || null,
      end_date: endDate || null,
    }),
    signal,
  });
  if (!response.ok || !response.body) {
    const detail = await response.text().catch(() => '');
    throw new Error(detail || 'Failed to start streaming answer');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let boundary = buffer.indexOf('\n\n');
    while (boundary !== -1) {
      const rawEvent = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);

      let eventName = 'message';
      let dataLine = '{}';
      for (const line of rawEvent.split('\n')) {
        if (line.startsWith('event: ')) eventName = line.slice(7);
        else if (line.startsWith('data: ')) dataLine = line.slice(6);
      }
      const data = JSON.parse(dataLine);

      switch (eventName) {
        case 'retrieval_started': callbacks.onRetrievalStarted?.(); break;
        case 'retrieval_completed': callbacks.onRetrievalCompleted?.(data); break;
        case 'answer_delta': callbacks.onAnswerDelta?.(data.text); break;
        case 'citations': callbacks.onCitations?.(data.citations); break;
        case 'completed': callbacks.onCompleted?.(data); break;
        case 'error': callbacks.onError?.(data.detail); break;
      }

      boundary = buffer.indexOf('\n\n');
    }
  }
}

export async function getCall(callId: string) {
  const response = await fetch(`${API_BASE}/calls/${callId}`);
  if (!response.ok) {
    throw new Error('Failed to load transcript');
  }
  return response.json();
}

export async function getPatients() {
  const response = await fetch(`${API_BASE}/patients`);
  if (!response.ok) {
    throw new Error('Failed to load patients');
  }
  const body = await response.json();
  return body.patients;
}

export interface SafetyEventsParams {
  callId?: string | null;
  category?: string | null;
}

export async function getSafetyEvents(params: string | SafetyEventsParams = {}) {
  const { callId, category } = typeof params === 'string' ? { callId: params, category: null } : params;
  const query = new URLSearchParams();
  if (callId) query.set('call_id', callId);
  if (category) query.set('category', category);
  const qs = query.toString();
  const response = await fetch(`${API_BASE}/safety-events${qs ? `?${qs}` : ''}`);
  if (!response.ok) {
    throw new Error('Failed to load safety events');
  }
  const body = await response.json();
  return body.safety_events;
}

export async function getCalls() {
  const response = await fetch(`${API_BASE}/calls`);
  if (!response.ok) {
    throw new Error('Failed to load calls');
  }
  const body = await response.json();
  return body.calls;
}

export interface HealthStatus {
  status: string;
  calls_loaded: number;
  retrieval_mode: string;
  storage_mode?: string;
  answer_mode?: string;
  developer_mode?: boolean;
}

export async function getHealth(): Promise<HealthStatus> {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) {
    throw new Error('API is unavailable');
  }
  return response.json();
}

export async function getPatient(patientId: string) {
  const response = await fetch(`${API_BASE}/v1/patients/${encodeURIComponent(patientId)}`);
  if (!response.ok) {
    if (response.status === 404) return null;
    throw new Error('Failed to load patient');
  }
  return response.json();
}

export interface PatientTimelineParams {
  eventType?: string | null;
  reviewStatus?: string | null;
}

export async function getPatientTimeline(patientId: string, params: PatientTimelineParams = {}) {
  const query = new URLSearchParams();
  if (params.eventType) query.set('event_type', params.eventType);
  if (params.reviewStatus) query.set('review_status', params.reviewStatus);
  const qs = query.toString();
  const response = await fetch(
    `${API_BASE}/v1/patients/${encodeURIComponent(patientId)}/timeline${qs ? `?${qs}` : ''}`,
  );
  if (!response.ok) {
    throw new Error('Failed to load patient timeline');
  }
  const body = await response.json();
  return body.timeline_events;
}

export async function rebuildPatientTimeline(patientId: string) {
  const response = await fetch(`${API_BASE}/v1/patients/${encodeURIComponent(patientId)}/timeline/rebuild`, {
    method: 'POST',
    headers: roleHeaders(),
  });
  if (!response.ok) {
    throw new Error('Failed to rebuild patient timeline');
  }
  const body = await response.json();
  return body.timeline_events;
}

export interface UpdateTimelineEventPayload {
  review_status: string;
  title?: string;
  description?: string;
}

export async function updateTimelineEvent(eventId: string, payload: UpdateTimelineEventPayload) {
  const response = await fetch(`${API_BASE}/v1/timeline-events/${encodeURIComponent(eventId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...roleHeaders() },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new Error(formatErrorDetail(detail) || 'Failed to update timeline event');
  }
  return response.json();
}

export interface PatientPatternsParams {
  status?: string | null;
  severity?: string | null;
}

export async function getPatientPatterns(patientId: string, params: PatientPatternsParams = {}) {
  const query = new URLSearchParams();
  if (params.status) query.set('status', params.status);
  if (params.severity) query.set('severity', params.severity);
  const qs = query.toString();
  const response = await fetch(
    `${API_BASE}/v1/patients/${encodeURIComponent(patientId)}/patterns${qs ? `?${qs}` : ''}`,
  );
  if (!response.ok) {
    throw new Error('Failed to load patient patterns');
  }
  const body = await response.json();
  return body.patterns;
}

export async function rebuildPatientPatterns(patientId: string) {
  const response = await fetch(`${API_BASE}/v1/patients/${encodeURIComponent(patientId)}/patterns/rebuild`, {
    method: 'POST',
    headers: roleHeaders(),
  });
  if (!response.ok) {
    throw new Error('Failed to rebuild patient patterns');
  }
  const body = await response.json();
  return body.patterns;
}

export async function updatePatternReviewedStatus(patternId: string, reviewedStatus: string) {
  const response = await fetch(`${API_BASE}/v1/patterns/${encodeURIComponent(patternId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...roleHeaders() },
    body: JSON.stringify({ reviewed_status: reviewedStatus }),
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new Error(formatErrorDetail(detail) || 'Failed to update pattern');
  }
  return response.json();
}

export interface IngestResult {
  call_id: string;
  status: string;
  chunk_count: number;
  error: string;
}

function formatErrorDetail(raw: string): string {
  try {
    const parsed = JSON.parse(raw);
    if (typeof parsed.detail === 'string') return parsed.detail;
    if (Array.isArray(parsed.detail)) {
      return parsed.detail
        .map((item: { loc?: unknown[]; msg?: string }) => {
          const path = Array.isArray(item.loc) ? item.loc.filter((p) => p !== 'body').join(' > ') : '';
          return path ? `${path}: ${item.msg}` : item.msg;
        })
        .join('; ');
    }
  } catch {
    // Not JSON - fall through to the raw text.
  }
  return raw;
}

export async function ingestCallsBatch(calls: unknown[]): Promise<IngestResult[]> {
  const response = await fetch(`${API_BASE}/calls/batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...roleHeaders() },
    body: JSON.stringify({ calls }),
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new Error(formatErrorDetail(detail) || 'Ingestion failed');
  }
  return response.json();
}

export interface ListTasksParams {
  patientId?: string | null;
  status?: string | null;
  priority?: string | null;
  category?: string | null;
  assignee?: string | null;
}

export async function listTasks(params: ListTasksParams = {}) {
  const query = new URLSearchParams();
  if (params.patientId) query.set('patient_id', params.patientId);
  if (params.status) query.set('status', params.status);
  if (params.priority) query.set('priority', params.priority);
  if (params.category) query.set('category', params.category);
  if (params.assignee) query.set('assignee', params.assignee);
  const qs = query.toString();
  const response = await fetch(`${API_BASE}/v1/tasks${qs ? `?${qs}` : ''}`);
  if (!response.ok) {
    throw new Error('Failed to load tasks');
  }
  const body = await response.json();
  return body.tasks;
}

export interface CreateTaskPayload {
  title: string;
  description: string;
  patient_id: string;
  category: string;
  priority?: string;
  assignee?: string | null;
  due_date?: string | null;
  source_event_id?: string | null;
  source_call_id?: string | null;
  source_turn_start?: number | null;
  source_turn_end?: number | null;
  created_by?: string;
}

export async function createTask(payload: CreateTaskPayload) {
  const response = await fetch(`${API_BASE}/v1/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...roleHeaders() },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new Error(formatErrorDetail(detail) || 'Failed to create task');
  }
  return response.json();
}

export async function getTask(taskId: string) {
  const response = await fetch(`${API_BASE}/v1/tasks/${encodeURIComponent(taskId)}`);
  if (!response.ok) {
    if (response.status === 404) return null;
    throw new Error('Failed to load task');
  }
  return response.json();
}

export interface UpdateTaskPayload {
  title?: string;
  description?: string;
  priority?: string;
  category?: string;
  assignee?: string | null;
  due_date?: string | null;
  status?: string;
  note?: string;
  actor?: string;
}

export async function updateTask(taskId: string, payload: UpdateTaskPayload) {
  const response = await fetch(`${API_BASE}/v1/tasks/${encodeURIComponent(taskId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...roleHeaders() },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new Error(formatErrorDetail(detail) || 'Failed to update task');
  }
  return response.json();
}

export async function completeTask(taskId: string, actor = 'coordinator') {
  const response = await fetch(`${API_BASE}/v1/tasks/${encodeURIComponent(taskId)}/complete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...roleHeaders() },
    body: JSON.stringify({ actor }),
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new Error(formatErrorDetail(detail) || 'Failed to complete task');
  }
  return response.json();
}

export async function reopenTask(taskId: string, actor = 'coordinator') {
  const response = await fetch(`${API_BASE}/v1/tasks/${encodeURIComponent(taskId)}/reopen`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...roleHeaders() },
    body: JSON.stringify({ actor }),
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new Error(formatErrorDetail(detail) || 'Failed to reopen task');
  }
  return response.json();
}

export async function suggestTaskFromEvent(eventId: string) {
  const response = await fetch(`${API_BASE}/v1/timeline-events/${encodeURIComponent(eventId)}/suggest-task`, {
    method: 'POST',
    headers: roleHeaders(),
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new Error(formatErrorDetail(detail) || 'Failed to suggest a task');
  }
  return response.json();
}

export interface GenerateBriefPayload {
  type: string;
  start_date?: string | null;
  end_date?: string | null;
  patient_id?: string | null;
  include_resolved?: boolean;
  answer_mode?: string;
}

export async function generateBrief(payload: GenerateBriefPayload) {
  const response = await fetch(`${API_BASE}/v1/briefs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...roleHeaders() },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new Error(formatErrorDetail(detail) || 'Failed to generate brief');
  }
  return response.json();
}

export interface ListBriefsParams {
  type?: string | null;
  patientId?: string | null;
}

export async function listBriefs(params: ListBriefsParams = {}) {
  const query = new URLSearchParams();
  if (params.type) query.set('type', params.type);
  if (params.patientId) query.set('patient_id', params.patientId);
  const qs = query.toString();
  const response = await fetch(`${API_BASE}/v1/briefs${qs ? `?${qs}` : ''}`);
  if (!response.ok) {
    throw new Error('Failed to load briefs');
  }
  const body = await response.json();
  return body.briefs;
}

export async function getBrief(briefId: string) {
  const response = await fetch(`${API_BASE}/v1/briefs/${encodeURIComponent(briefId)}`);
  if (!response.ok) {
    if (response.status === 404) return null;
    throw new Error('Failed to load brief');
  }
  return response.json();
}

export async function regenerateBrief(briefId: string, answerMode = 'mock') {
  const response = await fetch(
    `${API_BASE}/v1/briefs/${encodeURIComponent(briefId)}/regenerate?answer_mode=${encodeURIComponent(answerMode)}`,
    { method: 'POST', headers: roleHeaders() },
  );
  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new Error(formatErrorDetail(detail) || 'Failed to regenerate brief');
  }
  return response.json();
}

export async function getAuditQuestion(requestId: string) {
  const response = await fetch(`${API_BASE}/v1/audit/questions/${encodeURIComponent(requestId)}`);
  if (!response.ok) {
    if (response.status === 404) return null;
    throw new Error('Failed to load audit record');
  }
  return response.json();
}

export interface SubmitFeedbackPayload {
  target_type: 'answer' | 'timeline_event' | 'pattern' | 'person_mention';
  target_id: string;
  category: string;
  actor: string;
  comment?: string | null;
  corrected_value?: string | null;
  prompt_version?: string | null;
  retrieval_version?: string | null;
  model_version?: string | null;
}

export async function submitFeedback(payload: SubmitFeedbackPayload) {
  const response = await fetch(`${API_BASE}/v1/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...roleHeaders() },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new Error(formatErrorDetail(detail) || 'Failed to submit feedback');
  }
  return response.json();
}

export interface ListFeedbackParams {
  targetType?: string | null;
  targetId?: string | null;
  category?: string | null;
  limit?: number;
}

export async function listFeedback(params: ListFeedbackParams = {}) {
  const query = new URLSearchParams();
  if (params.targetType) query.set('target_type', params.targetType);
  if (params.targetId) query.set('target_id', params.targetId);
  if (params.category) query.set('category', params.category);
  if (params.limit) query.set('limit', String(params.limit));
  const qs = query.toString();
  const response = await fetch(`${API_BASE}/v1/feedback${qs ? `?${qs}` : ''}`);
  if (!response.ok) {
    throw new Error('Failed to load feedback');
  }
  const body = await response.json();
  return body.feedback;
}

export async function getFeedbackSummary() {
  const response = await fetch(`${API_BASE}/v1/feedback/summary`);
  if (!response.ok) {
    throw new Error('Failed to load feedback summary');
  }
  return response.json();
}

export interface PersonMentionsParams {
  relationshipType?: string | null;
  reviewStatus?: string | null;
}

export async function getPatientPersonMentions(patientId: string, params: PersonMentionsParams = {}) {
  const query = new URLSearchParams();
  if (params.relationshipType) query.set('relationship_type', params.relationshipType);
  if (params.reviewStatus) query.set('review_status', params.reviewStatus);
  const qs = query.toString();
  const response = await fetch(
    `${API_BASE}/v1/patients/${encodeURIComponent(patientId)}/people${qs ? `?${qs}` : ''}`,
  );
  if (!response.ok) {
    throw new Error('Failed to load people mentioned');
  }
  const body = await response.json();
  return body.person_mentions;
}

export async function rebuildPatientPersonMentions(patientId: string) {
  const response = await fetch(`${API_BASE}/v1/patients/${encodeURIComponent(patientId)}/people/rebuild`, {
    method: 'POST',
    headers: roleHeaders(),
  });
  if (!response.ok) {
    throw new Error('Failed to rebuild people mentioned');
  }
  const body = await response.json();
  return body.person_mentions;
}

export interface UpdatePersonMentionPayload {
  review_status: string;
  corrected_relationship_type?: string;
  corrected_name?: string;
}

export async function updatePersonMention(mentionId: string, payload: UpdatePersonMentionPayload) {
  const response = await fetch(`${API_BASE}/v1/person-mentions/${encodeURIComponent(mentionId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...roleHeaders() },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new Error(formatErrorDetail(detail) || 'Failed to update person mention');
  }
  return response.json();
}

export interface CompareRetrievalPayload {
  question: string;
  patient_id?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  limit?: number;
}

export async function compareRetrievalModes(payload: CompareRetrievalPayload) {
  const response = await fetch(`${API_BASE}/v1/retrieval-lab/compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new Error(formatErrorDetail(detail) || 'Failed to compare retrieval modes');
  }
  const body = await response.json();
  return body.results;
}

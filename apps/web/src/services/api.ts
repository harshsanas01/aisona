const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

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
}

export async function getHealth(): Promise<HealthStatus> {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) {
    throw new Error('API is unavailable');
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
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ calls }),
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new Error(formatErrorDetail(detail) || 'Ingestion failed');
  }
  return response.json();
}

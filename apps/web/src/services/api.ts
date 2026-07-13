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

export async function getSafetyEvents(callId?: string) {
  const url = callId ? `${API_BASE}/safety-events?call_id=${encodeURIComponent(callId)}` : `${API_BASE}/safety-events`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error('Failed to load safety events');
  }
  const body = await response.json();
  return body.safety_events;
}

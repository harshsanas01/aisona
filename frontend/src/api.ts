const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

export async function askQuestion(question: string) {
  const response = await fetch(`${API_BASE}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
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

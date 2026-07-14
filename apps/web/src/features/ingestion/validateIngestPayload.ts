// Mirrors apps/api/src/carecall_api/routes/ingestion.py's Pydantic schema so
// obviously-invalid payloads are caught before the network round trip. The
// server remains the source of truth - this is a fast-fail UX layer only.
export const MAX_BATCH_SIZE = 20;

export interface ParsedCall {
  call_id: string;
  date: string;
  patient: { id: string; name: string; age: number };
  duration_seconds: number;
  turns: { speaker: string; text: string }[];
}

export interface ValidationResult {
  calls: ParsedCall[];
  errors: string[];
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}

function validateCall(raw: unknown, index: number, errors: string[]): void {
  const prefix = `Call ${index + 1}`;
  if (typeof raw !== 'object' || raw === null) {
    errors.push(`${prefix}: must be a JSON object`);
    return;
  }
  const call = raw as Record<string, unknown>;

  if (!isNonEmptyString(call.call_id)) errors.push(`${prefix}: "call_id" is required`);
  if (!isNonEmptyString(call.date)) errors.push(`${prefix}: "date" is required (e.g. 2026-06-01)`);
  if (typeof call.duration_seconds !== 'number' || call.duration_seconds < 0) {
    errors.push(`${prefix}: "duration_seconds" must be a non-negative number`);
  }

  const patient = call.patient as Record<string, unknown> | undefined;
  if (typeof patient !== 'object' || patient === null) {
    errors.push(`${prefix}: "patient" object is required`);
  } else {
    if (!isNonEmptyString(patient.id)) errors.push(`${prefix}: "patient.id" is required`);
    if (!isNonEmptyString(patient.name)) errors.push(`${prefix}: "patient.name" is required`);
    if (typeof patient.age !== 'number' || patient.age < 0 || patient.age > 130) {
      errors.push(`${prefix}: "patient.age" must be a number between 0 and 130`);
    }
  }

  if (!Array.isArray(call.turns) || call.turns.length === 0) {
    errors.push(`${prefix}: "turns" must be a non-empty array`);
  } else {
    call.turns.forEach((turn, turnIndex) => {
      const t = turn as Record<string, unknown>;
      if (typeof t !== 'object' || t === null || !isNonEmptyString(t.speaker) || !isNonEmptyString(t.text)) {
        errors.push(`${prefix}, turn ${turnIndex + 1}: needs non-empty "speaker" and "text"`);
      }
    });
  }
}

export function validateIngestPayload(rawText: string): ValidationResult {
  const errors: string[] = [];
  let parsed: unknown;

  try {
    parsed = JSON.parse(rawText);
  } catch (err) {
    return { calls: [], errors: [`Invalid JSON: ${err instanceof Error ? err.message : 'could not parse'}`] };
  }

  const list = Array.isArray(parsed)
    ? parsed
    : parsed && typeof parsed === 'object' && Array.isArray((parsed as { calls?: unknown }).calls)
      ? (parsed as { calls: unknown[] }).calls
      : null;

  if (list === null) {
    return { calls: [], errors: ['Payload must be a JSON array of calls, or an object like {"calls": [...]}'] };
  }
  if (list.length === 0) {
    return { calls: [], errors: ['Provide at least one call'] };
  }
  if (list.length > MAX_BATCH_SIZE) {
    errors.push(`Batch has ${list.length} calls; the API accepts at most ${MAX_BATCH_SIZE} per request. Split into smaller batches.`);
  }

  list.forEach((call, index) => validateCall(call, index, errors));

  return { calls: errors.length === 0 ? (list as ParsedCall[]) : [], errors };
}

export const SAMPLE_PAYLOAD = `[
  {
    "call_id": "call_101",
    "date": "2026-07-01",
    "patient": { "id": "p_010", "name": "Alex Rivera", "age": 78 },
    "duration_seconds": 420,
    "turns": [
      { "speaker": "assistant", "text": "Good morning! How are you feeling today?" },
      { "speaker": "participant", "text": "A little tired, but otherwise okay." }
    ]
  }
]`;

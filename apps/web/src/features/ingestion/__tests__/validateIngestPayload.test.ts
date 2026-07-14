import { describe, expect, it } from 'vitest';
import { MAX_BATCH_SIZE, SAMPLE_PAYLOAD, validateIngestPayload } from '../validateIngestPayload';

describe('validateIngestPayload', () => {
  it('accepts the documented sample payload with no errors', () => {
    const { calls, errors } = validateIngestPayload(SAMPLE_PAYLOAD);
    expect(errors).toEqual([]);
    expect(calls).toHaveLength(1);
    expect(calls[0].call_id).toBe('call_101');
  });

  it('rejects invalid JSON with a readable message', () => {
    const { calls, errors } = validateIngestPayload('{ not valid json');
    expect(calls).toEqual([]);
    expect(errors[0]).toMatch(/Invalid JSON/);
  });

  it('accepts the {"calls": [...]} wrapper form', () => {
    const { errors } = validateIngestPayload(JSON.stringify({ calls: JSON.parse(SAMPLE_PAYLOAD) }));
    expect(errors).toEqual([]);
  });

  it('rejects a payload that is neither an array nor a {calls: []} object', () => {
    const { errors } = validateIngestPayload(JSON.stringify({ foo: 'bar' }));
    expect(errors[0]).toMatch(/must be a JSON array/);
  });

  it('flags a batch larger than MAX_BATCH_SIZE', () => {
    const calls = Array.from({ length: MAX_BATCH_SIZE + 1 }, (_, i) => ({
      call_id: `call_${i}`,
      date: '2026-01-01',
      patient: { id: 'p1', name: 'Test Patient', age: 70 },
      duration_seconds: 60,
      turns: [{ speaker: 'assistant', text: 'Hi' }],
    }));
    const { errors } = validateIngestPayload(JSON.stringify(calls));
    expect(errors.some((e) => e.includes(`at most ${MAX_BATCH_SIZE}`))).toBe(true);
  });

  it('reports per-field, per-call errors for missing required fields', () => {
    const { calls, errors } = validateIngestPayload(JSON.stringify([{ call_id: '' }]));
    expect(calls).toEqual([]);
    expect(errors.some((e) => e.includes('Call 1') && e.includes('call_id'))).toBe(true);
    expect(errors.some((e) => e.includes('patient'))).toBe(true);
    expect(errors.some((e) => e.includes('turns'))).toBe(true);
  });

  it('rejects a turn missing speaker or text', () => {
    const payload = [{
      call_id: 'call_1',
      date: '2026-01-01',
      patient: { id: 'p1', name: 'Test Patient', age: 70 },
      duration_seconds: 60,
      turns: [{ speaker: '', text: 'hello' }],
    }];
    const { errors } = validateIngestPayload(JSON.stringify(payload));
    expect(errors.some((e) => e.includes('turn 1'))).toBe(true);
  });
});

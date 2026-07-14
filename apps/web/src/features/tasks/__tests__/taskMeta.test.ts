import { describe, expect, it } from 'vitest';
import { isTaskOverdue } from '../taskMeta';

describe('isTaskOverdue', () => {
  it('returns false when there is no due date', () => {
    expect(isTaskOverdue({ due_date: null, status: 'open' })).toBe(false);
  });

  it('returns true for a past due date on an open task', () => {
    expect(isTaskOverdue({ due_date: '2000-01-01', status: 'open' })).toBe(true);
  });

  it('returns false for a past due date once the task is completed', () => {
    expect(isTaskOverdue({ due_date: '2000-01-01', status: 'completed' })).toBe(false);
  });

  it('returns false for a past due date once the task is dismissed', () => {
    expect(isTaskOverdue({ due_date: '2000-01-01', status: 'dismissed' })).toBe(false);
  });

  it('returns false for a future due date', () => {
    expect(isTaskOverdue({ due_date: '2999-01-01', status: 'open' })).toBe(false);
  });
});

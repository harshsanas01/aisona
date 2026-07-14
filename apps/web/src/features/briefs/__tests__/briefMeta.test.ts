import { describe, expect, it } from 'vitest';
import { briefSectionLabel, briefToMarkdown } from '../briefMeta';

describe('briefSectionLabel', () => {
  it('returns a human label for known sections', () => {
    expect(briefSectionLabel('high_attention')).toBe('High attention');
    expect(briefSectionLabel('transportation_appointment_issues')).toBe('Transportation & appointments');
  });

  it('falls back to a readable label for unknown sections', () => {
    expect(briefSectionLabel('some_new_section')).toBe('some new section');
  });
});

describe('briefToMarkdown', () => {
  const brief = {
    brief_type: 'weekly',
    start_date: '2026-06-01',
    end_date: '2026-06-07',
    patient_id: null,
    generated_at: '2026-06-08T00:00:00+00:00',
    model_version: 'deterministic',
    prompt_version: 'v1',
    bullets: [
      {
        section: 'high_attention',
        patient_name: 'Margaret Chen',
        summary: 'Observed pattern: something notable.',
        evidence: [{ call_id: 'call_009', turn_start: 2 }],
      },
    ],
  };

  it('includes the period, scope, and model/prompt version', () => {
    const markdown = briefToMarkdown(brief);
    expect(markdown).toContain('2026-06-01 to 2026-06-07');
    expect(markdown).toContain('Center-wide');
    expect(markdown).toContain('deterministic');
    expect(markdown).toContain('v1');
  });

  it('renders each bullet with its patient name and evidence citation', () => {
    const markdown = briefToMarkdown(brief);
    expect(markdown).toContain('**Margaret Chen**');
    expect(markdown).toContain('call_009 (turn 2)');
  });
});

export const BRIEF_SECTION_ORDER = [
  'high_attention',
  'follow_up_needed',
  'new_medication_changes',
  'recurring_concerns',
  'transportation_appointment_issues',
  'resolved_items',
  'task_status_summary',
] as const;

const SECTION_LABEL: Record<string, string> = {
  high_attention: 'High attention',
  follow_up_needed: 'Follow-up needed',
  new_medication_changes: 'New medication changes',
  recurring_concerns: 'Recurring concerns',
  transportation_appointment_issues: 'Transportation & appointments',
  resolved_items: 'Resolved items',
  task_status_summary: 'Task status summary',
};

export function briefSectionLabel(section: string): string {
  return SECTION_LABEL[section] ?? section.replace(/_/g, ' ');
}

export function briefToMarkdown(brief: {
  brief_type: string; start_date: string; end_date: string; patient_id: string | null;
  generated_at: string; model_version: string; prompt_version: string;
  bullets: Array<{ section: string; patient_name: string; summary: string; evidence: Array<{ call_id: string; turn_start: number }> }>;
}): string {
  const lines: string[] = [];
  lines.push(`# ${brief.brief_type === 'weekly' ? 'Weekly' : 'Daily'} Care Brief`);
  lines.push('');
  lines.push(`**Period:** ${brief.start_date} to ${brief.end_date}`);
  lines.push(`**Scope:** ${brief.patient_id ?? 'Center-wide'}`);
  lines.push(`**Generated:** ${brief.generated_at} (model: ${brief.model_version}, prompt: ${brief.prompt_version})`);
  lines.push('');

  const bySection = new Map<string, typeof brief.bullets>();
  for (const bullet of brief.bullets) {
    const list = bySection.get(bullet.section) ?? [];
    list.push(bullet);
    bySection.set(bullet.section, list);
  }

  for (const section of BRIEF_SECTION_ORDER) {
    const bullets = bySection.get(section);
    if (!bullets || bullets.length === 0) continue;
    lines.push(`## ${briefSectionLabel(section)}`);
    for (const bullet of bullets) {
      const evidence = bullet.evidence.map((e) => `${e.call_id} (turn ${e.turn_start})`).join(', ');
      lines.push(`- **${bullet.patient_name}**: ${bullet.summary}${evidence ? ` _(${evidence})_` : ''}`);
    }
    lines.push('');
  }

  return lines.join('\n');
}

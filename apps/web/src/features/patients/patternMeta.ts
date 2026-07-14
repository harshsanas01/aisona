const PATTERN_TYPE_LABEL: Record<string, string> = {
  first_occurrence: 'First occurrence',
  repeated_occurrence: 'Repeated occurrence',
  increasing_frequency: 'Increasing frequency',
  worsening_wording: 'Possible worsening',
  issue_resolved: 'Issue resolved',
  recurrence_after_resolution: 'Recurrence after resolution',
  medication_started_before_symptom: 'Medication started before symptom',
  repeated_transportation_issue: 'Repeated transportation issue',
  repeated_missed_medication: 'Repeated missed medication',
  repeated_sleep_issue: 'Repeated sleep issue',
  repeated_meal_concern: 'Repeated meal concern',
};

export function patternTypeLabel(patternType: string): string {
  return PATTERN_TYPE_LABEL[patternType] ?? patternType.replace(/_/g, ' ');
}

const SEVERITY_LABEL: Record<string, string> = {
  informational: 'Informational',
  attention: 'Attention',
  high_attention: 'High attention',
};

export function patternSeverityLabel(severity: string): string {
  return SEVERITY_LABEL[severity] ?? severity;
}

export function patternSeverityBadgeTone(severity: string): 'neutral' | 'warning' | 'danger' {
  if (severity === 'high_attention') return 'danger';
  if (severity === 'attention') return 'warning';
  return 'neutral';
}

const STATUS_LABEL: Record<string, string> = {
  active: 'Active',
  resolved: 'Resolved',
  uncertain: 'Uncertain',
};

export function patternStatusLabel(status: string): string {
  return STATUS_LABEL[status] ?? status;
}

const REVIEWED_STATUS_LABEL: Record<string, string> = {
  unreviewed: 'Unreviewed',
  confirmed: 'Confirmed',
  corrected: 'Corrected',
  dismissed: 'Dismissed',
};

export function patternReviewedStatusLabel(status: string): string {
  return REVIEWED_STATUS_LABEL[status] ?? status;
}

export interface SafetyCategoryMeta {
  label: string;
  color: string;
}

// Deliberately calm, operational labels - this is triage support for care
// coordinators, not a clinical or diagnostic classification.
export const SAFETY_CATEGORY_META: Record<string, SafetyCategoryMeta> = {
  dizziness: { label: 'Dizziness', color: '#f59e0b' },
  fall_or_near_fall: { label: 'Fall / near-fall', color: '#dc2626' },
  missed_medication: { label: 'Missed medication', color: '#7c3aed' },
  medication_change: { label: 'Medication change', color: '#2563eb' },
  sleep_problem: { label: 'Sleep concern', color: '#0891b2' },
  food_or_meal_concern: { label: 'Meal concern', color: '#65a30d' },
  glucose_concern: { label: 'Glucose concern', color: '#db2777' },
  respiratory_symptom: { label: 'Respiratory symptom', color: '#ea580c' },
  transportation_issue: { label: 'Transportation issue', color: '#4b5563' },
  home_safety_concern: { label: 'Home safety concern', color: '#b45309' },
};

export function safetyCategoryMeta(category: string): SafetyCategoryMeta {
  return SAFETY_CATEGORY_META[category] ?? { label: category, color: '#6b7280' };
}

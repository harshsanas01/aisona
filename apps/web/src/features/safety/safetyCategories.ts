import {
  AlertTriangle, Waves, Pill, RefreshCw, Moon, Utensils, Droplet, Wind, Car, Home, type LucideIcon,
} from 'lucide-react';

export interface SafetyCategoryMeta {
  label: string;
  dot: string;
  bg: string;
  fg: string;
  icon: LucideIcon;
}

// Deliberately calm, operational labels - this is triage support for care
// coordinators, not a clinical or diagnostic classification. Colors are
// hand-picked (not derived) so every category stays legible at small sizes.
export const SAFETY_CATEGORY_META: Record<string, SafetyCategoryMeta> = {
  dizziness: {
    label: 'Dizziness', icon: Waves,
    dot: 'var(--color-amber-500)', bg: 'var(--color-amber-100)', fg: 'var(--color-amber-700)',
  },
  fall_or_near_fall: {
    label: 'Fall / near-fall', icon: AlertTriangle,
    dot: 'var(--color-coral-500)', bg: 'var(--color-coral-100)', fg: 'var(--color-coral-700)',
  },
  missed_medication: {
    label: 'Missed medication', icon: Pill,
    dot: 'var(--color-violet-500)', bg: 'var(--color-violet-100)', fg: 'var(--color-violet-700)',
  },
  medication_change: {
    label: 'Medication change', icon: RefreshCw,
    dot: 'var(--color-blue-500)', bg: 'var(--color-blue-100)', fg: 'var(--color-blue-700)',
  },
  sleep_problem: {
    label: 'Sleep concern', icon: Moon,
    dot: 'var(--color-cyan-500)', bg: 'var(--color-cyan-100)', fg: 'var(--color-cyan-700)',
  },
  food_or_meal_concern: {
    label: 'Meal concern', icon: Utensils,
    dot: 'var(--color-green-500)', bg: 'var(--color-green-100)', fg: 'var(--color-green-700)',
  },
  glucose_concern: {
    label: 'Glucose concern', icon: Droplet,
    dot: 'var(--color-rose-500)', bg: 'var(--color-rose-100)', fg: 'var(--color-rose-700)',
  },
  respiratory_symptom: {
    label: 'Respiratory symptom', icon: Wind,
    dot: 'var(--color-orange-500)', bg: 'var(--color-orange-100)', fg: 'var(--color-orange-700)',
  },
  transportation_issue: {
    label: 'Transportation issue', icon: Car,
    dot: 'var(--color-slate-500)', bg: 'var(--color-slate-100)', fg: 'var(--color-slate-700)',
  },
  home_safety_concern: {
    label: 'Home safety concern', icon: Home,
    dot: 'var(--color-navy-600)', bg: 'var(--color-slate-100)', fg: 'var(--color-navy-800)',
  },
};

const FALLBACK_META: SafetyCategoryMeta = {
  label: 'Other', icon: AlertTriangle,
  dot: 'var(--color-slate-500)', bg: 'var(--color-slate-100)', fg: 'var(--color-slate-700)',
};

export function safetyCategoryMeta(category: string): SafetyCategoryMeta {
  return SAFETY_CATEGORY_META[category] ?? { ...FALLBACK_META, label: category };
}

export const SEVERITY_LABEL: Record<string, string> = {
  low: 'Low severity',
  medium: 'Medium severity',
  high: 'High severity',
};

export function severityLabel(severity: string): string {
  return SEVERITY_LABEL[severity] ?? severity;
}

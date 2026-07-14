import {
  AlarmClock, Accessibility, Activity, AlertTriangle, Calendar, Car, CheckCircle2,
  Home, Moon, PhoneCall, Pill, RefreshCw, Utensils, type LucideIcon,
} from 'lucide-react';

export interface TimelineEventTypeMeta {
  label: string;
  bg: string;
  fg: string;
  icon: LucideIcon;
}

// Same principle as safety category metadata: calm, operational labels -
// these describe observed transcript events, never a diagnosis.
export const TIMELINE_EVENT_TYPE_META: Record<string, TimelineEventTypeMeta> = {
  medication_started: {
    label: 'Medication started', icon: Pill,
    bg: 'var(--color-blue-100)', fg: 'var(--color-blue-700)',
  },
  medication_adherence_concern: {
    label: 'Medication adherence concern', icon: AlarmClock,
    bg: 'var(--color-violet-100)', fg: 'var(--color-violet-700)',
  },
  symptom_reported: {
    label: 'Symptom reported', icon: Activity,
    bg: 'var(--color-amber-100)', fg: 'var(--color-amber-700)',
  },
  symptom_recurrence: {
    label: 'Symptom recurrence', icon: RefreshCw,
    bg: 'var(--color-coral-100)', fg: 'var(--color-coral-700)',
  },
  sleep_issue: {
    label: 'Sleep issue', icon: Moon,
    bg: 'var(--color-cyan-100)', fg: 'var(--color-cyan-700)',
  },
  meal_concern: {
    label: 'Meal concern', icon: Utensils,
    bg: 'var(--color-green-100)', fg: 'var(--color-green-700)',
  },
  transportation_issue: {
    label: 'Transportation issue', icon: Car,
    bg: 'var(--color-slate-100)', fg: 'var(--color-slate-700)',
  },
  appointment_request: {
    label: 'Appointment request', icon: Calendar,
    bg: 'var(--color-blue-100)', fg: 'var(--color-blue-700)',
  },
  home_safety_concern: {
    label: 'Home safety concern', icon: Home,
    bg: 'var(--color-slate-100)', fg: 'var(--color-navy-800)',
  },
  assistive_device_update: {
    label: 'Assistive device update', icon: Accessibility,
    bg: 'var(--color-cyan-100)', fg: 'var(--color-cyan-700)',
  },
  issue_resolved: {
    label: 'Issue resolved', icon: CheckCircle2,
    bg: 'var(--color-success-bg)', fg: 'var(--color-green-700)',
  },
  follow_up_promised: {
    label: 'Follow-up promised', icon: PhoneCall,
    bg: 'var(--color-orange-100)', fg: 'var(--color-orange-700)',
  },
  other_safety_event: {
    label: 'Other safety event', icon: AlertTriangle,
    bg: 'var(--color-slate-100)', fg: 'var(--color-slate-700)',
  },
};

const FALLBACK_META: TimelineEventTypeMeta = {
  label: 'Other', icon: AlertTriangle,
  bg: 'var(--color-slate-100)', fg: 'var(--color-slate-700)',
};

export function timelineEventTypeMeta(eventType: string): TimelineEventTypeMeta {
  return TIMELINE_EVENT_TYPE_META[eventType] ?? { ...FALLBACK_META, label: eventType };
}

export const REVIEW_STATUS_LABEL: Record<string, string> = {
  unreviewed: 'Unreviewed',
  confirmed: 'Confirmed',
  corrected: 'Corrected',
  dismissed: 'Dismissed',
};

export function reviewStatusLabel(status: string): string {
  return REVIEW_STATUS_LABEL[status] ?? status;
}

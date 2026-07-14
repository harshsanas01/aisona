import type { BadgeTone } from '../../components/ui/Badge';

export const TASK_STATUSES = ['open', 'in_progress', 'blocked', 'completed', 'dismissed'] as const;
export const TASK_PRIORITIES = ['low', 'normal', 'high', 'urgent'] as const;
export const TASK_CATEGORIES = [
  'nurse_follow_up', 'transportation', 'medication_review', 'appointment',
  'meal_support', 'home_safety', 'general_outreach',
] as const;

// Local-development fixtures only - there is no real identity system yet
// (see docs/security/roles-and-privacy.md). Assignee is always a free-text
// field; these are just convenient suggestions, never enforced accounts.
export const LOCAL_ASSIGNEE_SUGGESTIONS = [
  'Nurse Amy', 'Coordinator Jordan', 'Coordinator Priya', 'Care Team',
];

const STATUS_LABEL: Record<string, string> = {
  open: 'Open',
  in_progress: 'In progress',
  blocked: 'Blocked',
  completed: 'Completed',
  dismissed: 'Dismissed',
};

export function taskStatusLabel(status: string): string {
  return STATUS_LABEL[status] ?? status;
}

export function taskStatusBadgeTone(status: string): BadgeTone {
  switch (status) {
    case 'open': return 'info';
    case 'in_progress': return 'brand';
    case 'blocked': return 'warning';
    case 'completed': return 'success';
    case 'dismissed': return 'neutral';
    default: return 'neutral';
  }
}

const PRIORITY_LABEL: Record<string, string> = {
  low: 'Low', normal: 'Normal', high: 'High', urgent: 'Urgent',
};

export function taskPriorityLabel(priority: string): string {
  return PRIORITY_LABEL[priority] ?? priority;
}

export function taskPriorityBadgeTone(priority: string): BadgeTone {
  switch (priority) {
    case 'urgent': return 'danger';
    case 'high': return 'warning';
    case 'normal': return 'outline';
    case 'low': return 'neutral';
    default: return 'neutral';
  }
}

const CATEGORY_LABEL: Record<string, string> = {
  nurse_follow_up: 'Nurse follow-up',
  transportation: 'Transportation',
  medication_review: 'Medication review',
  appointment: 'Appointment',
  meal_support: 'Meal support',
  home_safety: 'Home safety',
  general_outreach: 'General outreach',
};

export function taskCategoryLabel(category: string): string {
  return CATEGORY_LABEL[category] ?? category.replace(/_/g, ' ');
}

export function isTaskOverdue(task: { due_date: string | null; status: string }): boolean {
  if (!task.due_date) return false;
  if (task.status === 'completed' || task.status === 'dismissed') return false;
  const today = new Date().toISOString().slice(0, 10);
  return task.due_date < today;
}

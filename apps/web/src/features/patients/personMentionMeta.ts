import type { BadgeTone } from '../../components/ui/Badge';

const RELATIONSHIP_TYPE_LABEL: Record<string, string> = {
  participant: 'CareCall participant',
  family: 'Family',
  neighbor: 'Neighbor',
  staff: 'Staff',
  unknown: 'Unclear - needs review',
};

export function relationshipTypeLabel(relationshipType: string): string {
  return RELATIONSHIP_TYPE_LABEL[relationshipType] ?? relationshipType;
}

export function relationshipTypeBadgeTone(relationshipType: string): BadgeTone {
  if (relationshipType === 'unknown') return 'warning';
  if (relationshipType === 'participant') return 'brand';
  return 'outline';
}

const REVIEW_STATUS_LABEL: Record<string, string> = {
  unreviewed: 'Unreviewed',
  confirmed: 'Confirmed',
  corrected: 'Corrected',
  dismissed: 'Dismissed',
};

export function personMentionReviewStatusLabel(status: string): string {
  return REVIEW_STATUS_LABEL[status] ?? status;
}

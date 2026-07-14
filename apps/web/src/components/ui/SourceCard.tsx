import { ArrowUpRight } from 'lucide-react';
import type { Citation } from '../../types';
import { Badge } from './Badge';

interface SourceCardProps {
  citation: Citation;
  order: number;
  onOpen: (citation: Citation) => void;
}

const AVATAR_COLORS = [
  'var(--color-brand-500)', 'var(--color-blue-500)', 'var(--color-violet-500)',
  'var(--color-orange-500)', 'var(--color-cyan-500)', 'var(--color-rose-500)',
];

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function avatarColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = (hash * 31 + name.charCodeAt(i)) >>> 0;
  return AVATAR_COLORS[hash % AVATAR_COLORS.length];
}

export function SourceCard({ citation, order, onOpen }: SourceCardProps) {
  const turnLabel = citation.turn_start === citation.turn_end
    ? `turn ${citation.turn_start}`
    : `turns ${citation.turn_start}-${citation.turn_end}`;

  return (
    <button
      type="button"
      className="source-card"
      onClick={() => onOpen(citation)}
      aria-label={`Open transcript for ${citation.patient_name}, ${citation.date}, ${turnLabel}`}
    >
      <div className="source-card-top">
        <span className="source-avatar" style={{ background: avatarColor(citation.patient_name) }} aria-hidden="true">
          {initials(citation.patient_name)}
        </span>
        <div className="source-identity">
          <span className="source-name">{citation.patient_name}</span>
          <span className="source-meta">{citation.call_id} · {citation.date} · {turnLabel}</span>
        </div>
        <span className="source-order"><Badge tone="brand">#{order}</Badge></span>
      </div>
      <p className="source-quote">&ldquo;{citation.quote}&rdquo;</p>
      <span className="source-action">
        Open transcript <ArrowUpRight size={13} aria-hidden="true" />
      </span>
    </button>
  );
}

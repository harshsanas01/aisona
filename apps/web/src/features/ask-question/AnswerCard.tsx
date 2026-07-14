import { CheckCircle2, HelpCircle, Layers, Radar } from 'lucide-react';
import type { AskResponse } from '../../types';
import { Badge, type BadgeTone } from '../../components/ui/Badge';

interface AnswerCardProps {
  answer: AskResponse;
}

const CONFIDENCE_TONE: Record<string, BadgeTone> = { high: 'success', medium: 'brand', low: 'neutral' };

export function AnswerCard({ answer }: AnswerCardProps) {
  const hasActiveFilters = Boolean(
    answer.filters?.patient_id || answer.filters?.start_date || answer.filters?.end_date,
  );
  const isFilteredEmpty = !answer.answerable && answer.retrieval_debug.candidate_count === 0 && hasActiveFilters;

  const label = answer.answerable
    ? 'Answerable'
    : isFilteredEmpty
      ? 'No calls match the selected filters'
      : 'Not enough evidence';

  const message = isFilteredEmpty
    ? 'Try widening the date range or clearing the patient filter.'
    : answer.answer;

  return (
    <div className={`answer-result-card ${answer.answerable ? 'is-answerable' : 'is-unanswerable'}`}>
      <div className="answer-result-header">
        <span className="answer-result-status">
          {answer.answerable ? <CheckCircle2 size={16} aria-hidden="true" /> : <HelpCircle size={16} aria-hidden="true" />}
          {label}
        </span>
        <Badge tone={CONFIDENCE_TONE[answer.confidence] ?? 'neutral'}>{answer.confidence} confidence</Badge>
      </div>
      <p className="answer-result-text">{message}</p>
      <div className="answer-result-meta">
        <span><Radar size={12} aria-hidden="true" /> {answer.retrieval_debug.mode}</span>
        <span><Layers size={12} aria-hidden="true" /> {answer.retrieval_debug.candidate_count} candidates</span>
      </div>
    </div>
  );
}

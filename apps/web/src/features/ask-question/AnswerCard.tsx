import type { AskResponse } from '../../types';

interface AnswerCardProps {
  answer: AskResponse;
}

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
    <div className="answer-card">
      <div className="answer-header">
        <strong>{label}</strong>
        <span className="pill">{answer.confidence}</span>
      </div>
      <p>{message}</p>
      <div className="debug-row">
        <span>{answer.retrieval_debug.mode}</span>
        <span>{answer.retrieval_debug.candidate_count} candidates</span>
      </div>
    </div>
  );
}

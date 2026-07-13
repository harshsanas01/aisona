import type { AskResponse } from '../../types';

interface AnswerCardProps {
  answer: AskResponse;
}

export function AnswerCard({ answer }: AnswerCardProps) {
  const label = answer.answerable ? 'Answerable' : 'Not enough evidence';
  return (
    <div className="answer-card">
      <div className="answer-header">
        <strong>{label}</strong>
        <span className="pill">{answer.confidence}</span>
      </div>
      <p>{answer.answer}</p>
      <div className="debug-row">
        <span>{answer.retrieval_debug.mode}</span>
        <span>{answer.retrieval_debug.candidate_count} candidates</span>
      </div>
    </div>
  );
}

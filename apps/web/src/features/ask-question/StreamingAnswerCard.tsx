import type { Citation } from '../../types';
import type { StreamPhase } from './useStreamingAnswer';

interface StreamingAnswerCardProps {
  phase: StreamPhase;
  candidateCount: number;
  answerText: string;
  citations: Citation[];
  answerable: boolean | null;
  error: string;
  onCancel: () => void;
  onOpenCitation: (citation: Citation) => void;
}

const PHASE_LABEL: Record<StreamPhase, string> = {
  idle: '',
  retrieving: 'Retrieving evidence…',
  generating: 'Generating answer…',
  done: 'Done',
  error: 'Error',
  cancelled: 'Cancelled',
};

export function StreamingAnswerCard({
  phase,
  candidateCount,
  answerText,
  citations,
  answerable,
  error,
  onCancel,
  onOpenCitation,
}: StreamingAnswerCardProps) {
  if (phase === 'idle') return null;
  const isActive = phase === 'retrieving' || phase === 'generating';

  return (
    <div className="answer-card streaming-card">
      <div className="answer-header">
        <strong>{PHASE_LABEL[phase]}</strong>
        {isActive ? (
          <button type="button" className="secondary" onClick={onCancel}>Cancel</button>
        ) : null}
      </div>

      {error ? <div className="error">{error}</div> : null}

      <p>
        {answerText}
        {phase === 'generating' ? <span className="stream-cursor">▍</span> : null}
      </p>

      <div className="debug-row">
        <span>{candidateCount} candidates</span>
      </div>

      {phase === 'done' && answerable && citations.length ? (
        <div className="sources">
          <h3>Sources</h3>
          {citations.map((citation, index) => (
            <button
              key={`${citation.call_id}-${index}`}
              className="source-card"
              onClick={() => onOpenCitation(citation)}
            >
              <div className="source-topline">
                <strong>{citation.patient_name}</strong>
                <span>{citation.date}</span>
              </div>
              <div className="source-meta">{citation.call_id} · turns {citation.turn_start}-{citation.turn_end}</div>
              <p>{citation.quote}</p>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

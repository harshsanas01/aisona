import { Loader2, Radar, X } from 'lucide-react';
import type { Citation } from '../../types';
import type { StreamPhase } from './useStreamingAnswer';
import { Button } from '../../components/ui/Button';
import { SourceCard } from '../../components/ui/SourceCard';

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
    <div className={`answer-result-card ${answerable === false ? 'is-unanswerable' : 'is-answerable'}`}>
      <div className="answer-result-header">
        <span className="answer-result-status">
          {isActive ? <Loader2 size={16} className="spin-icon" aria-hidden="true" /> : null}
          {PHASE_LABEL[phase]}
        </span>
        {isActive ? (
          <Button variant="ghost" size="sm" leftIcon={<X size={13} />} onClick={onCancel}>Cancel</Button>
        ) : null}
      </div>

      {error ? <div className="error" role="alert">{error}</div> : null}

      <p className="answer-result-text">
        {answerText}
        {phase === 'generating' ? <span className="stream-cursor">▍</span> : null}
      </p>

      <div className="answer-result-meta">
        <span><Radar size={12} aria-hidden="true" /> {candidateCount} candidates</span>
      </div>

      {phase === 'done' && answerable && citations.length ? (
        <div className="sources">
          <h3>Sources</h3>
          <div className="source-list">
            {citations.map((citation, index) => (
              <SourceCard key={`${citation.call_id}-${index}`} citation={citation} order={index + 1} onOpen={onOpenCitation} />
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

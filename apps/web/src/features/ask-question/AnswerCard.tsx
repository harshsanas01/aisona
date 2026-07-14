import { useEffect, useState } from 'react';
import { CheckCircle2, HelpCircle, Layers, Radar, Sparkles, ThumbsDown, ThumbsUp } from 'lucide-react';
import type { AskResponse } from '../../types';
import { Badge, type BadgeTone } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { IconButton } from '../../components/ui/IconButton';
import { submitFeedback } from '../../services/api';
import { useRole } from '../../app/RoleContext';
import { AnswerFeedbackModal } from './AnswerFeedbackModal';

interface AnswerCardProps {
  answer: AskResponse;
  onOpenWhyThisAnswer?: () => void;
}

const CONFIDENCE_TONE: Record<string, BadgeTone> = { high: 'success', medium: 'brand', low: 'neutral' };

export function AnswerCard({ answer, onOpenWhyThisAnswer }: AnswerCardProps) {
  const [feedbackGiven, setFeedbackGiven] = useState<'up' | 'down' | null>(null);
  const [submittingUp, setSubmittingUp] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const { hasPermission } = useRole();
  const canGiveFeedback = hasPermission('review');

  useEffect(() => {
    setFeedbackGiven(null);
    setModalOpen(false);
  }, [answer.request_id]);

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

  const handleThumbsUp = async () => {
    if (!answer.request_id || submittingUp) return;
    setSubmittingUp(true);
    try {
      await submitFeedback({
        target_type: 'answer',
        target_id: answer.request_id,
        category: 'correct',
        actor: 'coordinator',
      });
      setFeedbackGiven('up');
    } catch {
      // Non-critical - the coordinator can simply try again.
    } finally {
      setSubmittingUp(false);
    }
  };

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
        {onOpenWhyThisAnswer ? (
          <Button variant="ghost" size="sm" leftIcon={<Sparkles size={12} />} onClick={onOpenWhyThisAnswer}>
            Why this answer?
          </Button>
        ) : null}
        {answer.request_id ? (
          feedbackGiven ? (
            <span className="answer-feedback-thanks">Thanks for the feedback</span>
          ) : (
            <span className="answer-feedback-controls">
              <IconButton
                icon={<ThumbsUp size={14} />}
                label="This answer was correct"
                onClick={handleThumbsUp}
                disabled={submittingUp || !canGiveFeedback}
              />
              <IconButton
                icon={<ThumbsDown size={14} />}
                label="This answer had a problem"
                onClick={() => setModalOpen(true)}
                disabled={!canGiveFeedback}
              />
            </span>
          )
        ) : null}
      </div>
      {answer.request_id ? (
        <AnswerFeedbackModal
          open={modalOpen}
          onClose={() => setModalOpen(false)}
          requestId={answer.request_id}
          onSubmitted={() => setFeedbackGiven('down')}
        />
      ) : null}
    </div>
  );
}

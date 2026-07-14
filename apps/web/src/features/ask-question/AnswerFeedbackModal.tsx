import { useEffect, useState } from 'react';
import { Modal } from '../../components/ui/Modal';
import { Select } from '../../components/ui/Select';
import { Textarea } from '../../components/ui/Textarea';
import { Button } from '../../components/ui/Button';
import { submitFeedback } from '../../services/api';

const NEGATIVE_FEEDBACK_CATEGORIES = [
  { value: 'partially_correct', label: 'Partially correct' },
  { value: 'incorrect', label: 'Incorrect' },
  { value: 'missing_source', label: 'Missing a source it should have cited' },
  { value: 'wrong_source', label: 'Cited the wrong source' },
  { value: 'irrelevant_answer', label: "Didn't answer the question" },
  { value: 'unsupported_claim', label: 'Made a claim the evidence does not support' },
];

interface AnswerFeedbackModalProps {
  open: boolean;
  onClose: () => void;
  requestId: string;
  onSubmitted: () => void;
}

export function AnswerFeedbackModal({ open, onClose, requestId, onSubmitted }: AnswerFeedbackModalProps) {
  const [category, setCategory] = useState(NEGATIVE_FEEDBACK_CATEGORIES[0].value);
  const [comment, setComment] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!open) return;
    setCategory(NEGATIVE_FEEDBACK_CATEGORIES[0].value);
    setComment('');
    setError('');
  }, [open]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      await submitFeedback({
        target_type: 'answer',
        target_id: requestId,
        category,
        actor: 'coordinator',
        comment: comment.trim() || null,
      });
      onSubmitted();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit feedback');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="What was wrong with this answer?">
      <form onSubmit={handleSubmit} className="answer-feedback-form">
        <Select
          label="What was the issue?"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          options={NEGATIVE_FEEDBACK_CATEGORIES}
        />
        <Textarea
          label="Additional details (optional)"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          hint="Helps whoever reviews this later understand what went wrong."
        />
        {error ? <p className="field-error">{error}</p> : null}
        <div className="answer-feedback-actions">
          <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
          <Button type="submit" loading={submitting}>Submit feedback</Button>
        </div>
      </form>
    </Modal>
  );
}

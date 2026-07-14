import { useRef, useState } from 'react';
import { streamAskQuestion } from '../../services/api';
import type { Citation } from '../../types';
import type { Filters } from '../../hooks/useAskQuestion';

export type StreamPhase = 'idle' | 'retrieving' | 'generating' | 'done' | 'error' | 'cancelled';

export function useStreamingAnswer() {
  const [phase, setPhase] = useState<StreamPhase>('idle');
  const [candidateCount, setCandidateCount] = useState(0);
  const [answerText, setAnswerText] = useState('');
  const [citations, setCitations] = useState<Citation[]>([]);
  const [answerable, setAnswerable] = useState<boolean | null>(null);
  const [error, setError] = useState('');
  const abortRef = useRef<AbortController | null>(null);

  const start = async (question: string, filters: Filters) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setPhase('retrieving');
    setCandidateCount(0);
    setAnswerText('');
    setCitations([]);
    setAnswerable(null);
    setError('');

    try {
      await streamAskQuestion(
        { question, patientId: filters.patientId, startDate: filters.startDate, endDate: filters.endDate },
        {
          onRetrievalCompleted: (data) => {
            setCandidateCount(data.candidate_count);
            setPhase('generating');
          },
          onAnswerDelta: (text) => setAnswerText((prev) => prev + text),
          // Citations only ever arrive after generation completes and has
          // been validated server-side - never rendered before this event.
          onCitations: (cites) => setCitations(cites as Citation[]),
          onCompleted: (data) => {
            setAnswerable(data.answerable);
            setPhase('done');
          },
          onError: (detail) => {
            setError(detail);
            setPhase('error');
          },
        },
        controller.signal,
      );
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        setPhase('cancelled');
      } else {
        setError(err instanceof Error ? err.message : 'Streaming failed');
        setPhase('error');
      }
    }
  };

  const cancel = () => {
    abortRef.current?.abort();
  };

  return { phase, candidateCount, answerText, citations, answerable, error, start, cancel };
}

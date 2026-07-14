import { useState } from 'react';
import { askQuestion } from '../services/api';
import type { AskResponse } from '../types';

export interface Filters {
  patientId: string | null;
  startDate: string | null;
  endDate: string | null;
}

export function useAskQuestion(initialQuestion: string) {
  const [question, setQuestion] = useState(initialQuestion);
  const [answer, setAnswer] = useState<AskResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const ask = async (value = question, filters: Filters = { patientId: null, startDate: null, endDate: null }) => {
    setLoading(true);
    setError('');
    setAnswer(null);
    try {
      const response = await askQuestion({
        question: value,
        patientId: filters.patientId,
        startDate: filters.startDate,
        endDate: filters.endDate,
      });
      setAnswer(response);
      return response;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error');
      return null;
    } finally {
      setLoading(false);
    }
  };

  return { question, setQuestion, answer, loading, error, ask };
}

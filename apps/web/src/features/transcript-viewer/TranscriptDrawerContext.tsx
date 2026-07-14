import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import { getCall, getSafetyEvents } from '../../services/api';
import type { SafetyEvent, TranscriptCall } from '../../types';

export interface TranscriptTarget {
  callId: string;
  /** Inclusive turn range to highlight, e.g. a citation's evidence span. */
  turnStart?: number;
  turnEnd?: number;
  /** Single turn to scroll to first (e.g. a safety event's turn). Defaults to turnStart. */
  focusTurn?: number;
  /** Restrict the safety legend to one category when opened from Safety Events. */
  category?: string | null;
}

interface TranscriptDrawerValue {
  target: TranscriptTarget | null;
  transcript: TranscriptCall | null;
  safetyEvents: SafetyEvent[];
  loading: boolean;
  error: string;
  open: (target: TranscriptTarget) => void;
  close: () => void;
}

const TranscriptDrawerContext = createContext<TranscriptDrawerValue | null>(null);

export function TranscriptDrawerProvider({ children }: { children: ReactNode }) {
  const [target, setTarget] = useState<TranscriptTarget | null>(null);
  const [transcript, setTranscript] = useState<TranscriptCall | null>(null);
  const [safetyEvents, setSafetyEvents] = useState<SafetyEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const open = useCallback((next: TranscriptTarget) => {
    setTarget(next);
    setTranscript(null);
    setSafetyEvents([]);
    setError('');
    setLoading(true);

    Promise.all([getCall(next.callId), getSafetyEvents({ callId: next.callId })])
      .then(([call, events]) => {
        setTranscript(call as TranscriptCall);
        setSafetyEvents(events as SafetyEvent[]);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to open transcript');
      })
      .finally(() => setLoading(false));
  }, []);

  const close = useCallback(() => {
    setTarget(null);
    setTranscript(null);
    setSafetyEvents([]);
    setError('');
  }, []);

  const value = useMemo(
    () => ({ target, transcript, safetyEvents, loading, error, open, close }),
    [target, transcript, safetyEvents, loading, error, open, close],
  );

  return <TranscriptDrawerContext.Provider value={value}>{children}</TranscriptDrawerContext.Provider>;
}

export function useTranscriptDrawer() {
  const ctx = useContext(TranscriptDrawerContext);
  if (!ctx) throw new Error('useTranscriptDrawer must be used within a TranscriptDrawerProvider');
  return ctx;
}

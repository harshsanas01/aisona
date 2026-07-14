import { useEffect, useState } from 'react';
import { getCalls, getSafetyEvents } from '../../services/api';
import type { CallSummary, SafetyEvent } from '../../types';

interface CallsState {
  calls: CallSummary[];
  safetyCountByCall: Map<string, number>;
  loading: boolean;
  error: string;
}

export function useCalls(): CallsState {
  const [calls, setCalls] = useState<CallSummary[]>([]);
  const [safetyCountByCall, setSafetyCountByCall] = useState<Map<string, number>>(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');

    Promise.all([getCalls(), getSafetyEvents()])
      .then(([callList, events]) => {
        if (cancelled) return;
        const counts = new Map<string, number>();
        for (const event of events as SafetyEvent[]) {
          counts.set(event.call_id, (counts.get(event.call_id) ?? 0) + 1);
        }
        setCalls(callList as CallSummary[]);
        setSafetyCountByCall(counts);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load calls');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, []);

  return { calls, safetyCountByCall, loading, error };
}

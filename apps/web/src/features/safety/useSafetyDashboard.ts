import { useEffect, useState } from 'react';
import { getCalls, getSafetyEvents } from '../../services/api';
import type { CallSummary, SafetyEvent } from '../../types';

interface SafetyDashboardState {
  events: SafetyEvent[];
  callsById: Map<string, CallSummary>;
  loading: boolean;
  error: string;
}

export function useSafetyDashboard(): SafetyDashboardState {
  const [events, setEvents] = useState<SafetyEvent[]>([]);
  const [callsById, setCallsById] = useState<Map<string, CallSummary>>(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');

    Promise.all([getSafetyEvents(), getCalls()])
      .then(([eventList, callList]) => {
        if (cancelled) return;
        setEvents(eventList as SafetyEvent[]);
        setCallsById(new Map((callList as CallSummary[]).map((call) => [call.call_id, call])));
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load safety events');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, []);

  return { events, callsById, loading, error };
}

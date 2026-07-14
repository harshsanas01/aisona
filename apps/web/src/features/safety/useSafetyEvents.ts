import { useEffect, useState } from 'react';
import { getSafetyEvents } from '../../services/api';
import type { SafetyEvent } from '../../types';

export function useSafetyEvents(callId: string | null) {
  const [events, setEvents] = useState<SafetyEvent[]>([]);

  useEffect(() => {
    if (!callId) {
      setEvents([]);
      return;
    }
    let cancelled = false;
    getSafetyEvents(callId)
      .then((result) => { if (!cancelled) setEvents(result); })
      .catch(() => { if (!cancelled) setEvents([]); });
    return () => { cancelled = true; };
  }, [callId]);

  return events;
}

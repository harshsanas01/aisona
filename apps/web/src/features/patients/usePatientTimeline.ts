import { useCallback, useEffect, useState } from 'react';
import {
  getPatient,
  getPatientTimeline,
  rebuildPatientTimeline,
  updateTimelineEvent,
  type UpdateTimelineEventPayload,
} from '../../services/api';
import type { PatientSummary, TimelineEvent } from '../../types';

interface PatientTimelineState {
  patient: PatientSummary | null;
  events: TimelineEvent[];
  loading: boolean;
  rebuilding: boolean;
  error: string;
  notFound: boolean;
  refresh: () => void;
  rebuild: () => Promise<void>;
  updateEvent: (eventId: string, payload: UpdateTimelineEventPayload) => Promise<void>;
}

export function usePatientTimeline(patientId: string): PatientTimelineState {
  const [patient, setPatient] = useState<PatientSummary | null>(null);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [rebuilding, setRebuilding] = useState(false);
  const [error, setError] = useState('');
  const [notFound, setNotFound] = useState(false);
  const [version, setVersion] = useState(0);

  const refresh = useCallback(() => setVersion((v) => v + 1), []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    setNotFound(false);

    Promise.all([getPatient(patientId), getPatientTimeline(patientId)])
      .then(([patientResult, eventList]) => {
        if (cancelled) return;
        if (patientResult === null) {
          setNotFound(true);
          return;
        }
        setPatient(patientResult as PatientSummary);
        setEvents(eventList as TimelineEvent[]);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load patient timeline');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [patientId, version]);

  const rebuild = useCallback(async () => {
    setRebuilding(true);
    setError('');
    try {
      const rebuilt = await rebuildPatientTimeline(patientId);
      setEvents(rebuilt as TimelineEvent[]);
      const patientResult = await getPatient(patientId);
      if (patientResult) setPatient(patientResult as PatientSummary);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rebuild patient timeline');
    } finally {
      setRebuilding(false);
    }
  }, [patientId]);

  const updateEvent = useCallback(async (eventId: string, payload: UpdateTimelineEventPayload) => {
    const updated = await updateTimelineEvent(eventId, payload);
    setEvents((current) => current.map((event) => (event.event_id === eventId ? updated : event)));
  }, []);

  return { patient, events, loading, rebuilding, error, notFound, refresh, rebuild, updateEvent };
}

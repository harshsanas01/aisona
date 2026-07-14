import { useEffect, useState } from 'react';
import { getPatient, getPatients } from '../../services/api';
import type { PatientSummary } from '../../types';

interface PatientsSummaryState {
  patients: PatientSummary[];
  loading: boolean;
  error: string;
}

export function usePatientsWithTimelineSummary(): PatientsSummaryState {
  const [patients, setPatients] = useState<PatientSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');

    getPatients()
      .then(async (basePatients: Array<{ id: string; name: string; age: number }>) => {
        const summaries = await Promise.all(basePatients.map((p) => getPatient(p.id)));
        if (cancelled) return;
        setPatients(summaries.filter(Boolean) as PatientSummary[]);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load patients');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, []);

  return { patients, loading, error };
}

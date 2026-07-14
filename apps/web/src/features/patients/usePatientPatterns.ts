import { useCallback, useEffect, useState } from 'react';
import { getPatientPatterns, rebuildPatientPatterns, updatePatternReviewedStatus } from '../../services/api';
import type { PatientPattern } from '../../types';

interface PatientPatternsState {
  patterns: PatientPattern[];
  loading: boolean;
  rebuilding: boolean;
  error: string;
  rebuild: () => Promise<void>;
  updateReviewedStatus: (patternId: string, reviewedStatus: string) => Promise<void>;
}

export function usePatientPatterns(patientId: string): PatientPatternsState {
  const [patterns, setPatterns] = useState<PatientPattern[]>([]);
  const [loading, setLoading] = useState(true);
  const [rebuilding, setRebuilding] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');

    getPatientPatterns(patientId)
      .then((result: PatientPattern[]) => { if (!cancelled) setPatterns(result); })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load patterns');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [patientId]);

  const rebuild = useCallback(async () => {
    setRebuilding(true);
    setError('');
    try {
      const rebuilt = await rebuildPatientPatterns(patientId);
      setPatterns(rebuilt);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rebuild patterns');
    } finally {
      setRebuilding(false);
    }
  }, [patientId]);

  const updateReviewedStatus = useCallback(async (patternId: string, reviewedStatus: string) => {
    const updated = await updatePatternReviewedStatus(patternId, reviewedStatus);
    setPatterns((current) => current.map((p) => (p.pattern_id === patternId ? updated : p)));
  }, []);

  return { patterns, loading, rebuilding, error, rebuild, updateReviewedStatus };
}

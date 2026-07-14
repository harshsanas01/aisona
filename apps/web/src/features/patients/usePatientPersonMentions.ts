import { useCallback, useEffect, useState } from 'react';
import { getPatientPersonMentions, rebuildPatientPersonMentions, updatePersonMention } from '../../services/api';
import type { PersonMention } from '../../types';

interface PatientPersonMentionsState {
  mentions: PersonMention[];
  loading: boolean;
  rebuilding: boolean;
  error: string;
  rebuild: () => Promise<void>;
  updateReviewStatus: (
    mentionId: string, reviewStatus: string, corrections?: { relationshipType?: string; name?: string },
  ) => Promise<void>;
}

export function usePatientPersonMentions(patientId: string): PatientPersonMentionsState {
  const [mentions, setMentions] = useState<PersonMention[]>([]);
  const [loading, setLoading] = useState(true);
  const [rebuilding, setRebuilding] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');

    getPatientPersonMentions(patientId)
      .then((result: PersonMention[]) => { if (!cancelled) setMentions(result); })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load people mentioned');
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
      const rebuilt = await rebuildPatientPersonMentions(patientId);
      setMentions(rebuilt);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rebuild people mentioned');
    } finally {
      setRebuilding(false);
    }
  }, [patientId]);

  const updateReviewStatus = useCallback(async (
    mentionId: string, reviewStatus: string, corrections?: { relationshipType?: string; name?: string },
  ) => {
    const updated = await updatePersonMention(mentionId, {
      review_status: reviewStatus,
      corrected_relationship_type: corrections?.relationshipType,
      corrected_name: corrections?.name,
    });
    setMentions((current) => current.map((m) => (m.mention_id === mentionId ? updated : m)));
  }, []);

  return { mentions, loading, rebuilding, error, rebuild, updateReviewStatus };
}

import { useCallback, useState } from 'react';
import { generateBrief, getBrief, regenerateBrief, type GenerateBriefPayload } from '../../services/api';
import type { Brief } from '../../types';

export function useBriefGeneration() {
  const [brief, setBrief] = useState<Brief | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const generate = useCallback(async (payload: GenerateBriefPayload) => {
    setLoading(true);
    setError('');
    try {
      const result = await generateBrief(payload);
      setBrief(result);
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate brief');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const regenerate = useCallback(async (briefId: string, answerMode = 'mock') => {
    setLoading(true);
    setError('');
    try {
      const result = await regenerateBrief(briefId, answerMode);
      setBrief(result);
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to regenerate brief');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const load = useCallback(async (briefId: string) => {
    setLoading(true);
    setError('');
    try {
      const result = await getBrief(briefId);
      setBrief(result);
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load brief');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return { brief, loading, error, generate, regenerate, load };
}

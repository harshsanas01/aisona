import { useCallback, useEffect, useState } from 'react';
import { listTasks, type ListTasksParams } from '../../services/api';
import type { CoordinatorTask } from '../../types';

interface TasksState {
  tasks: CoordinatorTask[];
  loading: boolean;
  error: string;
  refresh: () => void;
}

export function useTasks(params: ListTasksParams = {}): TasksState {
  const [tasks, setTasks] = useState<CoordinatorTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [version, setVersion] = useState(0);

  const refresh = useCallback(() => setVersion((v) => v + 1), []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');

    listTasks(params)
      .then((result: CoordinatorTask[]) => { if (!cancelled) setTasks(result); })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load tasks');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [version, params.patientId, params.status, params.priority, params.category, params.assignee]);

  return { tasks, loading, error, refresh };
}

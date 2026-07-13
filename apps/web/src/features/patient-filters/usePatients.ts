import { useEffect, useState } from 'react';
import { getPatients } from '../../services/api';
import type { Patient } from '../../types';

export function usePatients() {
  const [patients, setPatients] = useState<Patient[]>([]);

  useEffect(() => {
    let cancelled = false;
    getPatients()
      .then((result) => { if (!cancelled) setPatients(result); })
      .catch(() => { if (!cancelled) setPatients([]); });
    return () => { cancelled = true; };
  }, []);

  return patients;
}

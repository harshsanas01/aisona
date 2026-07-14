import { useEffect, useState } from 'react';
import { getHealth, type HealthStatus } from '../services/api';

const POLL_INTERVAL_MS = 30_000;

export function useHealth() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [online, setOnline] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const poll = () => {
      getHealth()
        .then((result) => {
          if (cancelled) return;
          setHealth(result);
          setOnline(true);
        })
        .catch(() => {
          if (cancelled) return;
          setOnline(false);
        });
    };

    poll();
    const interval = window.setInterval(poll, POLL_INTERVAL_MS);
    return () => { cancelled = true; window.clearInterval(interval); };
  }, []);

  return { health, online };
}

import { AlertTriangle } from 'lucide-react';
import { Button } from './Button';

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ title = 'Something went wrong', message, onRetry }: ErrorStateProps) {
  return (
    <div className="state-block is-error" role="alert">
      <div className="state-icon" aria-hidden="true"><AlertTriangle size={22} /></div>
      <p className="state-title">{title}</p>
      <p className="state-desc">{message}</p>
      {onRetry ? <Button variant="secondary" size="sm" onClick={onRetry}>Try again</Button> : null}
    </div>
  );
}

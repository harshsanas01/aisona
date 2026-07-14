import type { ReactNode } from 'react';

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="state-block" role="status">
      {icon ? <div className="state-icon" aria-hidden="true">{icon}</div> : null}
      <p className="state-title">{title}</p>
      {description ? <p className="state-desc">{description}</p> : null}
      {action}
    </div>
  );
}

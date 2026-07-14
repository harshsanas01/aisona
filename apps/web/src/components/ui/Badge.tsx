import type { ReactNode } from 'react';

export type BadgeTone =
  | 'neutral' | 'brand' | 'success' | 'warning' | 'danger' | 'info'
  | 'violet' | 'cyan' | 'orange' | 'rose' | 'outline';

interface BadgeProps {
  tone?: BadgeTone;
  dot?: boolean;
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function Badge({ tone = 'neutral', dot = false, icon, children, className = '' }: BadgeProps) {
  return (
    <span className={`badge badge-${tone} ${className}`.trim()}>
      {dot ? <span className="badge-dot" aria-hidden="true" /> : icon}
      {children}
    </span>
  );
}

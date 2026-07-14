import type { ReactNode } from 'react';
import { useId } from 'react';

interface TooltipProps {
  label: string;
  children: ReactNode;
}

export function Tooltip({ label, children }: TooltipProps) {
  const id = useId();
  return (
    <span className="tooltip-wrap">
      {children}
      <span role="tooltip" id={id} className="tooltip-bubble">{label}</span>
    </span>
  );
}

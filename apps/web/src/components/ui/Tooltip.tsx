import type { ReactNode } from 'react';
import { useId } from 'react';

interface TooltipProps {
  label: string;
  children: ReactNode;
  placement?: 'top' | 'bottom';
}

export function Tooltip({ label, children, placement = 'top' }: TooltipProps) {
  const id = useId();
  return (
    <span className="tooltip-wrap">
      {children}
      <span role="tooltip" id={id} className={`tooltip-bubble tooltip-${placement}`}>{label}</span>
    </span>
  );
}

import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { Tooltip } from './Tooltip';

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon: ReactNode;
  label: string;
  active?: boolean;
  size?: 'sm' | 'md';
  showTooltip?: boolean;
}

export function IconButton({
  icon,
  label,
  active = false,
  size = 'md',
  showTooltip = true,
  className = '',
  ...rest
}: IconButtonProps) {
  const classes = ['icon-btn', size === 'sm' ? 'icon-btn-sm' : '', active ? 'active' : '', className]
    .filter(Boolean)
    .join(' ');

  const button = (
    <button type="button" className={classes} aria-label={label} aria-pressed={active} {...rest}>
      {icon}
    </button>
  );

  if (!showTooltip) return button;
  return <Tooltip label={label}>{button}</Tooltip>;
}

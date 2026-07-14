import type { ReactNode } from 'react';
import { X } from 'lucide-react';

interface FilterChipProps {
  active?: boolean;
  icon?: ReactNode;
  onClick?: () => void;
  onRemove?: () => void;
  children: ReactNode;
}

export function FilterChip({ active = false, icon, onClick, onRemove, children }: FilterChipProps) {
  return (
    <span
      className={`filter-chip ${active ? 'active' : ''}`}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick}
      onKeyDown={onClick ? (event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onClick(); } } : undefined}
    >
      {icon}
      {children}
      {onRemove ? (
        <button
          type="button"
          className="filter-chip-remove"
          aria-label="Remove filter"
          onClick={(event) => { event.stopPropagation(); onRemove(); }}
        >
          <X size={12} />
        </button>
      ) : null}
    </span>
  );
}

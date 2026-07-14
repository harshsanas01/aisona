import type { ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { useDismissable } from './useDismissable';

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  labelledBy: string;
  children: ReactNode;
}

/** Right-side drawer on desktop; CSS collapses it to a full-screen sheet on mobile (see ui.css). */
export function Drawer({ open, onClose, labelledBy, children }: DrawerProps) {
  const panelRef = useDismissable(open, onClose);
  if (!open) return null;

  return createPortal(
    <>
      <div className="overlay" onClick={onClose} />
      <div
        ref={panelRef}
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby={labelledBy}
        tabIndex={-1}
      >
        {children}
      </div>
    </>,
    document.body,
  );
}

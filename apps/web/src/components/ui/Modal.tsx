import type { ReactNode } from 'react';
import { X } from 'lucide-react';
import { createPortal } from 'react-dom';
import { useDismissable } from './useDismissable';
import { IconButton } from './IconButton';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}

export function Modal({ open, onClose, title, children }: ModalProps) {
  const panelRef = useDismissable(open, onClose);
  if (!open) return null;

  return createPortal(
    <>
      <div className="overlay" onClick={onClose} />
      <div
        ref={panelRef}
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        tabIndex={-1}
      >
        <div className="modal-header">
          <h2 id="modal-title" className="modal-title">{title}</h2>
          <IconButton icon={<X size={16} />} label="Close dialog" onClick={onClose} showTooltip={false} />
        </div>
        {children}
      </div>
    </>,
    document.body,
  );
}

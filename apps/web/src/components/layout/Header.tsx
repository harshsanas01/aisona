import { useLocation } from 'react-router-dom';
import { useState } from 'react';
import { AlertCircle, CheckCircle2, Keyboard, Menu } from 'lucide-react';
import { NAV_ITEMS } from './navItems';
import { Badge } from '../ui/Badge';
import { IconButton } from '../ui/IconButton';
import { Modal } from '../ui/Modal';
import { Select } from '../ui/Select';
import { useHealth } from '../../hooks/useHealth';
import { ROLES, roleLabel, useRole, type Role } from '../../app/RoleContext';

const SHORTCUTS: Array<[string, string]> = [
  ['Ctrl/Cmd + Enter', 'Ask the current question'],
  ['Esc', 'Close the transcript drawer or a dialog'],
  ['Tab / Shift+Tab', 'Move focus within a dialog or drawer'],
];

interface HeaderProps {
  onOpenMobileNav: () => void;
}

export function Header({ onOpenMobileNav }: HeaderProps) {
  const location = useLocation();
  const { health, online } = useHealth();
  const { role, setRole } = useRole();
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const active = NAV_ITEMS.find((item) => location.pathname.startsWith(item.path)) ?? NAV_ITEMS[0];

  return (
    <header className="app-header">
      <div className="app-header-left">
        <IconButton
          icon={<Menu size={18} />}
          label="Open navigation"
          className="header-menu-btn"
          onClick={onOpenMobileNav}
          showTooltip={false}
        />
        <div>
          <h1>{active.title}</h1>
          <p className="app-header-subtitle">{active.subtitle}</p>
        </div>
      </div>

      <div className="app-header-right">
        <Select
          aria-label="Acting role"
          className="header-role-select"
          value={role}
          onChange={(e) => setRole(e.target.value as Role)}
          options={ROLES.map((r) => ({ value: r, label: roleLabel(r) }))}
        />
        {health?.storage_mode ? <Badge tone="outline">Storage: {health.storage_mode}</Badge> : null}
        {health?.answer_mode ? <Badge tone="outline">Answers: {health.answer_mode}</Badge> : null}
        <Badge tone={online ? 'success' : 'danger'} icon={online ? <CheckCircle2 size={12} /> : <AlertCircle size={12} />}>
          {online ? 'API healthy' : 'API unreachable'}
        </Badge>
        <IconButton
          icon={<Keyboard size={16} />}
          label="Keyboard shortcuts"
          tooltipPlacement="bottom"
          onClick={() => setShortcutsOpen(true)}
        />
      </div>

      <Modal open={shortcutsOpen} onClose={() => setShortcutsOpen(false)} title="Keyboard shortcuts">
        <dl className="shortcuts-list">
          {SHORTCUTS.map(([keys, description]) => (
            <div key={keys} className="shortcuts-row">
              <dt><kbd>{keys}</kbd></dt>
              <dd>{description}</dd>
            </div>
          ))}
        </dl>
      </Modal>
    </header>
  );
}

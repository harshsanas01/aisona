import { NavLink } from 'react-router-dom';
import { ChevronsLeft, ChevronsRight, HeartPulse, Wifi, WifiOff, X } from 'lucide-react';
import { NAV_ITEMS } from './navItems';
import { useHealth } from '../../hooks/useHealth';
import { IconButton } from '../ui/IconButton';
import { useDismissable } from '../ui/useDismissable';

interface SidebarProps {
  collapsed: boolean;
  onToggleCollapsed: () => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
}

export function Sidebar({ collapsed, onToggleCollapsed, mobileOpen, onCloseMobile }: SidebarProps) {
  const { health, online } = useHealth();
  // Escape-to-close and a focus trap only take effect while the mobile
  // off-canvas nav is open; on desktop this is inert.
  const navRef = useDismissable(mobileOpen, onCloseMobile);

  return (
    <>
      {mobileOpen ? <div className="sidebar-scrim" onClick={onCloseMobile} /> : null}
      <nav
        ref={navRef}
        className={`app-sidebar ${collapsed ? 'is-collapsed' : ''} ${mobileOpen ? 'is-mobile-open' : ''}`}
        aria-label="Primary"
      >
        <div className="sidebar-top">
          <div className="sidebar-brand">
            <span className="sidebar-logo" aria-hidden="true"><HeartPulse size={18} /></span>
            {!collapsed ? (
              <span className="sidebar-wordmark">
                <strong>CareCall</strong>
                <span>Insight</span>
              </span>
            ) : null}
          </div>
          <IconButton
            icon={<X size={16} />}
            label="Close navigation"
            className="sidebar-close-mobile"
            onClick={onCloseMobile}
            showTooltip={false}
          />
        </div>

        <ul className="sidebar-nav">
          {NAV_ITEMS.filter((item) => !item.devOnly || health?.developer_mode).map((item) => {
            const Icon = item.icon;
            return (
              <li key={item.path}>
                <NavLink
                  to={item.path}
                  className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}
                  onClick={onCloseMobile}
                >
                  <Icon size={18} aria-hidden="true" />
                  {!collapsed ? <span>{item.label}</span> : null}
                </NavLink>
              </li>
            );
          })}
        </ul>

        <div className="sidebar-bottom">
          <button type="button" className="sidebar-collapse-toggle" onClick={onToggleCollapsed} aria-pressed={collapsed}>
            {collapsed ? <ChevronsRight size={16} /> : <ChevronsLeft size={16} />}
            {!collapsed ? <span>Collapse</span> : null}
          </button>
          <div className={`sidebar-status ${online ? 'is-online' : 'is-offline'}`}>
            {online ? <Wifi size={14} aria-hidden="true" /> : <WifiOff size={14} aria-hidden="true" />}
            {!collapsed ? (
              <span>
                {online ? 'API online' : 'API unreachable'}
                {online && health ? ` · ${health.calls_loaded} calls` : ''}
              </span>
            ) : null}
          </div>
        </div>
      </nav>
    </>
  );
}

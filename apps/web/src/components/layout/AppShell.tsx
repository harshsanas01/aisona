import { useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { TranscriptDrawer } from '../../features/transcript-viewer/TranscriptDrawer';
import './layout.css';

const COLLAPSE_KEY = 'carecall.sidebar.collapsed';

export function AppShell() {
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(COLLAPSE_KEY) === 'true');
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    localStorage.setItem(COLLAPSE_KEY, String(collapsed));
  }, [collapsed]);

  return (
    <div className="app-shell-root">
      <Sidebar
        collapsed={collapsed}
        onToggleCollapsed={() => setCollapsed((prev) => !prev)}
        mobileOpen={mobileNavOpen}
        onCloseMobile={() => setMobileNavOpen(false)}
      />
      <div className="app-shell-main">
        <Header onOpenMobileNav={() => setMobileNavOpen(true)} />
        <main className="app-shell-content" id="main-content">
          <Outlet />
        </main>
      </div>
      <TranscriptDrawer />
    </div>
  );
}

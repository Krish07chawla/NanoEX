import { useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { Footer } from './Disclaimer';
import { useStreams } from '../../hooks/useStreams';
import { useAccountStore } from '../../store/accountStore';

export function AppLayout() {
  const [menuOpen, setMenuOpen] = useState(false);
  useStreams();
  useEffect(() => {
    useAccountStore
      .getState()
      .loadWallet()
      .catch(() => undefined);
  }, []);

  return (
    <div className="flex min-h-screen bg-ink-950 text-fg">
      <Sidebar open={menuOpen} onNavigate={() => setMenuOpen(false)} />
      {menuOpen && (
        <div className="fixed inset-0 z-30 bg-black/50 lg:hidden" onClick={() => setMenuOpen(false)} />
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onMenu={() => setMenuOpen(true)} />
        <main className="flex-1 p-4 md:p-6">
          <Outlet />
        </main>
        <Footer />
      </div>
    </div>
  );
}

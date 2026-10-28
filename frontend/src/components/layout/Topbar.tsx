import { useNavigate } from 'react-router-dom';
import { PaperBadge } from './Disclaimer';
import { useAuthStore } from '../../store/authStore';
import { useAccountStore } from '../../store/accountStore';
import { useMarketStore } from '../../store/marketStore';
import { post } from '../../services/api';
import { formatINR } from '../../utils/format';

export function Topbar({ onMenu }: { onMenu: () => void }) {
  const user = useAuthStore((s) => s.user);
  const clear = useAuthStore((s) => s.clear);
  const wallet = useAccountStore((s) => s.wallet);
  const connected = useMarketStore((s) => s.connected);
  const navigate = useNavigate();

  const logout = async () => {
    try {
      await post('/auth/logout');
    } finally {
      clear();
      navigate('/login');
    }
  };

  return (
    <header className="flex h-14 items-center justify-between gap-3 border-b border-ink-700 bg-ink-900 px-4">
      <div className="flex items-center gap-3">
        <button
          className="rounded border border-ink-600 px-2 py-1 text-fg-muted lg:hidden"
          onClick={onMenu}
          aria-label="Open menu"
        >
          ☰
        </button>
        <PaperBadge />
        <span className="hidden items-center gap-1.5 text-xs text-fg-muted sm:flex">
          <span className={connected ? 'h-2 w-2 rounded-full bg-buy' : 'h-2 w-2 rounded-full bg-sell'} />
          {connected ? 'Live feed' : 'Reconnecting…'}
        </span>
      </div>
      <div className="flex items-center gap-4">
        {wallet && (
          <div className="hidden text-right sm:block">
            <div className="text-[10px] uppercase tracking-wider text-fg-dim">Available</div>
            <div className="font-mono text-sm font-semibold">{formatINR(wallet.available)}</div>
          </div>
        )}
        <div className="hidden text-right md:block">
          <div className="text-sm">{user?.full_name}</div>
          <div className="text-[11px] text-fg-dim">{user?.role}</div>
        </div>
        <button
          onClick={logout}
          className="rounded border border-ink-600 px-3 py-1.5 text-xs text-fg-muted hover:text-fg"
        >
          Log out
        </button>
      </div>
    </header>
  );
}

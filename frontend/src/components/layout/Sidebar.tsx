import clsx from 'clsx';
import { NavLink } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';

const NAV = [
  { to: '/app', label: 'Dashboard', icon: '▦', end: true },
  { to: '/app/profit', label: 'Profit & Portfolio', icon: '₹' },
  { to: '/app/market', label: 'Live Market', icon: '◷' },
  { to: '/app/arbitrage', label: 'Arbitrage (NSE-BSE)', icon: '⇄' },
  { to: '/app/strategies', label: 'Strategies', icon: '⚙' },
  { to: '/app/backtester', label: 'Backtester', icon: '↺' },
  { to: '/app/orderbook', label: 'Order Book', icon: '≣' },
  { to: '/app/portfolio', label: 'Portfolio & Wallet', icon: '◫' },
  { to: '/app/history', label: 'Trade History', icon: '☰' },
  { to: '/app/risk', label: 'Risk Settings', icon: '⛨' },
  { to: '/app/profile', label: 'Profile', icon: '◉' },
];

const ADMIN_NAV = [
  { to: '/app/admin/users', label: 'Users', icon: '☺' },
  { to: '/app/admin/metrics', label: 'System Metrics', icon: '∿' },
];

function Item({
  to,
  label,
  icon,
  end,
  onNavigate,
}: {
  to: string;
  label: string;
  icon: string;
  end?: boolean;
  onNavigate?: () => void;
}) {
  return (
    <NavLink
      to={to}
      end={end}
      onClick={onNavigate}
      className={({ isActive }) =>
        clsx(
          'flex items-center gap-3 rounded-md px-3 py-2 text-sm transition',
          isActive
            ? 'bg-amber-soft font-semibold text-amber'
            : 'text-fg-muted hover:bg-ink-800 hover:text-fg',
        )
      }
    >
      <span className="w-4 text-center font-mono">{icon}</span>
      {label}
    </NavLink>
  );
}

export function Sidebar({ open, onNavigate }: { open: boolean; onNavigate: () => void }) {
  const isAdmin = useAuthStore((s) => s.user?.role === 'ADMIN');
  return (
    <aside
      className={clsx(
        'fixed inset-y-0 left-0 z-40 w-60 border-r border-ink-700 bg-ink-900 transition-transform lg:static lg:translate-x-0',
        open ? 'translate-x-0' : '-translate-x-full',
      )}
    >
      <div className="flex h-14 items-center gap-2 border-b border-ink-700 px-4">
        <svg viewBox="0 0 32 32" className="h-6 w-6" aria-hidden>
          <path
            d="M6 22 L12 14 L17 18 L26 8"
            stroke="#f5b942"
            strokeWidth="3"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        <span className="font-mono text-base font-semibold tracking-tight">
          Nano<span className="text-amber">EX</span> Web
        </span>
      </div>
      <nav className="flex flex-col gap-0.5 p-3" aria-label="Main">
        {NAV.map((n) => (
          <Item key={n.to} {...n} onNavigate={onNavigate} />
        ))}
        {isAdmin && (
          <>
            <div className="mt-4 px-3 pb-1 text-[10px] font-semibold uppercase tracking-wider text-fg-dim">
              Admin
            </div>
            {ADMIN_NAV.map((n) => (
              <Item key={n.to} {...n} onNavigate={onNavigate} />
            ))}
          </>
        )}
      </nav>
    </aside>
  );
}

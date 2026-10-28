import { Link } from 'react-router-dom';
import { DISCLAIMER, PaperBadge } from '../components/layout/Disclaimer';

const FEATURES = [
  [
    'Matching engine',
    'Price-time priority limit order book with market and limit orders, partial fills and live depth.',
  ],
  [
    'NSE-BSE arbitrage',
    'Watch the same stock on both exchanges, see spreads after every charge, and run two-leg paper trades.',
  ],
  [
    '9 strategies',
    'Momentum, mean reversion, Bollinger, RSI, breakout, MACD, EMA, Z-score and an ensemble vote.',
  ],
  ['Backtester', 'Seeded, reproducible runs with Sharpe, Sortino, drawdown and a real Indian cost model.'],
  ['Risk manager', 'Quantity and value caps, daily loss limit, volume cap and a one-click kill switch.'],
  ['Profit dashboard', 'Rs 5,00,000 virtual wallet, top-ups, P&L by strategy, equity curve and CSV export.'],
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-ink-950 text-fg">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <span className="font-mono text-lg font-semibold">
          Nano<span className="text-amber">EX</span> Web
        </span>
        <div className="flex gap-3">
          <Link to="/login" className="rounded-md px-4 py-2 text-sm text-fg-muted hover:text-fg">
            Log in
          </Link>
          <Link to="/register" className="rounded-md bg-amber px-4 py-2 text-sm font-semibold text-ink-950">
            Create account
          </Link>
        </div>
      </header>
      <section className="mx-auto max-w-6xl px-6 pb-16 pt-10">
        <PaperBadge />
        <h1 className="mt-5 max-w-3xl text-4xl font-semibold leading-tight md:text-5xl">
          Learn how high-frequency trading works on a simulated{' '}
          <span className="text-amber">NSE and BSE</span>.
        </h1>
        <p className="mt-5 max-w-2xl text-lg text-fg-muted">
          Start with ₹5,00,000 of virtual money. Place orders into a real matching engine, run strategy bots,
          backtest ideas and test cross-exchange arbitrage, with every brokerage, STT, GST and stamp-duty
          rupee counted.
        </p>
        <div className="mt-8 flex gap-3">
          <Link to="/register" className="rounded-md bg-amber px-5 py-3 font-semibold text-ink-950">
            Enter the trading floor
          </Link>
          <Link
            to="/login"
            className="rounded-md border border-ink-600 px-5 py-3 text-fg-muted hover:text-fg"
          >
            I have an account
          </Link>
        </div>
        <div className="mt-16 grid gap-4 md:grid-cols-3">
          {FEATURES.map(([title, body]) => (
            <div key={title} className="rounded-lg border border-ink-700 bg-ink-850 p-5">
              <h3 className="font-semibold text-amber">{title}</h3>
              <p className="mt-2 text-sm text-fg-muted">{body}</p>
            </div>
          ))}
        </div>
      </section>
      <footer className="border-t border-ink-700 px-6 py-4 text-center text-xs text-fg-dim">
        {DISCLAIMER}
      </footer>
    </div>
  );
}

// Shared API types (mirror the FastAPI schemas).

export type Side = 'BUY' | 'SELL';
export type Exchange = 'NSE' | 'BSE';
export type OrderType = 'MARKET' | 'LIMIT';

export interface ApiEnvelope<T> {
  success: boolean;
  data: T;
  error: { code: string; message: string; details?: Record<string, unknown> } | null;
  meta: Record<string, unknown> | null;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: 'USER' | 'ADMIN';
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface Wallet {
  id: string;
  balance: number;
  blocked_margin: number;
  available: number;
  initial_balance: number;
  capital_added: number;
  updated_at: string;
}

export interface WalletTxn {
  id: string;
  type: string;
  amount: number;
  balance_after: number;
  note: string | null;
  created_at: string;
}

export interface Quote {
  symbol: string;
  exchange: Exchange;
  bid: number;
  ask: number;
  last: number;
  volume: number;
  timestamp: number;
}

export interface DepthLevel {
  price: number;
  quantity: number;
  orders: number;
}

export interface Depth {
  symbol: string;
  exchange: Exchange;
  bids: DepthLevel[];
  asks: DepthLevel[];
}

export interface Order {
  id: string;
  symbol: string;
  exchange: Exchange;
  side: Side;
  order_type: OrderType;
  price: number | null;
  quantity: number;
  filled_qty: number;
  avg_fill_price: number | null;
  status: 'NEW' | 'PARTIAL' | 'FILLED' | 'CANCELLED' | 'REJECTED';
  source: 'MANUAL' | 'STRATEGY' | 'ARBITRAGE';
  strategy_name: string | null;
  signal_reason: string | null;
  reject_reason: string | null;
  latency_us: number | null;
  created_at: string;
}

export interface Trade {
  id: string;
  order_id: string;
  symbol: string;
  exchange: Exchange;
  side: Side;
  price: number;
  quantity: number;
  fees: number;
  realized_pnl: number;
  source: string;
  strategy_name: string | null;
  signal_reason: string | null;
  executed_at: string;
}

export interface Position {
  symbol: string;
  quantity: number;
  side: 'LONG' | 'SHORT';
  avg_price: number;
  mark_price: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pct: number;
  realized_pnl: number;
}

export interface PortfolioSummary {
  cash: number;
  blocked: number;
  available: number;
  market_value: number;
  equity: number;
  capital_added: number;
  realized_pnl: number;
  unrealized_pnl: number;
  total_fees: number;
  net_realized_pnl: number;
  total_pnl: number;
  total_return_pct: number;
  open_positions: number;
  trade_count: number;
}

export interface ProfitDashboard {
  summary: PortfolioSummary;
  by_source: { source: string; pnl: number }[];
  by_strategy: { name: string; pnl: number }[];
  by_symbol: { symbol: string; pnl: number }[];
  daily: { date: string; pnl: number }[];
  win_rate_pct: number;
  closed_trades: number;
  best_trade: number;
  worst_trade: number;
  arbitrage_net_pnl: number;
  positions: Position[];
  equity_curve: { t: string; equity: number }[];
}

export interface CostBreakdown {
  brokerage: number;
  stt: number;
  exchange_txn: number;
  sebi: number;
  gst: number;
  stamp: number;
  slippage: number;
  total: number;
}

export interface Opportunity {
  symbol: string;
  buy_exchange: Exchange;
  sell_exchange: Exchange;
  buy_price: number;
  sell_price: number;
  spread_abs: number;
  spread_pct: number;
  quantity: number;
  max_qty: number;
  gross_profit: number;
  est_costs: number;
  cost_breakdown: CostBreakdown;
  est_net_profit: number;
  liquidity_ok: boolean;
  confidence: 'HIGH' | 'MEDIUM' | 'LOW';
  actionable?: boolean;
}

export interface SpreadRow {
  symbol: string;
  nse_last: number;
  bse_last: number;
  nse_bid: number;
  nse_ask: number;
  bse_bid: number;
  bse_ask: number;
  spread_abs: number;
  spread_pct: number;
  timestamp: number;
  opportunity?: Opportunity;
}

export interface ArbTrade {
  id: string;
  symbol: string;
  buy_exchange: Exchange;
  sell_exchange: Exchange;
  quantity: number;
  matched_qty: number;
  mode: 'MANUAL' | 'AUTO';
  status: 'COMPLETED' | 'PARTIAL' | 'HEDGED' | 'FAILED';
  expected_spread: number;
  captured_spread: number;
  gross_pnl: number;
  total_costs: number;
  net_pnl: number;
  latency_ms: number;
  failure_reason: string | null;
  created_at: string;
}

export interface ArbStats {
  attempts: number;
  executed: number;
  completed: number;
  hit_rate_pct: number;
  cumulative_net_pnl: number;
  total_costs: number;
  avg_spread_captured: number;
  avg_latency_ms: number;
  status_counts: Record<string, number>;
  curve: { t: string; cumulative_pnl: number }[];
}

export interface ParamSpec {
  default: number;
  min: number;
  max: number;
  description: string;
  type: 'int' | 'float';
}

export interface StrategyType {
  key: string;
  name: string;
  description: string;
  params: Record<string, ParamSpec>;
}

export interface StrategyConfig {
  id: string;
  name: string;
  strategy_type: string;
  symbol: string;
  exchange: Exchange;
  params: Record<string, number>;
  quantity: number;
  stop_loss_pct: number | null;
  take_profit_pct: number | null;
  trailing_stop_pct: number | null;
  is_active: boolean;
  created_at: string;
  runtime: { running: boolean; held: number; last_signal: string | null } | null;
}

export interface BacktestMetrics {
  initial_capital: number;
  final_equity: number;
  total_return_pct: number;
  buy_hold_return_pct: number;
  win_rate_pct: number;
  max_drawdown_pct: number;
  sharpe: number;
  sortino: number;
  profit_factor: number | null;
  num_trades: number;
  avg_trade_pnl: number;
  total_costs: number;
  exposure_pct: number;
  bars: number;
}

export interface BacktestResult {
  id?: string;
  metrics: BacktestMetrics;
  equity_curve: { i: number; price: number; equity: number; buy_hold: number }[];
  trades: {
    entry_index: number;
    exit_index: number;
    entry_price: number;
    exit_price: number;
    quantity: number;
    pnl: number;
    costs: number;
    return_pct: number;
    entry_reason: string;
    exit_reason: string;
  }[];
}

export interface RiskSettings {
  max_order_qty: number;
  max_order_notional: number;
  max_position_value: number;
  daily_loss_limit: number;
  daily_volume_cap: number;
  max_open_orders: number;
  kill_switch: boolean;
  arb_min_profit: number;
  arb_quantity: number;
  arb_auto_enabled: boolean;
}

export interface PerfMetrics {
  uptime_seconds: number;
  orders_total: number;
  trades_total: number;
  ticks_total: number;
  rejected_total: number;
  orders_per_sec: number;
  avg_order_latency_us: number;
  avg_tick_to_trade_us: number;
}

import { AuditLog } from '../../components/AuditLog';
import { Card, ErrorState, Loading, PageHeader, StatCard } from '../../components/ui';
import { useApi } from '../../hooks/useApi';
import { get } from '../../services/api';
import type { PerfMetrics } from '../../types';
import { formatDuration, formatInt, formatNum } from '../../utils/format';

interface SystemMetrics extends PerfMetrics {
  users: number;
  orders: number;
  trades: number;
  active_bots: number;
  ws_market_clients: number;
  market_provider: string;
  market_running: boolean;
}

export default function AdminMetrics() {
  const { data, error, loading, refetch } = useApi(() => get<SystemMetrics>('/admin/metrics'), [], 3000);
  if (loading && !data) return <Loading />;
  if (error || !data) return <ErrorState message={error?.message ?? 'Failed'} onRetry={refetch} />;
  return (
    <div>
      <PageHeader
        title="System Metrics"
        subtitle="Live counters from the backend (also exposed at /metrics in Prometheus format)."
      />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Uptime" value={formatDuration(data.uptime_seconds)} />
        <StatCard label="Orders / sec (1m)" value={formatNum(data.orders_per_sec, 3)} tone="amber" />
        <StatCard label="Avg order latency" value={`${formatNum(data.avg_order_latency_us / 1000)} ms`} />
        <StatCard label="Tick-to-trade" value={`${formatNum(data.avg_tick_to_trade_us / 1000)} ms`} />
        <StatCard label="Users" value={formatInt(data.users)} />
        <StatCard
          label="Orders (all time)"
          value={formatInt(data.orders)}
          sub={`${formatInt(data.rejected_total)} rejected since start`}
        />
        <StatCard label="Trades (all time)" value={formatInt(data.trades)} />
        <StatCard label="Ticks processed" value={formatInt(data.ticks_total)} />
      </div>
      <Card title="Runtime" className="mt-4">
        <dl className="grid grid-cols-2 gap-2 text-sm md:grid-cols-4">
          <dt className="text-fg-muted">Market provider</dt>
          <dd className="font-mono">{data.market_provider}</dd>
          <dt className="text-fg-muted">Feed running</dt>
          <dd className={data.market_running ? 'text-buy' : 'text-sell'}>
            {data.market_running ? 'yes' : 'no'}
          </dd>
          <dt className="text-fg-muted">Active strategy bots</dt>
          <dd className="font-mono">{data.active_bots}</dd>
          <dt className="text-fg-muted">Market WebSocket clients</dt>
          <dd className="font-mono">{data.ws_market_clients}</dd>
        </dl>
      </Card>
      <AuditLog />
    </div>
  );
}

import { useState } from 'react';
import { Badge, Card, ErrorState, Loading, Select } from './ui';
import { Pager, Table } from './ui/Table';
import { useApi } from '../hooks/useApi';
import { api } from '../services/api';
import { formatTime } from '../utils/format';

interface AuditEntry {
  id: string;
  user_id: string | null;
  action: string;
  entity: string | null;
  entity_id: string | null;
  ip_address: string | null;
  details: Record<string, unknown> | null;
  created_at: string;
}

const ACTIONS = [
  'LOGIN',
  'LOGIN_FAILED',
  'LOGOUT',
  'REGISTER',
  'PASSWORD_CHANGE',
  'ORDER',
  'ORDER_CANCEL',
  'ARBITRAGE',
  'WALLET_TOPUP',
  'WALLET_RESET',
  'RISK_CHANGE',
  'KILL_SWITCH',
  'ADMIN_ACTION',
];
const SIZE = 15;

const tone = (a: string) =>
  a === 'LOGIN_FAILED' || a === 'KILL_SWITCH' ? 'sell' : a === 'ADMIN_ACTION' ? 'amber' : 'muted';

/** Admin audit trail with an action filter. */
export function AuditLog() {
  const [action, setAction] = useState('');
  const [page, setPage] = useState(1);
  const { data, error, loading, refetch } = useApi(
    () =>
      api<AuditEntry[]>({
        url: '/admin/audit-logs',
        params: { page, size: SIZE, ...(action ? { action } : {}) },
      }),
    [page, action],
    10000,
  );

  return (
    <Card
      title="Audit log"
      className="mt-4"
      actions={
        <div className="w-44">
          <Select
            aria-label="Filter by action"
            value={action}
            onChange={(e) => {
              setAction(e.target.value);
              setPage(1);
            }}
            className="py-1 text-xs"
          >
            <option value="">All actions</option>
            {ACTIONS.map((a) => (
              <option key={a}>{a}</option>
            ))}
          </Select>
        </div>
      }
    >
      {loading && !data ? (
        <Loading />
      ) : error ? (
        <ErrorState message={error.message} onRetry={refetch} />
      ) : (
        <>
          <Table
            dense
            rows={data?.data ?? []}
            rowKey={(r) => r.id}
            empty="No audit entries."
            columns={[
              { key: 't', header: 'Time', render: (r) => formatTime(r.created_at) },
              { key: 'a', header: 'Action', render: (r) => <Badge tone={tone(r.action)}>{r.action}</Badge> },
              {
                key: 'u',
                header: 'User',
                render: (r) => (
                  <span className="font-mono text-xs text-fg-muted">{r.user_id?.slice(0, 8) ?? '—'}</span>
                ),
              },
              {
                key: 'ip',
                header: 'IP',
                render: (r) => <span className="font-mono text-xs">{r.ip_address ?? '—'}</span>,
              },
              {
                key: 'd',
                header: 'Details',
                render: (r) => (
                  <span
                    className="block max-w-md truncate font-mono text-xs text-fg-dim"
                    title={JSON.stringify(r.details)}
                  >
                    {r.details ? JSON.stringify(r.details) : ''}
                  </span>
                ),
              },
            ]}
          />
          <Pager page={page} size={SIZE} total={Number(data?.meta?.total ?? 0)} onPage={setPage} />
        </>
      )}
    </Card>
  );
}

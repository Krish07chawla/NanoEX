import { useState } from 'react';
import { Badge, Button, Card, PageHeader } from '../../components/ui';
import { Pager, Table } from '../../components/ui/Table';
import { useApi } from '../../hooks/useApi';
import { ApiError, api, patch, post } from '../../services/api';
import { useAuthStore } from '../../store/authStore';
import { toast } from '../../store/toastStore';
import { formatINR, formatTime } from '../../utils/format';

interface AdminUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
  balance: number;
}

export default function AdminUsers() {
  const me = useAuthStore((s) => s.user);
  const [page, setPage] = useState(1);
  const users = useApi(() => api<AdminUser[]>({ url: '/admin/users', params: { page, size: 20 } }), [page]);

  const toggle = async (u: AdminUser) => {
    try {
      await patch(`/admin/users/${u.id}`, { is_active: !u.is_active });
      users.refetch();
    } catch (e) {
      toast.error('Update failed', e instanceof ApiError ? e.message : String(e));
    }
  };

  const adjust = async (u: AdminUser) => {
    const raw = window.prompt(`Adjust ${u.email}'s wallet by (₹, negative to deduct):`, '10000');
    if (!raw) return;
    const note = window.prompt('Reason (kept in the audit log):', 'Admin adjustment') ?? 'Admin adjustment';
    try {
      await post(`/admin/users/${u.id}/wallet-adjust`, { amount: Number(raw), note });
      toast.success('Wallet adjusted');
      users.refetch();
    } catch (e) {
      toast.error('Adjustment failed', e instanceof ApiError ? e.message : String(e));
    }
  };

  return (
    <div>
      <PageHeader
        title="Users"
        subtitle="Admin view: enable or disable accounts and adjust virtual wallets."
      />
      <Card>
        <Table<AdminUser>
          rows={users.data?.data ?? []}
          rowKey={(u) => u.id}
          columns={[
            {
              key: 'e',
              header: 'User',
              render: (u) => (
                <div>
                  <div className="font-semibold">{u.full_name}</div>
                  <div className="text-xs text-fg-dim">{u.email}</div>
                </div>
              ),
            },
            {
              key: 'r',
              header: 'Role',
              render: (u) => <Badge tone={u.role === 'ADMIN' ? 'amber' : 'muted'}>{u.role}</Badge>,
            },
            {
              key: 's',
              header: 'Status',
              render: (u) => (
                <Badge tone={u.is_active ? 'buy' : 'sell'}>{u.is_active ? 'ACTIVE' : 'DISABLED'}</Badge>
              ),
            },
            { key: 'b', header: 'Wallet', align: 'right', render: (u) => formatINR(u.balance) },
            {
              key: 'l',
              header: 'Last login',
              render: (u) => (
                <span className="text-fg-dim">{u.last_login_at ? formatTime(u.last_login_at) : 'never'}</span>
              ),
            },
            {
              key: 'a',
              header: '',
              align: 'right',
              render: (u) => (
                <div className="flex justify-end gap-1">
                  <Button variant="ghost" className="px-2 py-1 text-xs" onClick={() => adjust(u)}>
                    Adjust wallet
                  </Button>
                  {u.id !== me?.id && (
                    <Button
                      variant={u.is_active ? 'danger' : 'buy'}
                      className="px-2 py-1 text-xs"
                      onClick={() => toggle(u)}
                    >
                      {u.is_active ? 'Disable' : 'Enable'}
                    </Button>
                  )}
                </div>
              ),
            },
          ]}
        />
        {users.data?.meta && (
          <Pager page={page} size={20} total={Number(users.data.meta.total)} onPage={setPage} />
        )}
      </Card>
    </div>
  );
}

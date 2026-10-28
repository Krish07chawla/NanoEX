import { useState, type FormEvent } from 'react';
import { Button, Card, Field, Input, PageHeader } from '../components/ui';
import { ApiError, patch, post } from '../services/api';
import { useAuthStore } from '../store/authStore';
import { toast } from '../store/toastStore';
import type { User } from '../types';
import { formatTime } from '../utils/format';
import { passwordProblem } from './Register';

export default function Profile() {
  const { user, setUser } = useAuthStore();
  const [name, setName] = useState(user?.full_name ?? '');
  const [pw, setPw] = useState({ current_password: '', new_password: '', confirm: '' });

  const saveName = async (e: FormEvent) => {
    e.preventDefault();
    try {
      setUser(await patch<User>('/users/me', { full_name: name }));
      toast.success('Profile updated');
    } catch (err) {
      toast.error('Update failed', err instanceof ApiError ? err.message : String(err));
    }
  };

  const changePassword = async (e: FormEvent) => {
    e.preventDefault();
    const problem = passwordProblem(pw.new_password);
    if (problem) return toast.error('Weak password', problem);
    if (pw.new_password !== pw.confirm) return toast.error('Passwords do not match');
    try {
      await post('/auth/change-password', {
        current_password: pw.current_password,
        new_password: pw.new_password,
      });
      setPw({ current_password: '', new_password: '', confirm: '' });
      toast.success('Password changed', 'Other sessions have been signed out.');
    } catch (err) {
      toast.error('Could not change password', err instanceof ApiError ? err.message : String(err));
    }
  };

  return (
    <div>
      <PageHeader title="Profile" />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Account">
          <dl className="mb-4 grid grid-cols-2 gap-2 text-sm">
            <dt className="text-fg-muted">Email</dt>
            <dd>{user?.email}</dd>
            <dt className="text-fg-muted">Role</dt>
            <dd>{user?.role}</dd>
            <dt className="text-fg-muted">Member since</dt>
            <dd>{user ? formatTime(user.created_at) : ''}</dd>
          </dl>
          <form onSubmit={saveName} className="space-y-3">
            <Field label="Full name">
              <Input value={name} onChange={(e) => setName(e.target.value)} minLength={2} required />
            </Field>
            <Button type="submit">Save</Button>
          </form>
        </Card>
        <Card title="Change password">
          <form onSubmit={changePassword} className="space-y-3">
            <Field label="Current password">
              <Input
                type="password"
                value={pw.current_password}
                onChange={(e) => setPw({ ...pw, current_password: e.target.value })}
                required
              />
            </Field>
            <Field label="New password" hint="8+ characters with a letter and a number">
              <Input
                type="password"
                value={pw.new_password}
                onChange={(e) => setPw({ ...pw, new_password: e.target.value })}
                required
              />
            </Field>
            <Field label="Confirm new password">
              <Input
                type="password"
                value={pw.confirm}
                onChange={(e) => setPw({ ...pw, confirm: e.target.value })}
                required
              />
            </Field>
            <Button type="submit">Change password</Button>
          </form>
        </Card>
      </div>
    </div>
  );
}

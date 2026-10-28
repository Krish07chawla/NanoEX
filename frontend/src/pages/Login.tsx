import { useState, type FormEvent } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Button, Field, Input } from '../components/ui';
import { DISCLAIMER, PaperBadge } from '../components/layout/Disclaimer';
import { ApiError, post } from '../services/api';
import { useAuthStore } from '../store/authStore';
import type { User } from '../types';

export function AuthShell({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-ink-950 px-4 text-fg">
      <div className="w-full max-w-md">
        <Link to="/" className="mb-6 block text-center font-mono text-xl font-semibold">
          Nano<span className="text-amber">EX</span> Web
        </Link>
        <div className="rounded-lg border border-ink-700 bg-ink-850 p-6">
          <div className="mb-4 flex items-center justify-between">
            <h1 className="text-lg font-semibold">{title}</h1>
            <PaperBadge />
          </div>
          {children}
        </div>
        <p
          className="mt-4 rounded-md border border-amber/30 bg-amber-soft px-4 py-3 text-xs text-amber"
          role="note"
        >
          {DISCLAIMER}
        </p>
      </div>
    </div>
  );
}

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const setSession = useAuthStore((s) => s.setSession);
  const navigate = useNavigate();
  const from = (useLocation().state as { from?: string } | null)?.from ?? '/app';

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const data = await post<{ access_token: string; user: User }>('/auth/login', { email, password });
      setSession(data.user, data.access_token);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Login failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="Log in">
      <form onSubmit={submit} className="space-y-4">
        <Field label="Email">
          <Input
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </Field>
        <Field label="Password">
          <Input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </Field>
        {error && <div className="rounded-md bg-sell-soft px-3 py-2 text-sm text-sell">{error}</div>}
        <Button type="submit" loading={busy} className="w-full">
          Log in
        </Button>
        <p className="text-center text-sm text-fg-muted">
          New here?{' '}
          <Link to="/register" className="text-amber">
            Create an account
          </Link>
        </p>
      </form>
    </AuthShell>
  );
}

import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button, Field, Input } from '../components/ui';
import { AuthShell } from './Login';
import { ApiError, post } from '../services/api';
import { useAuthStore } from '../store/authStore';
import type { User } from '../types';

export function passwordProblem(pw: string): string | null {
  if (pw.length < 8) return 'At least 8 characters';
  if (!/[A-Za-z]/.test(pw) || !/\d/.test(pw)) return 'Use at least one letter and one number';
  return null;
}

export default function Register() {
  const [form, setForm] = useState({ full_name: '', email: '', password: '', confirm: '' });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const setSession = useAuthStore((s) => s.setSession);
  const navigate = useNavigate();
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [k]: e.target.value });

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const problem = passwordProblem(form.password);
    if (problem) return setError(problem);
    if (form.password !== form.confirm) return setError('Passwords do not match');
    setBusy(true);
    setError(null);
    try {
      await post<User>('/auth/register', {
        email: form.email,
        password: form.password,
        full_name: form.full_name,
      });
      const data = await post<{ access_token: string; user: User }>('/auth/login', {
        email: form.email,
        password: form.password,
      });
      setSession(data.user, data.access_token);
      navigate('/app', { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Registration failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="Create account">
      <form onSubmit={submit} className="space-y-4">
        <Field label="Full name">
          <Input value={form.full_name} onChange={set('full_name')} minLength={2} required />
        </Field>
        <Field label="Email">
          <Input type="email" autoComplete="email" value={form.email} onChange={set('email')} required />
        </Field>
        <Field label="Password" hint="8+ characters with a letter and a number">
          <Input
            type="password"
            autoComplete="new-password"
            value={form.password}
            onChange={set('password')}
            required
          />
        </Field>
        <Field label="Confirm password">
          <Input
            type="password"
            autoComplete="new-password"
            value={form.confirm}
            onChange={set('confirm')}
            required
          />
        </Field>
        {error && <div className="rounded-md bg-sell-soft px-3 py-2 text-sm text-sell">{error}</div>}
        <Button type="submit" loading={busy} className="w-full">
          Create account and get ₹5,00,000 virtual
        </Button>
        <p className="text-center text-sm text-fg-muted">
          Already registered?{' '}
          <Link to="/login" className="text-amber">
            Log in
          </Link>
        </p>
      </form>
    </AuthShell>
  );
}

import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { Loading } from '../ui';

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { accessToken, bootstrapped } = useAuthStore();
  const location = useLocation();
  if (!bootstrapped) return <Loading label="Restoring session…" />;
  if (!accessToken) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return <>{children}</>;
}

export function AdminRoute({ children }: { children: ReactNode }) {
  const role = useAuthStore((s) => s.user?.role);
  if (role !== 'ADMIN') return <Navigate to="/app" replace />;
  return <>{children}</>;
}

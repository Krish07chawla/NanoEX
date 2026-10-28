// Axios client: attaches the access token, refreshes it once on 401 (refresh token is an httpOnly cookie).
import axios, { AxiosError, type AxiosRequestConfig } from 'axios';
import type { ApiEnvelope } from '../types';
import { useAuthStore } from '../store/authStore';

export const http = axios.create({ baseURL: '/api/v1', withCredentials: true });

http.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshing: Promise<string | null> | null = null;

export async function refreshAccessToken(): Promise<string | null> {
  if (!refreshing) {
    refreshing = axios
      .post<ApiEnvelope<{ access_token: string }>>('/api/v1/auth/refresh', null, { withCredentials: true })
      .then((r) => {
        useAuthStore.getState().setToken(r.data.data.access_token);
        return r.data.data.access_token;
      })
      .catch(() => null)
      .finally(() => {
        refreshing = null;
      });
  }
  return refreshing;
}

http.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const original = error.config as AxiosRequestConfig & { _retried?: boolean };
    const isAuthCall = original?.url?.startsWith('/auth/');
    if (error.response?.status === 401 && original && !original._retried && !isAuthCall) {
      original._retried = true;
      const token = await refreshAccessToken();
      if (token) return http(original);
      useAuthStore.getState().clear();
    }
    return Promise.reject(error);
  },
);

export class ApiError extends Error {
  constructor(
    message: string,
    public code: string,
    public status?: number,
    public details?: Record<string, unknown>,
  ) {
    super(message);
  }
}

function toApiError(e: unknown): ApiError {
  if (axios.isAxiosError(e)) {
    const body = e.response?.data as ApiEnvelope<unknown> | undefined;
    if (body?.error)
      return new ApiError(body.error.message, body.error.code, e.response?.status, body.error.details);
    return new ApiError(e.message, 'NETWORK_ERROR', e.response?.status);
  }
  return new ApiError(String(e), 'UNKNOWN');
}

/** Unwrap the {success, data, error, meta} envelope. */
export async function api<T>(
  config: AxiosRequestConfig,
): Promise<{ data: T; meta: Record<string, unknown> | null }> {
  try {
    const r = await http.request<ApiEnvelope<T>>(config);
    return { data: r.data.data, meta: r.data.meta };
  } catch (e) {
    throw toApiError(e);
  }
}

export const get = async <T>(url: string, params?: Record<string, unknown>) =>
  (await api<T>({ url, params })).data;
export const post = async <T>(url: string, data?: unknown) =>
  (await api<T>({ url, method: 'POST', data })).data;
export const put = async <T>(url: string, data?: unknown) =>
  (await api<T>({ url, method: 'PUT', data })).data;
export const patch = async <T>(url: string, data?: unknown) =>
  (await api<T>({ url, method: 'PATCH', data })).data;
export const del = async <T>(url: string) => (await api<T>({ url, method: 'DELETE' })).data;

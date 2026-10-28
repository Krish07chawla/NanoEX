import { create } from 'zustand';
import type { User } from '../types';

interface AuthState {
  user: User | null;
  accessToken: string | null;
  bootstrapped: boolean;
  setSession: (user: User, token: string) => void;
  setToken: (token: string) => void;
  setUser: (user: User) => void;
  setBootstrapped: () => void;
  clear: () => void;
}

// Access token is kept in memory only (never localStorage) to limit XSS exposure.
export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: null,
  bootstrapped: false,
  setSession: (user, accessToken) => set({ user, accessToken }),
  setToken: (accessToken) => set({ accessToken }),
  setUser: (user) => set({ user }),
  setBootstrapped: () => set({ bootstrapped: true }),
  clear: () => set({ user: null, accessToken: null }),
}));

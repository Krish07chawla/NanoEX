import { create } from 'zustand';
import type { Wallet } from '../types';
import { get } from '../services/api';

// Wallet + a "version" counter that pages watch to refetch after fills arrive over the user socket.
interface AccountState {
  wallet: Wallet | null;
  version: number;
  loadWallet: () => Promise<void>;
  setWallet: (w: Wallet) => void;
  bump: () => void;
}

export const useAccountStore = create<AccountState>((set) => ({
  wallet: null,
  version: 0,
  loadWallet: async () => set({ wallet: await get<Wallet>('/wallet') }),
  setWallet: (wallet) => set({ wallet }),
  bump: () => set((s) => ({ version: s.version + 1 })),
}));

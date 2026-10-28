import { create } from 'zustand';
import type { Depth, Exchange, Quote, SpreadRow } from '../types';

const HISTORY_POINTS = 240;

export const quoteKey = (symbol: string, exchange: Exchange) => `${symbol}:${exchange}`;

interface MarketState {
  connected: boolean;
  quotes: Record<string, Quote>;
  history: Record<string, { t: number; price: number }[]>;
  spreads: SpreadRow[];
  depth: Depth | null;
  lastTick: number;
  setConnected: (v: boolean) => void;
  applyTicks: (ticks: Quote[]) => void;
  setSpreads: (rows: SpreadRow[]) => void;
  setDepth: (d: Depth) => void;
  seedHistory: (key: string, points: { t: number; price: number }[]) => void;
}

export const useMarketStore = create<MarketState>((set) => ({
  connected: false,
  quotes: {},
  history: {},
  spreads: [],
  depth: null,
  lastTick: 0,
  setConnected: (connected) => set({ connected }),
  applyTicks: (ticks) =>
    set((s) => {
      const quotes = { ...s.quotes };
      const history = { ...s.history };
      for (const q of ticks) {
        const key = quoteKey(q.symbol, q.exchange);
        quotes[key] = q;
        const prev = history[key] ?? [];
        history[key] = [...prev.slice(-(HISTORY_POINTS - 1)), { t: q.timestamp, price: q.last }];
      }
      return { quotes, history, lastTick: Date.now() };
    }),
  setSpreads: (spreads) => set({ spreads }),
  setDepth: (depth) => set({ depth }),
  seedHistory: (key, points) =>
    set((s) =>
      s.history[key]?.length > 5 ? s : { history: { ...s.history, [key]: points.slice(-HISTORY_POINTS) } },
    ),
}));

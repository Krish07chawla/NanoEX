import { useEffect } from 'react';
import { connectSocket, type WsMessage } from '../services/ws';
import { useAuthStore } from '../store/authStore';
import { useMarketStore } from '../store/marketStore';
import { useAccountStore } from '../store/accountStore';
import { toast } from '../store/toastStore';
import type { ArbTrade, Depth, Order, Quote, SpreadRow, Trade, Wallet } from '../types';
import { formatINR } from '../utils/format';

let marketSocket: ReturnType<typeof connectSocket> | null = null;

/** Ask the market socket to stream depth for one book. */
export const selectDepthBook = (symbol: string, exchange: string) =>
  marketSocket?.send({ action: 'depth', symbol, exchange });

/** Connects /ws/market and /ws/user while the user is logged in. Mounted once in the app layout. */
export function useStreams() {
  const token = useAuthStore((s) => s.accessToken);
  const loggedIn = Boolean(token);

  useEffect(() => {
    if (!loggedIn) return;
    const market = useMarketStore.getState();
    marketSocket = connectSocket(
      '/ws/market',
      (m: WsMessage) => {
        if (m.type === 'tick') market.applyTicks(m.data as Quote[]);
        else if (m.type === 'arb_opportunity') market.setSpreads(m.data as SpreadRow[]);
        else if (m.type === 'depth') market.setDepth(m.data as Depth);
      },
      market.setConnected,
    );

    const account = useAccountStore.getState();
    const user = connectSocket('/ws/user', (m: WsMessage) => {
      const data = m.data as Record<string, unknown>;
      if (m.type === 'wallet') account.setWallet(data.wallet as Wallet);
      if (m.type === 'trade') {
        const t = data.trade as Trade;
        toast.success(
          `${t.side} ${t.quantity} ${t.symbol} filled`,
          `@ ${formatINR(t.price)} on ${t.exchange}`,
        );
        account.loadWallet();
        account.bump();
      }
      if (m.type === 'order_update') {
        const o = data.order as Order;
        if (o.status === 'REJECTED') toast.error(`Order rejected: ${o.symbol}`, o.reject_reason ?? undefined);
        account.bump();
      }
      if (m.type === 'arb_result') {
        const a = data.arbitrage as ArbTrade;
        const fn =
          a.status === 'COMPLETED' ? toast.success : a.status === 'FAILED' ? toast.error : toast.warning;
        fn(`Arbitrage ${a.status}: ${a.symbol}`, `Net ${formatINR(a.net_pnl)} · ${a.latency_ms} ms`);
        account.bump();
      }
    });
    return () => {
      marketSocket?.close();
      marketSocket = null;
      user.close();
    };
  }, [loggedIn]);
}

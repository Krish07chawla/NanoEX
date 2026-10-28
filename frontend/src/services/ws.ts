// Reconnecting WebSocket helper for /ws/market and /ws/user.
import { useAuthStore } from '../store/authStore';

export interface WsMessage<T = unknown> {
  type: string;
  data: T;
}

const RECONNECT_MS = 2000;

export function connectSocket(
  path: string,
  onMessage: (m: WsMessage) => void,
  onStatus?: (open: boolean) => void,
) {
  let socket: WebSocket | null = null;
  let closed = false;
  let timer: ReturnType<typeof setTimeout> | undefined;

  const open = () => {
    const token = useAuthStore.getState().accessToken;
    if (!token || closed) return;
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    socket = new WebSocket(`${proto}://${window.location.host}${path}?token=${encodeURIComponent(token)}`);
    socket.onopen = () => onStatus?.(true);
    socket.onmessage = (e) => onMessage(JSON.parse(e.data) as WsMessage);
    socket.onclose = () => {
      onStatus?.(false);
      if (!closed) timer = setTimeout(open, RECONNECT_MS);
    };
  };
  open();

  return {
    send: (data: unknown) => socket?.readyState === WebSocket.OPEN && socket.send(JSON.stringify(data)),
    close: () => {
      closed = true;
      clearTimeout(timer);
      socket?.close();
    },
  };
}

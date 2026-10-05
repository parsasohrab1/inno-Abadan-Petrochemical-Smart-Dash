import { useEffect, useRef, useState } from "react";

export type LiveMessage = { channel: string; data: any };

/** WebSocket connection to the API gateway with automatic reconnection. */
export function useLiveFeed(onMessage?: (m: LiveMessage) => void) {
  const [connected, setConnected] = useState(false);
  const [last, setLast] = useState<LiveMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const cbRef = useRef(onMessage);
  cbRef.current = onMessage;

  useEffect(() => {
    let stop = false;
    let retry: ReturnType<typeof setTimeout>;

    const connect = () => {
      if (stop) return;
      const token = localStorage.getItem("cbm_token") ?? "";
      const url =
        (import.meta.env.VITE_WS_URL ?? "/ws") +
        (import.meta.env.VITE_WS_URL ? `?token=${token}` : "");
      const proto = location.protocol === "https:" ? "wss" : "ws";
      const full = url.startsWith("ws") ? url : `${proto}://${location.host}${url}`;
      const ws = new WebSocket(full);
      wsRef.current = ws;
      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        if (!stop) retry = setTimeout(connect, 3000);
      };
      ws.onerror = () => ws.close();
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data) as LiveMessage;
          setLast(msg);
          cbRef.current?.(msg);
        } catch {
          /* ignore */
        }
      };
    };
    connect();
    return () => {
      stop = true;
      clearTimeout(retry);
      wsRef.current?.close();
    };
  }, []);

  return { connected, last };
}

/**
 * Subscribe to backend Redis events over WebSocket.
 * Requires the user to hold dashboard:view scope (admin/fod/dpd/scd).
 * Falls back to polling real dashboard flags while the socket reconnects.
 */
import { useEffect, useRef, useState } from 'react';
import { useAppStore } from '../store/appStore';
import type { LiveFlag } from '../types';

export interface LiveEvent {
  event: string;
  [key: string]: unknown;
}

export function useLiveEvents(eventFilter?: string, maxBuffer = 20): { events: LiveEvent[]; connected: boolean } {
  const token = useAppStore((state) => state.token);
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!token) return;
    const tokenValue = token;
    let cancelled = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let pollTimer: ReturnType<typeof setTimeout> | null = null;

    function mergeEvents(nextEvents: LiveEvent[]) {
      setEvents((current) => {
        const merged = [...nextEvents, ...current];
        const seen = new Set<string>();
        return merged
          .filter((item) => {
            const key = String(item.id || `${item.event}-${JSON.stringify(item)}`);
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
          })
          .slice(0, maxBuffer);
      });
    }

    async function pollFlags() {
      if (cancelled || wsRef.current?.readyState === WebSocket.OPEN) return;
      if (eventFilter && eventFilter !== 'flag.created') return;
      const apiBase = import.meta.env.VITE_API_URL || '/api';
      try {
        const response = await fetch(`${apiBase}/dashboard/flags`, {
          headers: { Authorization: `Bearer ${tokenValue}` }
        });
        if (response.ok) {
          const body = (await response.json()) as { responses?: LiveFlag[] };
          mergeEvents((body.responses || []).map((flag) => ({ event: 'flag.created', ...flag })));
        }
      } catch {
        // The WebSocket reconnect loop is the primary live path.
      } finally {
        if (!cancelled && wsRef.current?.readyState !== WebSocket.OPEN) {
          pollTimer = setTimeout(pollFlags, 5000);
        }
      }
    }

    function connect() {
      if (cancelled) return;
      const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
      const host = window.location.host;
      const apiBase = (import.meta.env.VITE_API_URL || '/api').replace(/^http(s?):\/\/[^/]+/, '');
      const url = `${proto}://${host}${apiBase}/dashboard/live?token=${encodeURIComponent(tokenValue)}${eventFilter ? `&event=${encodeURIComponent(eventFilter)}` : ''}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;
      ws.onopen = () => setConnected(true);
      ws.onmessage = (ev) => {
        try {
          mergeEvents([JSON.parse(ev.data) as LiveEvent]);
        } catch {
          // Ignore non-JSON heartbeat or close frames.
        }
      };
      ws.onclose = () => {
        setConnected(false);
        wsRef.current = null;
        if (!cancelled) {
          reconnectTimer = setTimeout(connect, 3000);
          pollFlags();
        }
      };
      ws.onerror = () => {
        try {
          ws.close();
        } catch {
          // Ignore duplicate close attempts.
        }
      };
    }

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (pollTimer) clearTimeout(pollTimer);
      if (wsRef.current) {
        try {
          wsRef.current.close();
        } catch {
          // Ignore duplicate close attempts.
        }
        wsRef.current = null;
      }
    };
  }, [token, eventFilter, maxBuffer]);

  return { events, connected };
}

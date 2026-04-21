import { useCallback, useEffect, useRef, useState } from "react";
import { getWsBaseUrl, type VitalsHistoryPoint } from "../services/api";

export type VitalsWsMessage = {
  metric?: string;
  value?: number;
  unit?: string;
  timestamp?: string;
  alert_level?: number | null;
  source?: string;
  type?: string;
};

export type ConnectionStatus = "connected" | "connecting" | "disconnected";

const MAX_POINTS = 40;
const RECONNECT_MS = 3000;

export function useVitalsWebSocket(patientId: string | undefined): {
  latestReading: VitalsWsMessage | null;
  history: VitalsHistoryPoint[];
  connectionStatus: ConnectionStatus;
} {
  const [latestReading, setLatestReading] = useState<VitalsWsMessage | null>(null);
  const [history, setHistory] = useState<VitalsHistoryPoint[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("disconnected");
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<number | null>(null);
  const manualClose = useRef(false);

  const appendPoint = useCallback((msg: VitalsWsMessage) => {
    if (msg.metric == null || msg.value == null || !msg.timestamp) return;
    setHistory((prev) => {
      const next = [
        ...prev,
        {
          timestamp: msg.timestamp!,
          value: msg.value!,
          unit: msg.unit,
          metric: msg.metric,
        },
      ];
      return next.slice(-MAX_POINTS);
    });
    setLatestReading(msg);
  }, []);

  const connect = useCallback(() => {
    if (!patientId) {
      setConnectionStatus("disconnected");
      return;
    }
    manualClose.current = false;
    setConnectionStatus("connecting");
    const url = `${getWsBaseUrl()}/ws/vitals/${encodeURIComponent(patientId)}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionStatus("connected");
      if (reconnectRef.current) {
        window.clearTimeout(reconnectRef.current);
        reconnectRef.current = null;
      }
    };

    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(String(ev.data)) as VitalsWsMessage & { type?: string };
        if (data.type === "ping") return;
        if (data.metric != null && data.value != null) {
          appendPoint(data);
        }
      } catch {
        /* ignore */
      }
    };

    ws.onerror = () => {
      setConnectionStatus("disconnected");
    };

    ws.onclose = () => {
      wsRef.current = null;
      setConnectionStatus("disconnected");
      if (!manualClose.current && patientId) {
        reconnectRef.current = window.setTimeout(() => {
          connect();
        }, RECONNECT_MS);
      }
    };
  }, [appendPoint, patientId]);

  useEffect(() => {
    manualClose.current = false;
    connect();
    return () => {
      manualClose.current = true;
      if (reconnectRef.current) window.clearTimeout(reconnectRef.current);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connect]);

  return { latestReading, history, connectionStatus };
}

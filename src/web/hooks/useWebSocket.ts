import { useEffect, useRef, useCallback } from 'react';
import { authService } from '@/lib/auth';

interface WebSocketMessage {
  type: string;
  chat_id: string;
  data: any;
}

interface UseWebSocketOptions {
  onMessage?: (message: any) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
}

export function useWebSocket(
  pathOrId: string,
  options: UseWebSocketOptions = {},
  isFullPath: boolean = false
) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const optionsRef = useRef(options);
  
  // Use state or ref for path to ensure we reconnect to the right place
  const pathRef = useRef(pathOrId);

  optionsRef.current = options;
  pathRef.current = pathOrId;

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    const path = pathRef.current;
    if (!path) return;

    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = typeof window !== 'undefined' && (window as any).__API_URL__
      ? (window as any).__API_URL__.replace(/^https?:/, protocol)
      : `${protocol}//localhost:8000`;

    const wsUrl = isFullPath ? `${host}${path}` : `${host}/api/v1/ws/chats/${path}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        optionsRef.current.onConnect?.();
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          optionsRef.current.onMessage?.(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onclose = () => {
        optionsRef.current.onDisconnect?.();
        reconnectTimeoutRef.current = setTimeout(() => connect(), 5000);
      };

      ws.onerror = (error) => {
        optionsRef.current.onError?.(error);
      };
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [pathOrId]);

  return { connect, disconnect };
}

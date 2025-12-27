import { createContext, useContext, useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { useAuth } from './AuthContext';

const WebSocketContext = createContext();
export { WebSocketContext };

// API URL에서 WebSocket URL 생성 (http -> ws, https -> wss)
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_BASE_URL = API_URL.replace(/^http/, 'ws');

// 고급 재연결 설정
const RECONNECT_CONFIG = {
  initialDelay: 1000,       // 첫 재연결 대기 시간 (1초)
  maxDelay: 30000,          // 최대 대기 시간 (30초)
  maxRetries: 10,           // 최대 재시도 횟수
  backoffMultiplier: 1.5,   // 지수 백오프 배수
};

const PING_INTERVAL = 30000; // 30초마다 ping
const CONNECTION_TIMEOUT = 10000; // 연결 타임아웃 10초

export function WebSocketProvider({ children }) {
  const { user, token } = useAuth();
  const [isConnected, setIsConnected] = useState(false);
  const [connectionState, setConnectionState] = useState('disconnected'); // 'connecting', 'connected', 'disconnected', 'reconnecting', 'failed'
  const [lastMessage, setLastMessage] = useState(null);
  const [retryCount, setRetryCount] = useState(0);
  const [nextRetryIn, setNextRetryIn] = useState(null);

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const pingIntervalRef = useRef(null);
  const connectionTimeoutRef = useRef(null);
  const listenersRef = useRef({});
  const countdownIntervalRef = useRef(null);

  // 재연결 대기 시간 계산 (지수 백오프)
  const calculateReconnectDelay = useCallback((attempt) => {
    const delay = Math.min(
      RECONNECT_CONFIG.initialDelay * Math.pow(RECONNECT_CONFIG.backoffMultiplier, attempt),
      RECONNECT_CONFIG.maxDelay
    );
    // 약간의 랜덤성 추가 (0.5 ~ 1.5배)
    return Math.floor(delay * (0.5 + Math.random()));
  }, []);

  // 재연결 카운트다운 시작
  const startCountdown = useCallback((delay) => {
    let remaining = Math.ceil(delay / 1000);
    setNextRetryIn(remaining);

    countdownIntervalRef.current = setInterval(() => {
      remaining -= 1;
      if (remaining <= 0) {
        clearInterval(countdownIntervalRef.current);
        countdownIntervalRef.current = null;
        setNextRetryIn(null);
      } else {
        setNextRetryIn(remaining);
      }
    }, 1000);
  }, []);

  // Connect to WebSocket
  const connect = useCallback((isManualReconnect = false) => {
    if (!user || !token) {
      console.log('[WS] No user or token, skipping connection');
      return;
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('[WS] Already connected');
      return;
    }

    // 기존 타이머들 정리
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current);
      countdownIntervalRef.current = null;
    }
    setNextRetryIn(null);

    try {
      setConnectionState(isManualReconnect ? 'reconnecting' : 'connecting');

      const wsUrl = `${WS_BASE_URL}/ws/user/${user.id}?token=${token}`;
      console.log('[WS] Connecting to:', wsUrl.replace(token, 'TOKEN_HIDDEN'));

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      // 연결 타임아웃 설정
      connectionTimeoutRef.current = setTimeout(() => {
        if (ws.readyState !== WebSocket.OPEN) {
          console.warn('[WS] Connection timeout, closing...');
          ws.close();
        }
      }, CONNECTION_TIMEOUT);

      ws.onopen = () => {
        console.log('[WS] ✅ Connected successfully');
        clearTimeout(connectionTimeoutRef.current);
        setIsConnected(true);
        setConnectionState('connected');
        setRetryCount(0); // 성공 시 재시도 카운트 리셋

        // 연결 성공 알림
        if (listenersRef.current['connection_status']) {
          listenersRef.current['connection_status'].forEach(cb =>
            cb({ type: 'connection_status', status: 'connected' })
          );
        }

        // Ping interval 시작
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
          }
        }, PING_INTERVAL);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastMessage(data);

          // Notify listeners
          const eventType = data.type || 'unknown';
          if (listenersRef.current[eventType]) {
            listenersRef.current[eventType].forEach(callback => callback(data));
          }

          // Notify wildcard listeners
          if (listenersRef.current['*']) {
            listenersRef.current['*'].forEach(callback => callback(data));
          }
        } catch (error) {
          if (event.data === 'pong') {
            // Pong received, connection is alive
          } else {
            console.error('[WS] Failed to parse message:', error);
          }
        }
      };

      ws.onerror = (error) => {
        console.error('[WS] ❌ Error:', error);
      };

      ws.onclose = (event) => {
        console.log('[WS] Disconnected:', event.code, event.reason);
        clearTimeout(connectionTimeoutRef.current);
        setIsConnected(false);

        // Clear ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }

        // 연결 끊김 알림
        if (listenersRef.current['connection_status']) {
          listenersRef.current['connection_status'].forEach(cb =>
            cb({ type: 'connection_status', status: 'disconnected', code: event.code })
          );
        }

        // 자동 재연결 시도 (정상 종료가 아닐 경우)
        if (event.code !== 1000 && user && token) {
          const currentRetry = retryCount + 1;

          if (currentRetry <= RECONNECT_CONFIG.maxRetries) {
            const delay = calculateReconnectDelay(currentRetry - 1);
            console.log(`[WS] 🔄 Reconnecting (attempt ${currentRetry}/${RECONNECT_CONFIG.maxRetries}) in ${Math.ceil(delay / 1000)}s...`);

            setConnectionState('reconnecting');
            setRetryCount(currentRetry);
            startCountdown(delay);

            reconnectTimeoutRef.current = setTimeout(() => {
              connect(true);
            }, delay);
          } else {
            console.error('[WS] ❌ Max reconnection attempts reached');
            setConnectionState('failed');

            // 재연결 실패 알림
            if (listenersRef.current['connection_status']) {
              listenersRef.current['connection_status'].forEach(cb =>
                cb({ type: 'connection_status', status: 'failed', message: '연결 재시도 한도 초과' })
              );
            }
          }
        } else {
          setConnectionState('disconnected');
        }
      };
    } catch (error) {
      console.error('[WS] Failed to connect:', error);
      setConnectionState('failed');
    }
  }, [user, token, retryCount, calculateReconnectDelay, startCountdown]);

  // 수동 재연결 (재시도 카운트 리셋)
  const reconnect = useCallback(() => {
    console.log('[WS] 🔄 Manual reconnect requested');
    setRetryCount(0);
    setConnectionState('connecting');

    // 기존 연결 정리
    if (wsRef.current) {
      wsRef.current.close(1000, 'Manual reconnect');
      wsRef.current = null;
    }

    // 약간의 딜레이 후 재연결
    setTimeout(() => {
      connect(true);
    }, 500);
  }, [connect]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    console.log('[WS] Disconnecting...');

    // 모든 타이머 정리
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }

    if (connectionTimeoutRef.current) {
      clearTimeout(connectionTimeoutRef.current);
      connectionTimeoutRef.current = null;
    }

    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current);
      countdownIntervalRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnecting');
      wsRef.current = null;
    }

    setIsConnected(false);
    setConnectionState('disconnected');
    setRetryCount(0);
    setNextRetryIn(null);
  }, []);

  // Send message to server
  const send = useCallback((data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const message = typeof data === 'string' ? data : JSON.stringify(data);
      wsRef.current.send(message);
      return true;
    }
    console.warn('[WS] Cannot send message, not connected');
    return false;
  }, []);

  // Subscribe to specific event type
  const subscribe = useCallback((eventType, callback) => {
    if (!listenersRef.current[eventType]) {
      listenersRef.current[eventType] = [];
    }
    listenersRef.current[eventType].push(callback);

    // Return unsubscribe function
    return () => {
      listenersRef.current[eventType] = listenersRef.current[eventType].filter(
        cb => cb !== callback
      );
    };
  }, []);

  // 이벤트 리스너 추가/제거 (호환성용)
  const addListener = useCallback((eventType, callback) => {
    return subscribe(eventType, callback);
  }, [subscribe]);

  const removeListener = useCallback((eventType, callback) => {
    if (listenersRef.current[eventType]) {
      listenersRef.current[eventType] = listenersRef.current[eventType].filter(
        cb => cb !== callback
      );
    }
  }, []);

  // Connect when user and token are available
  useEffect(() => {
    if (user && token) {
      connect();
    }

    return () => {
      disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, token]);

  // 페이지 가시성 변경 시 재연결 (탭 전환 등)
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && user && token) {
        if (!isConnected && connectionState !== 'connecting' && connectionState !== 'reconnecting') {
          console.log('[WS] Page became visible, checking connection...');
          reconnect();
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [user, token, isConnected, connectionState, reconnect]);

  // 온라인/오프라인 상태 감지
  useEffect(() => {
    const handleOnline = () => {
      console.log('[WS] Network online, attempting reconnect...');
      if (user && token && !isConnected) {
        reconnect();
      }
    };

    const handleOffline = () => {
      console.log('[WS] Network offline');
      setConnectionState('disconnected');
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [user, token, isConnected, reconnect]);

  // Memoize context value to prevent unnecessary re-renders of consumers
  const value = useMemo(() => ({
    isConnected,
    connectionState,
    lastMessage,
    retryCount,
    nextRetryIn,
    maxRetries: RECONNECT_CONFIG.maxRetries,
    send,
    subscribe,
    addListener,
    removeListener,
    connect,
    disconnect,
    reconnect,
  }), [
    isConnected,
    connectionState,
    lastMessage,
    retryCount,
    nextRetryIn,
    send,
    subscribe,
    addListener,
    removeListener,
    connect,
    disconnect,
    reconnect,
  ]);

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocket() {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within WebSocketProvider');
  }
  return context;
}

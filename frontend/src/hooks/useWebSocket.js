import { useEffect, useRef, useState, useCallback } from 'react';

// API URL에서 WebSocket URL 생성 (http -> ws, https -> wss)
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_URL = API_URL.replace(/^http/, 'ws');
const RECONNECT_DELAY = 3000; // 3초
const PING_INTERVAL = 30000; // 30초

export const useWebSocket = (userId) => {
    const [isConnected, setIsConnected] = useState(false);
    const [lastMessage, setLastMessage] = useState(null);
    const wsRef = useRef(null);
    const reconnectTimeoutRef = useRef(null);
    const pingIntervalRef = useRef(null);
    const subscribedChannelsRef = useRef(new Set());

    const connect = useCallback(() => {
        const token = localStorage.getItem('token');
        if (!token || !userId) {
            console.log('[WebSocket] No token or userId, skipping connection');
            return;
        }

        try {
            const ws = new WebSocket(`${WS_URL}/ws/user/${userId}?token=${token}`);

            ws.onopen = () => {
                console.log('[WebSocket] Connected');
                setIsConnected(true);

                // 재구독
                if (subscribedChannelsRef.current.size > 0) {
                    ws.send(JSON.stringify({
                        action: 'subscribe',
                        channels: Array.from(subscribedChannelsRef.current),
                    }));
                }

                // Ping 시작
                pingIntervalRef.current = setInterval(() => {
                    if (ws.readyState === WebSocket.OPEN) {
                        ws.send(JSON.stringify({ action: 'ping' }));
                    }
                }, PING_INTERVAL);
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    setLastMessage(data);
                } catch (error) {
                    console.error('[WebSocket] Failed to parse message:', error);
                }
            };

            ws.onerror = (error) => {
                console.error('[WebSocket] Error:', error);
            };

            ws.onclose = () => {
                console.log('[WebSocket] Disconnected');
                setIsConnected(false);

                // Ping 중지
                if (pingIntervalRef.current) {
                    clearInterval(pingIntervalRef.current);
                    pingIntervalRef.current = null;
                }

                // 자동 재연결
                reconnectTimeoutRef.current = setTimeout(() => {
                    console.log('[WebSocket] Attempting to reconnect...');
                    connect();
                }, RECONNECT_DELAY);
            };

            wsRef.current = ws;
        } catch (error) {
            console.error('[WebSocket] Connection error:', error);
        }
    }, [userId]);

    const disconnect = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
        }

        if (pingIntervalRef.current) {
            clearInterval(pingIntervalRef.current);
            pingIntervalRef.current = null;
        }

        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }

        setIsConnected(false);
    }, []);

    const subscribe = useCallback((channels) => {
        channels.forEach(channel => subscribedChannelsRef.current.add(channel));

        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({
                action: 'subscribe',
                channels: channels,
            }));
        }
    }, []);

    const unsubscribe = useCallback((channels) => {
        channels.forEach(channel => subscribedChannelsRef.current.delete(channel));

        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({
                action: 'unsubscribe',
                channels: channels,
            }));
        }
    }, []);

    const sendMessage = useCallback((message) => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(message));
        }
    }, []);

    useEffect(() => {
        connect();

        return () => {
            disconnect();
        };
    }, [connect, disconnect]);

    return {
        isConnected,
        lastMessage,
        subscribe,
        unsubscribe,
        sendMessage,
        reconnect: connect,
    };
};

export default useWebSocket;

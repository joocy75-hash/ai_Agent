import { useEffect, useRef, useCallback } from 'react';
import { notification } from 'antd';
import {
    RobotOutlined,
    CheckCircleOutlined,
    CloseCircleOutlined,
    SwapOutlined,
    DollarOutlined,
    ExclamationCircleOutlined,
    ThunderboltOutlined,
    ArrowUpOutlined,
    ArrowDownOutlined,
} from '@ant-design/icons';
import { useWebSocket } from '../context/WebSocketContext';

// 알림 설정
const NOTIFICATION_CONFIG = {
    placement: 'topRight',
    duration: 6,
    style: {
        borderRadius: 12,
        boxShadow: '0 8px 24px rgba(0, 0, 0, 0.15)',
    },
};

// 알림 아이콘 컴포넌트
const NotificationIcon = ({ type, side }) => {
    const iconStyle = { fontSize: 24 };

    switch (type) {
        case 'bot_start':
            return <RobotOutlined style={{ ...iconStyle, color: '#52c41a' }} />;
        case 'bot_stop':
            return <RobotOutlined style={{ ...iconStyle, color: '#ff4d4f' }} />;
        case 'position_entry':
            return side === 'long' || side === 'buy'
                ? <ArrowUpOutlined style={{ ...iconStyle, color: '#52c41a' }} />
                : <ArrowDownOutlined style={{ ...iconStyle, color: '#ff4d4f' }} />;
        case 'order_filled':
            return <CheckCircleOutlined style={{ ...iconStyle, color: '#1890ff' }} />;
        case 'position_closed':
            return <SwapOutlined style={{ ...iconStyle, color: '#722ed1' }} />;
        case 'take_profit':
            return <DollarOutlined style={{ ...iconStyle, color: '#52c41a' }} />;
        case 'stop_loss':
            return <CloseCircleOutlined style={{ ...iconStyle, color: '#ff4d4f' }} />;
        case 'error':
            return <ExclamationCircleOutlined style={{ ...iconStyle, color: '#ff4d4f' }} />;
        default:
            return <ThunderboltOutlined style={{ ...iconStyle, color: '#1890ff' }} />;
    }
};

// 트레이딩 알림 컴포넌트
export default function TradingNotification() {
    const { subscribe, isConnected } = useWebSocket();
    const [api, contextHolder] = notification.useNotification();
    const notificationKeyRef = useRef(0);

    // 알림 표시 함수
    const showNotification = useCallback((type, title, description, extra = {}) => {
        const key = `notification_${notificationKeyRef.current++}`;

        api.open({
            key,
            message: (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <NotificationIcon type={type} side={extra.side} />
                    <span style={{ fontWeight: 600, fontSize: 15 }}>{title}</span>
                </div>
            ),
            description: (
                <div style={{ marginTop: 8 }}>
                    {description}
                    {extra.details && (
                        <div style={{
                            marginTop: 8,
                            padding: '8px 12px',
                            background: '#f5f5f7',
                            borderRadius: 8,
                            fontSize: 13
                        }}>
                            {Object.entries(extra.details).map(([k, value]) => (
                                <div key={k} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                                    <span style={{ color: '#666' }}>{k}:</span>
                                    <span style={{ fontWeight: 500 }}>{value}</span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            ),
            ...NOTIFICATION_CONFIG,
            ...extra.config,
        });
    }, [api]);

    // 봇 상태 변경 핸들러
    const handleBotStatusChange = useCallback((data) => {
        if (data.is_running) {
            showNotification(
                'bot_start',
                '🤖 AI 자동매매 시작',
                'AI 트레이딩 봇이 활성화되었습니다.',
                {
                    details: {
                        '전략': data.strategy_name || data.strategy || '기본 전략',
                        '시작 시간': new Date().toLocaleTimeString('ko-KR'),
                    },
                    config: { duration: 8 }
                }
            );
        } else {
            showNotification(
                'bot_stop',
                '🛑 AI 자동매매 중지',
                'AI 트레이딩 봇이 비활성화되었습니다.',
                {
                    config: { duration: 6 }
                }
            );
        }
    }, [showNotification]);

    // CustomEvent 리스너 (Trading.jsx에서 발생시키는 이벤트)
    useEffect(() => {
        const handleCustomBotStatus = (event) => {
            handleBotStatusChange(event.detail);
        };

        window.addEventListener('botStatusChange', handleCustomBotStatus);
        return () => {
            window.removeEventListener('botStatusChange', handleCustomBotStatus);
        };
    }, [handleBotStatusChange]);

    // WebSocket 이벤트 구독
    useEffect(() => {
        if (!isConnected) return;

        // 봇 상태 변경 이벤트 (WebSocket)
        const unsubBot = subscribe('bot_status', handleBotStatusChange);

        // 포지션 진입 이벤트
        const unsubPosition = subscribe('position_entry', (data) => {
            const isLong = data.side?.toLowerCase() === 'long' || data.side?.toLowerCase() === 'buy';
            showNotification(
                'position_entry',
                `📈 포지션 진입 - ${isLong ? 'LONG' : 'SHORT'}`,
                `${data.symbol?.replace('USDT', '/USDT')} 포지션이 열렸습니다.`,
                {
                    side: data.side,
                    details: {
                        '심볼': data.symbol?.replace('USDT', ''),
                        '방향': isLong ? 'Long (매수)' : 'Short (매도)',
                        '진입가': `$${parseFloat(data.entry_price || data.price || 0).toLocaleString()}`,
                        '수량': data.size || data.qty || '-',
                        '레버리지': data.leverage ? `${data.leverage}x` : '-',
                    },
                    config: { duration: 8 }
                }
            );
        });

        // 주문 체결 이벤트
        const unsubOrder = subscribe('order_filled', (data) => {
            showNotification(
                'order_filled',
                '✅ 주문 체결',
                `${data.symbol?.replace('USDT', '/USDT')} 주문이 체결되었습니다.`,
                {
                    details: {
                        '심볼': data.symbol?.replace('USDT', ''),
                        '유형': data.side?.toUpperCase() || '-',
                        '체결가': `$${parseFloat(data.price || data.fill_price || 0).toLocaleString()}`,
                        '수량': data.qty || data.filled_qty || '-',
                    },
                    config: { duration: 6 }
                }
            );
        });

        // 포지션 청산 이벤트
        const unsubClose = subscribe('position_closed', (data) => {
            const pnl = parseFloat(data.pnl || data.realized_pnl || 0);
            const pnlPercent = parseFloat(data.pnl_percent || 0);
            const isProfit = pnl >= 0;

            showNotification(
                isProfit ? 'take_profit' : 'stop_loss',
                isProfit ? '💰 포지션 청산 - 수익' : '📉 포지션 청산 - 손실',
                `${data.symbol?.replace('USDT', '/USDT')} 포지션이 청산되었습니다.`,
                {
                    details: {
                        '심볼': data.symbol?.replace('USDT', ''),
                        '청산 사유': data.exit_reason || data.reason || '수동 청산',
                        '실현 손익': (
                            <span style={{ color: isProfit ? '#52c41a' : '#ff4d4f', fontWeight: 600 }}>
                                {isProfit ? '+' : ''}{pnl.toFixed(2)} USDT
                            </span>
                        ),
                        '수익률': (
                            <span style={{ color: isProfit ? '#52c41a' : '#ff4d4f' }}>
                                {isProfit ? '+' : ''}{pnlPercent.toFixed(2)}%
                            </span>
                        ),
                    },
                    config: { duration: 10 }
                }
            );
        });

        // 트레이드 시그널 이벤트
        const unsubSignal = subscribe('trade_signal', (data) => {
            const isLong = data.signal?.toLowerCase() === 'buy' || data.signal?.toLowerCase() === 'long';
            showNotification(
                'position_entry',
                `⚡ 트레이드 시그널`,
                `${data.symbol?.replace('USDT', '/USDT')} ${isLong ? '매수' : '매도'} 시그널 감지`,
                {
                    side: isLong ? 'long' : 'short',
                    details: {
                        '심볼': data.symbol?.replace('USDT', ''),
                        '시그널': isLong ? 'BUY (매수)' : 'SELL (매도)',
                        '현재가': `$${parseFloat(data.price || 0).toLocaleString()}`,
                        '신뢰도': data.confidence ? `${(data.confidence * 100).toFixed(0)}%` : '-',
                    },
                    config: { duration: 6 }
                }
            );
        });

        // 에러 이벤트
        const unsubError = subscribe('trading_error', (data) => {
            showNotification(
                'error',
                '⚠️ 거래 오류',
                data.message || '거래 중 오류가 발생했습니다.',
                {
                    config: {
                        duration: 10,
                        style: { ...NOTIFICATION_CONFIG.style, borderLeft: '4px solid #ff4d4f' }
                    }
                }
            );
        });

        // 청산 알림 (레거시 호환)
        const unsubLiquidation = subscribe('position_update', (data) => {
            // 포지션이 0이 되었을 때 (청산)
            if (data.data && (data.data.contracts === 0 || data.data.size === 0)) {
                const pnl = parseFloat(data.data.unrealizedPnl || 0);
                const isProfit = pnl >= 0;

                showNotification(
                    isProfit ? 'take_profit' : 'stop_loss',
                    '🔔 포지션 변경',
                    `${data.data.symbol?.replace('USDT', '/USDT')} 포지션이 청산되었습니다.`,
                    {
                        config: { duration: 6 }
                    }
                );
            }
        });

        // Cleanup
        return () => {
            unsubBot();
            unsubPosition();
            unsubOrder();
            unsubClose();
            unsubSignal();
            unsubError();
            unsubLiquidation();
        };
    }, [isConnected, subscribe, showNotification, handleBotStatusChange]);

    return <>{contextHolder}</>;
}


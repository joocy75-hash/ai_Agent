/**
 * GridBotCard Component
 *
 * 그리드 봇 전용 카드 - 미니 그리드 시각화와 실시간 통계 표시
 * 라이트 테마 버전
 *
 * 특징:
 * - 민트/청록색 그라디언트 테마 유지
 * - 라이트 배경
 * - 실시간 수익 카운터
 * - 활성 주문 표시
 */

import { useState, useEffect } from 'react';
import {
    Card,
    Button,
    Space,
    Tag,
    Typography,
    Tooltip,
    Popconfirm,
    message,
    Progress,
    Spin,
} from 'antd';
import {
    PlayCircleOutlined,
    PauseCircleOutlined,
    EditOutlined,
    DeleteOutlined,
    LineChartOutlined,
    EyeOutlined,
} from '@ant-design/icons';

import GridVisualizer from './GridVisualizer';
import { useWebSocket } from '../../context/WebSocketContext';

const { Text } = Typography;

export default function GridBotCard({
    bot,
    onStart,
    onStop,
    onEdit,
    onDelete,
    onViewDetail,
    loading = false,
}) {
    const [actionLoading, setActionLoading] = useState(false);
    const [animatedProfit, setAnimatedProfit] = useState(0);
    const [gridOrders, setGridOrders] = useState(bot.grid_orders || []);
    const [realizedProfit, setRealizedProfit] = useState(0);
    const [livePrice, setLivePrice] = useState(null);

    const { subscribe, send, isConnected } = useWebSocket();

    const isRunning = bot.is_running;
    const gridConfig = bot.grid_config || {};

    // WebSocket grid_order + price 채널 구독
    useEffect(() => {
        if (!isConnected) return;

        // grid_order 및 price 채널 구독 요청
        send({
            action: 'subscribe',
            channels: ['grid_order', 'price'],
        });

        // grid_order_update 이벤트 리스너
        const unsubscribeOrder = subscribe('grid_order_update', (data) => {
            // 해당 봇의 업데이트만 처리
            if (data.data?.bot_id !== bot.id) return;

            const orderData = data.data;

            // 그리드 주문 상태 업데이트
            setGridOrders((prev) => {
                const updated = [...prev];
                const idx = updated.findIndex((o) => o.grid_index === orderData.grid_index);
                if (idx >= 0) {
                    updated[idx] = {
                        ...updated[idx],
                        status: orderData.status,
                        filled_price: orderData.filled_price,
                        profit: orderData.profit,
                    };
                }
                return updated;
            });

            // 체결 알림 표시
            if (orderData.status === 'buy_filled') {
                message.success({
                    content: `${bot.name} 그리드 #${orderData.grid_index + 1} 매수 체결`,
                    duration: 3,
                });
            }
        });

        // grid_cycle_complete 이벤트 리스너 (매도 체결 = 사이클 완료)
        const unsubscribeCycle = subscribe('grid_cycle_complete', (data) => {
            if (data.data?.bot_id !== bot.id) return;

            const cycleData = data.data;

            // 실현 수익 누적
            if (cycleData.profit) {
                setRealizedProfit((prev) => prev + cycleData.profit);
            }

            // 사이클 완료 알림
            message.success({
                content: `${bot.name} 사이클 완료! +$${cycleData.profit?.toFixed(4) || 0}`,
                duration: 4,
            });
        });

        // price_update 이벤트 리스너 (현재가 실시간 업데이트)
        const unsubscribePrice = subscribe('price_update', (data) => {
            // 해당 봇의 심볼과 일치하는 가격만 업데이트
            if (data.symbol === bot.symbol && data.price) {
                setLivePrice(parseFloat(data.price));
            }
        });

        return () => {
            unsubscribeOrder();
            unsubscribeCycle();
            unsubscribePrice();
        };
    }, [bot.id, bot.name, bot.symbol, isConnected, send, subscribe]);

    // props에서 받은 grid_orders로 초기화 동기화
    useEffect(() => {
        if (bot.grid_orders?.length > 0) {
            setGridOrders(bot.grid_orders);
        }
    }, [bot.grid_orders]);

    // 수익 애니메이션 효과 (WebSocket 실시간 수익 + 기존 수익)
    useEffect(() => {
        const targetProfit = (gridConfig.realized_profit || 0) + realizedProfit;
        const duration = 1000;
        const steps = 30;
        const increment = (targetProfit - animatedProfit) / steps;

        if (Math.abs(targetProfit - animatedProfit) < 0.01) return;

        let step = 0;
        const timer = setInterval(() => {
            step++;
            setAnimatedProfit((prev) => {
                const next = prev + increment;
                return step >= steps ? targetProfit : next;
            });
            if (step >= steps) clearInterval(timer);
        }, duration / steps);

        return () => clearInterval(timer);
    }, [gridConfig.realized_profit]);

    // PNL 포맷팅
    const formatPnl = (value) => {
        if (!value || value === 0) return '$0.00';
        const formatted = Math.abs(value).toFixed(2);
        return value >= 0 ? `+$${formatted}` : `-$${formatted}`;
    };

    // 가격 포맷
    const formatPrice = (price) => {
        if (!price) return '-';
        if (price >= 1000) return `$${(price / 1000).toFixed(1)}K`;
        return `$${price.toFixed(2)}`;
    };

    // 시작/중지 핸들러
    const handleToggle = async () => {
        setActionLoading(true);
        try {
            if (isRunning) {
                await onStop?.(bot.id);
            } else {
                await onStart?.(bot.id);
            }
        } catch (err) {
            message.error(err.message || '작업 실패');
        } finally {
            setActionLoading(false);
        }
    };

    // 삭제 핸들러
    const handleDelete = async () => {
        setActionLoading(true);
        try {
            await onDelete?.(bot.id);
            message.success(`봇 "${bot.name}" 삭제됨`);
        } catch (err) {
            message.error(err.message || '삭제 실패');
        } finally {
            setActionLoading(false);
        }
    };

    // 그리드 진행률 계산
    const gridProgress =
        gridConfig.grid_count > 0
            ? ((gridConfig.filled_buy_count + gridConfig.filled_sell_count) /
                (gridConfig.grid_count * 2)) *
            100
            : 0;

    return (
        <Card
            style={{
                borderRadius: 16,
                border: isRunning
                    ? '2px solid #34c759'
                    : '1px solid #e5e5ea',
                background: '#ffffff',
                overflow: 'hidden',
                transition: 'all 0.3s ease',
                boxShadow: isRunning
                    ? '0 4px 20px rgba(52, 199, 89, 0.15)'
                    : '0 2px 8px rgba(0, 0, 0, 0.06)',
            }}
            styles={{ body: { padding: 0 } }}
            hoverable
        >
            <Spin spinning={loading || actionLoading}>
                {/* Header - 그리드 봇 배지 & 상태 */}
                <div
                    style={{
                        background: 'linear-gradient(135deg, #00C076 0%, #00A8FF 100%)',
                        padding: '12px 16px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                    }}
                >
                    <Space>
                        <div
                            style={{
                                width: 32,
                                height: 32,
                                borderRadius: 8,
                                background: 'rgba(255,255,255,0.2)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                fontSize: 16,
                                color: '#fff',
                            }}
                        >
                            <LineChartOutlined />
                        </div>
                        <div>
                            <Text style={{ color: '#fff', fontWeight: 600, fontSize: 15 }}>
                                {bot.name}
                            </Text>
                            <div>
                                <Tag
                                    style={{
                                        background: 'rgba(255,255,255,0.2)',
                                        border: 'none',
                                        color: '#fff',
                                        fontSize: 11,
                                        marginTop: 2,
                                    }}
                                >
                                    그리드
                                </Tag>
                            </div>
                        </div>
                    </Space>

                    {/* 상태 표시 */}
                    <div
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 6,
                            padding: '4px 10px',
                            background: isRunning
                                ? 'rgba(255,255,255,0.3)'
                                : 'rgba(255,255,255,0.15)',
                            borderRadius: 20,
                        }}
                    >
                        <div
                            style={{
                                width: 8,
                                height: 8,
                                borderRadius: '50%',
                                background: isRunning ? '#ffffff' : 'rgba(255,255,255,0.5)',
                                boxShadow: isRunning ? '0 0 8px rgba(255,255,255,0.8)' : 'none',
                                animation: isRunning ? 'gridPulse 2s infinite' : 'none',
                            }}
                        />
                        <Text style={{ color: '#fff', fontSize: 12, fontWeight: 500 }}>
                            {isRunning ? '활성' : '대기'}
                        </Text>
                    </div>
                </div>

                {/* Body */}
                <div style={{ padding: 16 }}>
                    {/* 심볼 & 가격 범위 */}
                    <div
                        style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            marginBottom: 12,
                        }}
                    >
                        <Tag
                            style={{
                                background: '#e8f4fd',
                                border: 'none',
                                color: '#0071e3',
                                fontWeight: 600,
                                fontSize: 13,
                            }}
                        >
                            {bot.symbol}
                        </Tag>
                        <Text style={{ color: '#86868b', fontSize: 11 }}>
                            {formatPrice(gridConfig.lower_price)} ~{' '}
                            {formatPrice(gridConfig.upper_price)}
                        </Text>
                    </div>

                    {/* 미니 그리드 시각화 (실시간 WebSocket 업데이트 반영) */}
                    <div style={{ marginBottom: 12 }}>
                        <GridVisualizer
                            lowerPrice={gridConfig.lower_price || 85000}
                            upperPrice={gridConfig.upper_price || 100000}
                            gridCount={gridConfig.grid_count || 10}
                            gridMode={gridConfig.grid_mode}
                            currentPrice={livePrice || gridConfig.current_price || 92500}
                            orders={gridOrders}
                            height={120}
                            compact
                            showLabels={false}
                            lightMode={true}
                        />
                    </div>

                    {/* 통계 그리드 */}
                    <div
                        style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(2, 1fr)',
                            gap: 8,
                            marginBottom: 12,
                        }}
                    >
                        {/* 실현 수익 */}
                        <div
                            style={{
                                background: animatedProfit >= 0
                                    ? 'linear-gradient(135deg, rgba(52, 199, 89, 0.1) 0%, rgba(52, 199, 89, 0.05) 100%)'
                                    : 'linear-gradient(135deg, rgba(255, 59, 48, 0.1) 0%, rgba(255, 59, 48, 0.05) 100%)',
                                borderRadius: 10,
                                padding: 10,
                                textAlign: 'center',
                                border: animatedProfit >= 0
                                    ? '1px solid rgba(52, 199, 89, 0.2)'
                                    : '1px solid rgba(255, 59, 48, 0.2)',
                            }}
                        >
                            <Text
                                style={{
                                    color: '#86868b',
                                    fontSize: 10,
                                    display: 'block',
                                }}
                            >
                                실현 수익
                            </Text>
                            <Text
                                style={{
                                    color: animatedProfit >= 0 ? '#34c759' : '#ff3b30',
                                    fontSize: 16,
                                    fontWeight: 700,
                                    fontFamily: 'SF Mono, Monaco, monospace',
                                }}
                            >
                                {formatPnl(animatedProfit)}
                            </Text>
                        </div>

                        {/* 그리드 개수 */}
                        <div
                            style={{
                                background: '#f5f5f7',
                                borderRadius: 10,
                                padding: 10,
                                textAlign: 'center',
                            }}
                        >
                            <Text
                                style={{
                                    color: '#86868b',
                                    fontSize: 10,
                                    display: 'block',
                                }}
                            >
                                그리드
                            </Text>
                            <Text style={{ color: '#0071e3', fontSize: 16, fontWeight: 700 }}>
                                {gridConfig.grid_count || 0}개
                            </Text>
                        </div>

                        {/* 체결 현황 */}
                        <div
                            style={{
                                background: '#f5f5f7',
                                borderRadius: 10,
                                padding: 10,
                                textAlign: 'center',
                            }}
                        >
                            <Text
                                style={{
                                    color: '#86868b',
                                    fontSize: 10,
                                    display: 'block',
                                }}
                            >
                                매수/매도
                            </Text>
                            <Text style={{ color: '#1d1d1f', fontSize: 14, fontWeight: 600 }}>
                                <span style={{ color: '#34c759' }}>
                                    {gridConfig.filled_buy_count || 0}
                                </span>
                                {' / '}
                                <span style={{ color: '#ff3b30' }}>
                                    {gridConfig.filled_sell_count || 0}
                                </span>
                            </Text>
                        </div>

                        {/* 투자금 */}
                        <div
                            style={{
                                background: '#f5f5f7',
                                borderRadius: 10,
                                padding: 10,
                                textAlign: 'center',
                            }}
                        >
                            <Text
                                style={{
                                    color: '#86868b',
                                    fontSize: 10,
                                    display: 'block',
                                }}
                            >
                                투자금
                            </Text>
                            <Text style={{ color: '#ff9500', fontSize: 14, fontWeight: 600 }}>
                                ${gridConfig.total_investment?.toLocaleString() || 0}
                            </Text>
                        </div>
                    </div>

                    {/* 그리드 진행률 */}
                    <div style={{ marginBottom: 12 }}>
                        <div
                            style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                marginBottom: 4,
                            }}
                        >
                            <Text style={{ color: '#86868b', fontSize: 11 }}>
                                그리드 활성도
                            </Text>
                            <Text style={{ color: '#0071e3', fontSize: 11 }}>
                                {gridProgress.toFixed(0)}%
                            </Text>
                        </div>
                        <Progress
                            percent={gridProgress}
                            showInfo={false}
                            strokeColor={{
                                from: '#34c759',
                                to: '#0071e3',
                            }}
                            trailColor="#e5e5ea"
                            size="small"
                        />
                    </div>

                    {/* 액션 버튼 */}
                    <div style={{ display: 'flex', gap: 8 }}>
                        {/* 시작/중지 토글 버튼 */}
                        <Button
                            type="primary"
                            icon={isRunning ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
                            onClick={handleToggle}
                            loading={actionLoading}
                            style={{
                                flex: 2,
                                height: 40,
                                borderRadius: 8,
                                background: isRunning
                                    ? '#ff3b30'
                                    : 'linear-gradient(135deg, #00C076 0%, #00A8FF 100%)',
                                border: 'none',
                                fontWeight: 600,
                            }}
                        >
                            {isRunning ? 'Stop' : 'Start'}
                        </Button>

                        {/* 상세 보기 버튼 */}
                        <Tooltip title="상세 보기">
                            <Button
                                icon={<EyeOutlined />}
                                onClick={() => onViewDetail?.(bot.id)}
                                style={{
                                    height: 40,
                                    width: 40,
                                    borderRadius: 8,
                                    background: '#f5f5f7',
                                    border: '1px solid #e5e5ea',
                                    color: '#0071e3',
                                }}
                            />
                        </Tooltip>

                        {/* 설정 버튼 */}
                        <Tooltip title="설정 편집">
                            <Button
                                icon={<EditOutlined />}
                                onClick={() => onEdit?.(bot)}
                                disabled={isRunning}
                                style={{
                                    height: 40,
                                    width: 40,
                                    borderRadius: 8,
                                    background: '#f5f5f7',
                                    border: '1px solid #e5e5ea',
                                    color: isRunning ? '#d2d2d7' : '#1d1d1f',
                                }}
                            />
                        </Tooltip>

                        {/* 삭제 버튼 */}
                        <Popconfirm
                            title="그리드 봇 삭제"
                            description={`"${bot.name}" 봇을 삭제하시겠습니까?`}
                            onConfirm={handleDelete}
                            okText="삭제"
                            cancelText="취소"
                            okButtonProps={{ danger: true }}
                        >
                            <Tooltip title="삭제">
                                <Button
                                    icon={<DeleteOutlined />}
                                    danger
                                    style={{
                                        height: 40,
                                        width: 40,
                                        borderRadius: 8,
                                        background: 'rgba(255, 59, 48, 0.08)',
                                        border: '1px solid rgba(255, 59, 48, 0.2)',
                                    }}
                                />
                            </Tooltip>
                        </Popconfirm>
                    </div>
                </div>

                {/* 애니메이션 스타일 */}
                <style>{`
                    @keyframes gridPulse {
                        0%, 100% { opacity: 1; transform: scale(1); }
                        50% { opacity: 0.6; transform: scale(1.2); }
                    }
                `}</style>
            </Spin>
        </Card>
    );
}

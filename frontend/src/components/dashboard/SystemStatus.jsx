import { useEffect, useState } from 'react';
import { Card, Row, Col, Badge, Statistic, Alert, Tooltip, notification } from 'antd';
import {
    CheckCircleOutlined,
    CloseCircleOutlined,
    SyncOutlined,
    DollarOutlined,
    WalletOutlined,
    PercentageOutlined,
    RiseOutlined,
    FallOutlined,
    ClockCircleOutlined,
    WarningOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/ko';
import axios from 'axios';
import useWebSocket from '../../hooks/useWebSocket';

dayjs.extend(relativeTime);
dayjs.locale('ko');

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function SystemStatus() {
    const [data, setData] = useState({
        balance: null,
        botStatus: null,
        unrealizedPnL: null,
        lastUpdate: null,
    });
    const [loading, setLoading] = useState(true);
    const [wsConnected, setWsConnected] = useState(false);

    // WebSocket 연결
    const { isConnected, lastMessage, subscribe, unsubscribe } = useWebSocket(
        localStorage.getItem('userId')
    );

    useEffect(() => {
        // 초기 데이터 로드
        loadData();

        // WebSocket 구독
        subscribe(['balance', 'position', 'alert']);

        return () => {
            unsubscribe(['balance', 'position', 'alert']);
        };
    }, [subscribe, unsubscribe]);

    // WebSocket 메시지 처리
    useEffect(() => {
        if (!lastMessage) return;

        switch (lastMessage.type) {
            case 'balance_update':
                setData(prev => ({
                    ...prev,
                    balance: lastMessage.data,
                    lastUpdate: lastMessage.timestamp,
                }));
                break;

            case 'position_update':
                // 포지션 업데이트 시 미실현 손익 재계산
                loadUnrealizedPnL();
                break;

            case 'alert':
                // 알림 표시
                const { level, message } = lastMessage;
                notification[level.toLowerCase()]({
                    message: `시스템 알림 (${level})`,
                    description: message,
                    placement: 'topRight',
                });
                break;

            default:
                break;
        }
    }, [lastMessage]);

    const loadData = async () => {
        try {
            const token = localStorage.getItem('token');
            if (!token) {
                setLoading(false);
                return;
            }

            const headers = {
                'Authorization': `Bearer ${token}`,
            };

            // 병렬로 API 호출
            const [botStatusRes, unrealizedPnLRes] = await Promise.all([
                axios.get(`${API_BASE_URL}/bot/status`, { headers }),
                axios.get(`${API_BASE_URL}/positions/unrealized-pnl`, { headers }).catch(() => null),
            ]);

            const botStatusData = botStatusRes.data;
            const pnlData = unrealizedPnLRes?.data;

            setData({
                balance: botStatusData.balance,
                botStatus: {
                    status: botStatusData.status,
                    strategyName: botStatusData.strategy?.name,
                    lastSignal: botStatusData.strategy?.lastSignal,
                    lastSignalTime: botStatusData.strategy?.lastSignalTime,
                },
                unrealizedPnL: pnlData ? {
                    amount: pnlData.unrealized_pnl,
                    percent: pnlData.unrealized_pnl_percent,
                    positionCount: pnlData.position_count,
                } : null,
                lastUpdate: botStatusData.connection?.lastDataReceived,
            });

            setWsConnected(botStatusData.connection?.exchange === 'CONNECTED');
            setLoading(false);
        } catch (error) {
            console.error('[SystemStatus] Error loading data:', error);
            setWsConnected(false);
            setLoading(false);
        }
    };

    const loadUnrealizedPnL = async () => {
        try {
            const token = localStorage.getItem('token');
            if (!token) return;

            const headers = { 'Authorization': `Bearer ${token}` };
            const response = await axios.get(`${API_BASE_URL}/positions/unrealized-pnl`, { headers });

            setData(prev => ({
                ...prev,
                unrealizedPnL: {
                    amount: response.data.unrealized_pnl,
                    percent: response.data.unrealized_pnl_percent,
                    positionCount: response.data.position_count,
                },
            }));
        } catch (error) {
            console.error('[SystemStatus] Error loading unrealized P&L:', error);
        }
    };

    const getDataFreshness = () => {
        if (!data.lastUpdate) return { text: '알 수 없음', isStale: true };

        const secondsAgo = Math.floor((Date.now() - new Date(data.lastUpdate).getTime()) / 1000);
        const isStale = secondsAgo > 30;

        return {
            text: dayjs(data.lastUpdate).fromNow(),
            isStale,
            secondsAgo,
        };
    };

    const getBotStatusBadge = () => {
        if (!data.botStatus) return <Badge status="default" text="알 수 없음" />;

        const status = data.botStatus.status?.toUpperCase();
        if (status === 'RUNNING') {
            return <Badge status="processing" text="실행 중" />;
        } else if (status === 'STOPPED') {
            return <Badge status="default" text="중지됨" />;
        } else if (status === 'ERROR') {
            return <Badge status="error" text="오류" />;
        }
        return <Badge status="default" text={status} />;
    };

    const getConnectionBadge = () => {
        const freshness = getDataFreshness();
        const connected = wsConnected && isConnected;

        if (connected && !freshness.isStale) {
            return (
                <Tooltip title={`WebSocket: ${isConnected ? '연결됨' : '끊김'} | 마지막 수신: ${freshness.text}`}>
                    <Badge
                        status="success"
                        text="실시간 연결"
                        icon={<CheckCircleOutlined />}
                    />
                </Tooltip>
            );
        }

        return (
            <Tooltip title={`WebSocket: ${isConnected ? '연결됨' : '끊김'} | 마지막 수신: ${freshness.text}`}>
                <Badge
                    status="error"
                    text="연결 끊김"
                    icon={<CloseCircleOutlined />}
                />
            </Tooltip>
        );
    };

    const getMarginUsage = () => {
        if (!data.balance) return 0;
        const { total, free } = data.balance;
        if (total === 0) return 0;
        return ((total - free) / total) * 100;
    };

    const freshness = getDataFreshness();

    return (
        <>
            {/* 미실현 손익 알림 (가장 상단) */}
            {data.unrealizedPnL && data.unrealizedPnL.positionCount > 0 && (
                <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
                    <Col span={24}>
                        <Alert
                            message={
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <span style={{ fontSize: 16, fontWeight: 'bold' }}>
                                        미실현 손익 (현재 포지션 {data.unrealizedPnL.positionCount}개)
                                        {isConnected && <Badge status="processing" text="실시간" style={{ marginLeft: 8 }} />}
                                    </span>
                                    <span style={{ fontSize: 24, fontWeight: 'bold' }}>
                                        {data.unrealizedPnL.amount >= 0 ? '+' : ''}
                                        ${data.unrealizedPnL.amount.toFixed(2)} USDT
                                        <span style={{ fontSize: 16, marginLeft: 8 }}>
                                            ({data.unrealizedPnL.percent >= 0 ? '+' : ''}
                                            {data.unrealizedPnL.percent.toFixed(2)}%)
                                        </span>
                                    </span>
                                </div>
                            }
                            type={data.unrealizedPnL.amount >= 0 ? 'success' : 'error'}
                            icon={data.unrealizedPnL.amount >= 0 ? <RiseOutlined /> : <FallOutlined />}
                            showIcon
                        />
                    </Col>
                </Row>
            )}

            {/* 기존 시스템 상태 카드들 */}
            <Row gutter={[16, 16]}>
                {/* 시스템 상태 카드 */}
                <Col xs={24} sm={12} lg={6}>
                    <Card
                        loading={loading}
                        style={{
                            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                            color: 'white',
                        }}
                    >
                        <div style={{ marginBottom: 12 }}>
                            <SyncOutlined style={{ fontSize: 24, marginRight: 8 }} />
                            <span style={{ fontSize: 16, fontWeight: 'bold' }}>시스템 상태</span>
                        </div>

                        <div style={{ marginBottom: 8 }}>
                            <div style={{ fontSize: 12, opacity: 0.9 }}>봇 상태</div>
                            <div style={{ fontSize: 16, fontWeight: 'bold', marginTop: 4 }}>
                                {getBotStatusBadge()}
                            </div>
                        </div>

                        {data.botStatus?.strategyName && (
                            <div style={{ marginBottom: 8 }}>
                                <div style={{ fontSize: 12, opacity: 0.9 }}>실행 전략</div>
                                <div style={{ fontSize: 14, fontWeight: 'bold', marginTop: 4 }}>
                                    {data.botStatus.strategyName}
                                </div>
                            </div>
                        )}

                        <div>
                            <div style={{ fontSize: 12, opacity: 0.9 }}>연결 상태</div>
                            <div style={{ fontSize: 16, fontWeight: 'bold', marginTop: 4 }}>
                                {getConnectionBadge()}
                            </div>
                        </div>
                    </Card>
                </Col>

                {/* 총 자산 카드 */}
                <Col xs={24} sm={12} lg={6}>
                    <Card
                        loading={loading}
                        style={{
                            background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                            color: 'white',
                        }}
                    >
                        <Statistic
                            title={
                                <span style={{ color: 'rgba(255,255,255,0.9)' }}>
                                    총 자산
                                    {isConnected && <Badge status="processing" style={{ marginLeft: 8 }} />}
                                </span>
                            }
                            value={data.balance?.total || 0}
                            precision={2}
                            prefix={<DollarOutlined />}
                            suffix="USDT"
                            valueStyle={{ color: 'white', fontSize: 24 }}
                        />
                        <div style={{ marginTop: 8, fontSize: 11, opacity: 0.8, display: 'flex', alignItems: 'center', gap: 4 }}>
                            <ClockCircleOutlined />
                            <span>업데이트: {freshness.text}</span>
                            {freshness.isStale && (
                                <Tooltip title="데이터가 30초 이상 오래되었습니다">
                                    <WarningOutlined style={{ color: '#faad14' }} />
                                </Tooltip>
                            )}
                        </div>
                    </Card>
                </Col>

                {/* 사용 가능 잔고 카드 */}
                <Col xs={24} sm={12} lg={6}>
                    <Card
                        loading={loading}
                        style={{
                            background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
                            color: 'white',
                        }}
                    >
                        <Statistic
                            title={<span style={{ color: 'rgba(255,255,255,0.9)' }}>사용 가능 잔고</span>}
                            value={data.balance?.free || 0}
                            precision={2}
                            prefix={<WalletOutlined />}
                            suffix="USDT"
                            valueStyle={{ color: 'white', fontSize: 24 }}
                        />
                        <div style={{ marginTop: 8, fontSize: 11, opacity: 0.8 }}>
                            사용 중: ${((data.balance?.total || 0) - (data.balance?.free || 0)).toFixed(2)} USDT
                        </div>
                    </Card>
                </Col>

                {/* 증거금 사용률 카드 */}
                <Col xs={24} sm={12} lg={6}>
                    <Card
                        loading={loading}
                        style={{
                            background: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
                            color: 'white',
                        }}
                    >
                        <Statistic
                            title={<span style={{ color: 'rgba(255,255,255,0.9)' }}>증거금 사용률</span>}
                            value={getMarginUsage()}
                            precision={1}
                            prefix={<PercentageOutlined />}
                            suffix="%"
                            valueStyle={{
                                color: 'white',
                                fontSize: 24,
                            }}
                        />
                        <div style={{ marginTop: 8, fontSize: 12, opacity: 0.9, fontWeight: 'bold' }}>
                            {getMarginUsage() > 80 ? '⚠️ 위험' : getMarginUsage() > 50 ? '⚠️ 주의' : '✅ 안전'}
                        </div>
                    </Card>
                </Col>
            </Row>
        </>
    );
}

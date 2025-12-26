import { useState, useEffect } from 'react';
import { Row, Col, Card, Typography, Select, Button, message, Badge, Space, Tag, Divider } from 'antd';
import {
    LineChartOutlined,
    ControlOutlined,
    ReloadOutlined,
    PlayCircleOutlined,
    PauseCircleOutlined,
    InfoCircleOutlined,
    BookOutlined,
} from '@ant-design/icons';
import { botAPI } from '../api/bot';
import { useAuth } from '../context/AuthContext';
import { useWebSocket } from '../context/WebSocketContext';
import { useStrategies } from '../context/StrategyContext';
import TradingViewWidget from '../components/TradingViewWidget';
import BalanceCard from '../components/BalanceCard';
import PositionList from '../components/PositionList';
import BotLogViewer from '../components/BotLogViewer';

const { Title, Text } = Typography;
const { Option } = Select;

export default function Trading() {
    const { user } = useAuth();
    const { isConnected, subscribe } = useWebSocket();
    const { strategies: allStrategies, loading: strategiesLoading, lastUpdated } = useStrategies();

    // 화면 크기 감지
    const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

    useEffect(() => {
        const handleResize = () => setIsMobile(window.innerWidth < 768);
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    // Chart State - TradingView 위젯 사용으로 단순화
    const [symbol, setSymbol] = useState('BTCUSDT');
    const symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT'];

    // Bot State
    const [botStatus, setBotStatus] = useState(null);
    const [selectedStrategy, setSelectedStrategy] = useState('');
    const [botLoading, setBotLoading] = useState(false);
    const [showStartConfirm, setShowStartConfirm] = useState(false);
    const [showStopConfirm, setShowStopConfirm] = useState(false);

    // Load Bot Data (전략 목록은 StrategyContext에서 전역 관리)
    const loadBotData = async () => {
        setBotLoading(true);
        try {
            const statusData = await botAPI.getBotStatus();
            setBotStatus(statusData);

            if (statusData.strategy_id) {
                setSelectedStrategy(statusData.strategy_id.toString());
            }
        } catch (err) {
            console.error('[Trading] Bot data load error:', err);
        } finally {
            setBotLoading(false);
        }
    };

    // 전역 전략 상태에서 모든 전략 가져오기 (사용자가 선택할 수 있도록)
    const strategies = allStrategies;

    // Initial Load - Bot 데이터만 로드 (차트는 TradingView 위젯이 자동 처리)
    useEffect(() => {
        loadBotData();
    }, []);

    // 전역 전략 상태가 변경되면 선택된 전략 유효성 검사
    useEffect(() => {
        if (selectedStrategy && strategies.length > 0) {
            const strategyExists = strategies.some(s => s.id === parseInt(selectedStrategy));
            if (!strategyExists) {
                console.log(`[Trading] Selected strategy ${selectedStrategy} no longer available, clearing selection`);
                setSelectedStrategy('');
            }
        }
        console.log(`[Trading] Strategy list updated: ${strategies.length} active strategies available`);
    }, [lastUpdated, strategies, selectedStrategy]);

    // WebSocket for price alerts
    useEffect(() => {
        if (!isConnected) return;

        const unsubscribe = subscribe('price_alert_triggered', (data) => {
            console.log('[Trading] Price alert triggered:', data);
            const alertData = data.data;
            const direction = alertData.direction === 'up' ? '상향 돌파' : '하향 돌파';

            // 알림 표시
            message.info({
                content: (
                    <span>
                        🔔 <strong>{alertData.label || '가격 알림'}</strong><br />
                        {alertData.symbol} {direction}<br />
                        설정가: ${Number(alertData.alert_price).toLocaleString()}<br />
                        현재가: ${Number(alertData.current_price).toLocaleString()}
                    </span>
                ),
                duration: 8,
                style: { marginTop: '20vh' },
            });
        });

        return () => unsubscribe();
    }, [isConnected, subscribe]);

    // Bot Controls
    const handleStartBot = async () => {
        if (!selectedStrategy) {
            message.warning('전략을 선택해주세요');
            return;
        }

        setBotLoading(true);
        try {
            const result = await botAPI.startBot(parseInt(selectedStrategy));
            setBotStatus(result);

            // WebSocket으로 봇 상태 변경 알림 전송
            if (isConnected) {
                // 직접 이벤트 트리거 (알림 표시용)
                window.dispatchEvent(new CustomEvent('botStatusChange', {
                    detail: {
                        is_running: true,
                        strategy_name: selectedStrategyObj?.name,
                        strategy: selectedStrategyObj?.name
                    }
                }));
            }

            message.success('봇이 시작되었습니다!');
            setShowStartConfirm(false);
        } catch (err) {
            message.error(err.response?.data?.detail || '봇 시작 실패');
        } finally {
            setBotLoading(false);
        }
    };

    const handleStopBot = async () => {
        setBotLoading(true);
        try {
            const result = await botAPI.stopBot();
            setBotStatus(result);

            // WebSocket으로 봇 상태 변경 알림 전송
            if (isConnected) {
                window.dispatchEvent(new CustomEvent('botStatusChange', {
                    detail: { is_running: false }
                }));
            }

            message.success('봇이 중지되었습니다');
            setShowStopConfirm(false);
        } catch (err) {
            message.error(err.response?.data?.detail || '봇 중지 실패');
        } finally {
            setBotLoading(false);
        }
    };

    const isRunning = botStatus?.is_running || false;
    const selectedStrategyObj = strategies.find(s => s.id === parseInt(selectedStrategy));

    // 환율 (실시간 API 연동 가능, 현재는 고정 환율 사용)
    const USD_KRW_RATE = 1460; // 1 USD = 1,460 KRW

    const formatPrice = (price) => {
        if (!price) return '0';
        return Math.round(price).toLocaleString('en-US');
    };

    const formatKRW = (usdPrice) => {
        if (!usdPrice) return '₩0';
        const krwPrice = usdPrice * USD_KRW_RATE;
        return '₩' + Math.round(krwPrice).toLocaleString('ko-KR');
    };

    return (
        <div style={{ maxWidth: 1400, margin: '0 auto' }}>
            {/* Page Header */}
            <div style={{ marginBottom: isMobile ? 16 : 24 }}>
                <Title level={isMobile ? 3 : 2} style={{ marginBottom: 4 }}>
                    <LineChartOutlined style={{ marginRight: 8 }} />
                    트레이딩
                </Title>
                {!isMobile && <Text type="secondary">차트 분석 및 봇 제어를 한 곳에서 관리하세요</Text>}
            </div>
            {/* Balance Card - Top */}
            <BalanceCard style={{ marginBottom: isMobile ? 12 : 20 }} />

            {/* Main Layout: Chart (Left) + Bot Control (Right) */}
            <Row gutter={isMobile ? [8, 8] : [20, 20]}>
                {/* Left Column - Chart */}
                <Col xs={24} lg={17}>
                    {/* TradingView Chart Card */}
                    <Card
                        style={{ marginBottom: isMobile ? 12 : 20 }}
                        styles={{ body: { padding: 0 } }}
                    >
                        {/* TradingView Widget - 외부 실시간 차트 */}
                        <TradingViewWidget
                            symbol={symbol}
                            height={isMobile ? 350 : 500}
                            availableSymbols={symbols}
                            onSymbolChange={setSymbol}
                        />
                    </Card>

                    {/* Position List */}
                    <PositionList currentPrices={{}} />
                </Col>

                {/* Right Column - Bot Control */}
                <Col xs={24} lg={7}>
                    {/* Bot Control Panel */}
                    <Card
                        style={{ marginBottom: 20 }}
                        title={
                            <Space>
                                <ControlOutlined />
                                <span style={{ fontWeight: 600 }}>AI BOT Trading</span>
                            </Space>
                        }
                        extra={
                            <Badge
                                status={isRunning ? 'processing' : 'default'}
                                text={isRunning ? '실행 중' : '중지됨'}
                            />
                        }
                    >
                        <Space direction="vertical" style={{ width: '100%' }} size="middle">
                            {/* Bot Status with Inline Logs */}
                            <div style={{
                                padding: isRunning ? '12px 16px 0 16px' : '12px 16px',
                                background: isRunning
                                    ? 'linear-gradient(135deg, #f6ffed 0%, #d9f7be 100%)'
                                    : '#f5f5f7',
                                borderRadius: 8,
                                border: isRunning ? '1px solid #b7eb8f' : '1px solid #e5e5e5'
                            }}>
                                {/* Header with status indicator */}
                                <div style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'space-between',
                                    marginBottom: isRunning ? 12 : 0
                                }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                                        <div style={{
                                            width: 32,
                                            height: 32,
                                            borderRadius: '50%',
                                            background: isRunning ? '#52c41a' : '#d9d9d9',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            boxShadow: isRunning ? '0 0 12px rgba(82, 196, 26, 0.4)' : 'none'
                                        }}>
                                            {isRunning ? (
                                                <PauseCircleOutlined style={{ fontSize: 16, color: '#fff' }} />
                                            ) : (
                                                <PlayCircleOutlined style={{ fontSize: 16, color: '#fff' }} />
                                            )}
                                        </div>
                                        <Text strong style={{ fontSize: 14, color: isRunning ? '#389e0d' : '#8c8c8c' }}>
                                            {isRunning ? 'AI Bot 실행 중' : 'AI Bot 대기 중'}
                                        </Text>
                                    </div>
                                </div>

                                {/* Inline Real-time Logs - Only when running */}
                                {isRunning && (
                                    <BotLogViewer
                                        height={200}
                                        maxLogs={50}
                                        compact={true}
                                        showHeader={false}
                                    />
                                )}
                            </div>

                            {/* Strategy Selection */}
                            <div>
                                <Text strong style={{ display: 'block', marginBottom: 8 }}>전략 선택</Text>
                                <Select
                                    style={{ width: '100%' }}
                                    placeholder="전략을 선택하세요"
                                    value={selectedStrategy || undefined}
                                    onChange={setSelectedStrategy}
                                    disabled={isRunning}
                                >
                                    {strategies.map(strategy => (
                                        <Option key={strategy.id} value={strategy.id.toString()}>
                                            {strategy.name}
                                        </Option>
                                    ))}
                                </Select>
                            </div>

                            {/* Selected Strategy Info */}
                            {selectedStrategyObj && (
                                <div style={{ background: '#f0f5ff', padding: 12, borderRadius: 8 }}>
                                    <Text strong style={{ display: 'block', marginBottom: 8 }}>선택된 전략</Text>
                                    <Space wrap size={[4, 4]}>
                                        <Tag color="blue" style={{ margin: 0 }}>{selectedStrategyObj.type}</Tag>
                                        <Tag color="purple" style={{ margin: 0 }}>{selectedStrategyObj.symbol}</Tag>
                                        <Tag color="cyan" style={{ margin: 0 }}>{selectedStrategyObj.timeframe}</Tag>
                                    </Space>
                                </div>
                            )}

                            <Divider style={{ margin: '12px 0' }} />

                            {/* Start/Stop Toggle Button */}
                            {isRunning ? (
                                <Button
                                    danger
                                    size="large"
                                    block
                                    icon={<PauseCircleOutlined />}
                                    onClick={() => setShowStopConfirm(true)}
                                    loading={botLoading}
                                    style={{
                                        height: 52,
                                        fontSize: 16,
                                        fontWeight: 600,
                                        borderRadius: 10
                                    }}
                                >
                                    Stop
                                </Button>
                            ) : (
                                <Button
                                    type="primary"
                                    size="large"
                                    block
                                    icon={<PlayCircleOutlined />}
                                    onClick={() => setShowStartConfirm(true)}
                                    disabled={botLoading || !selectedStrategy}
                                    style={{
                                        height: 52,
                                        fontSize: 16,
                                        fontWeight: 600,
                                        borderRadius: 10,
                                        background: !selectedStrategy ? '#d9d9d9' : 'linear-gradient(135deg, #52c41a 0%, #389e0d 100%)',
                                        borderColor: !selectedStrategy ? '#d9d9d9' : '#52c41a'
                                    }}
                                >
                                    Start
                                </Button>
                            )}

                            <Button
                                block
                                icon={<ReloadOutlined />}
                                onClick={loadBotData}
                                loading={botLoading}
                                style={{ borderRadius: 8 }}
                            >
                                새로고침
                            </Button>
                        </Space>
                    </Card>

                    {/* Strategy Description Card */}
                    {selectedStrategyObj && (
                        <Card
                            style={{ marginTop: 20 }}
                            title={
                                <Space>
                                    <BookOutlined />
                                    <span>전략 설명서</span>
                                </Space>
                            }
                            size="small"
                        >
                            <div style={{ marginBottom: 16 }}>
                                <Text strong style={{ fontSize: 16, color: '#1890ff' }}>
                                    {selectedStrategyObj.name}
                                </Text>
                            </div>

                            {/* Strategy Info */}
                            <div style={{ marginBottom: 12 }}>
                                <Space wrap size={[4, 4]}>
                                    <Tag color="blue" style={{ margin: 0 }}>{selectedStrategyObj.type || 'AI'}</Tag>
                                    <Tag color="purple" style={{ margin: 0 }}>{selectedStrategyObj.symbol}</Tag>
                                    <Tag color="cyan" style={{ margin: 0 }}>{selectedStrategyObj.timeframe}</Tag>
                                    {selectedStrategyObj.leverage && (
                                        <Tag color="orange" style={{ margin: 0 }}>x{selectedStrategyObj.leverage}</Tag>
                                    )}
                                </Space>
                            </div>

                            {/* Description */}
                            <div style={{
                                background: '#f8f9fa',
                                padding: '16px',
                                borderRadius: 12,
                                marginBottom: 16,
                                border: '1px solid #e8e8e8'
                            }}>
                                <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
                                    <InfoCircleOutlined style={{ marginRight: 8, color: '#1890ff' }} />
                                    <Text strong style={{ color: '#1890ff' }}>전략 상세 설명</Text>
                                </div>
                                <div style={{
                                    color: '#4a4a4a',
                                    whiteSpace: 'pre-wrap',
                                    lineHeight: '1.6',
                                    fontSize: '14px'
                                }}>
                                    {selectedStrategyObj.description || '이 전략은 AI 기반 자동 매매 전략입니다. 설정된 조건에 따라 자동으로 포지션을 진입/청산합니다.'}
                                </div>
                            </div>

                            {/* Parameters */}


                            {/* Risk Level */}
                            <div style={{ marginTop: 12 }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <Text type="secondary">위험도</Text>
                                    <Tag color={
                                        selectedStrategyObj.risk_level?.includes('high') ? 'red' :
                                            selectedStrategyObj.risk_level?.includes('medium') ? 'orange' : 'green'
                                    }>
                                        {selectedStrategyObj.risk_level?.includes('high') ? '고위험' :
                                            selectedStrategyObj.risk_level?.includes('medium') ? '중위험' : '저위험'}
                                    </Tag>
                                </div>
                            </div>

                            {/* 손절/익절 정보 */}
                            {(selectedStrategyObj.stop_loss || selectedStrategyObj.take_profit) && (
                                <div style={{ marginTop: 8 }}>
                                    <Space size="large">
                                        {selectedStrategyObj.stop_loss && (
                                            <Text type="secondary">
                                                손절: <Text strong style={{ color: '#ff4d4f' }}>-{selectedStrategyObj.stop_loss}%</Text>
                                            </Text>
                                        )}
                                        {selectedStrategyObj.take_profit && (
                                            <Text type="secondary">
                                                익절: <Text strong style={{ color: '#52c41a' }}>+{selectedStrategyObj.take_profit}%</Text>
                                            </Text>
                                        )}
                                    </Space>
                                </div>
                            )}

                            {/* Warning */}
                            <div style={{
                                marginTop: 12,
                                padding: 8,
                                background: '#fff7e6',
                                borderRadius: 4,
                                border: '1px solid #ffd591'
                            }}>
                                <Text style={{ fontSize: 12, color: '#ad6800' }}>
                                    ⚠️ 자동 거래는 실제 자금이 사용됩니다. 신중히 진행하세요.
                                </Text>
                            </div>
                        </Card>
                    )}
                </Col>
            </Row>

            {/* Start Bot Confirmation Modal */}
            {showStartConfirm && (
                <div style={{
                    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                    background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center',
                    justifyContent: 'center', zIndex: 1000
                }}>
                    <Card style={{ maxWidth: 500, width: '90%' }}>
                        <Title level={4} style={{ color: '#52c41a' }}>⚠️ 봇 시작 확인</Title>
                        <p>자동 트레이딩 봇을 시작하시겠습니까?</p>
                        <div style={{ background: '#f5f5f5', padding: '1rem', borderRadius: 4, marginBottom: '1rem' }}>
                            <p><strong>선택된 전략:</strong> {selectedStrategyObj?.name}</p>
                            <p><strong>심볼:</strong> {selectedStrategyObj?.symbol}</p>
                            <p><strong>타임프레임:</strong> {selectedStrategyObj?.timeframe}</p>
                        </div>
                        <div style={{ background: '#fff3e0', padding: '1rem', borderRadius: 4, marginBottom: '1rem', border: '1px solid #ffb74d' }}>
                            <Text style={{ color: '#e65100' }}>
                                <strong>주의:</strong> 실제 거래가 시작되며 실제 자금이 사용됩니다.
                            </Text>
                        </div>
                        <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                            <Button onClick={() => setShowStartConfirm(false)}>취소</Button>
                            <Button type="primary" onClick={handleStartBot} loading={botLoading} style={{ background: '#52c41a', borderColor: '#52c41a' }}>
                                확인 - 봇 시작
                            </Button>
                        </Space>
                    </Card>
                </div>
            )}

            {/* Stop Bot Confirmation Modal */}
            {showStopConfirm && (
                <div style={{
                    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                    background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center',
                    justifyContent: 'center', zIndex: 1000
                }}>
                    <Card style={{ maxWidth: 500, width: '90%' }}>
                        <Title level={4} style={{ color: '#f5222d' }}>🛑 봇 중지 확인</Title>
                        <p>자동 트레이딩 봇을 중지하시겠습니까?</p>
                        <div style={{ background: '#ffebee', padding: '1rem', borderRadius: 4, marginBottom: '1rem', border: '1px solid #ef5350' }}>
                            <Text style={{ color: '#c62828' }}>
                                <strong>⚠️ 중요:</strong> 봇이 중지되면 모든 열린 포지션이 자동으로 청산됩니다.
                            </Text>
                        </div>
                        <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                            <Button onClick={() => setShowStopConfirm(false)}>취소</Button>
                            <Button danger onClick={handleStopBot} loading={botLoading}>
                                확인 - 봇 중지 및 청산
                            </Button>
                        </Space>
                    </Card>
                </div>
            )}
        </div>
    );
}

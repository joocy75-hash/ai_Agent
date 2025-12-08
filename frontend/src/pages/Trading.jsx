import { useState, useEffect, useCallback } from 'react';
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
import { chartAPI } from '../api/chart';
import { botAPI } from '../api/bot';
import { strategyAPI } from '../api/strategy';
import { useAuth } from '../context/AuthContext';
import { useWebSocket } from '../context/WebSocketContext';
import TradingChart from '../components/TradingChart';
import BalanceCard from '../components/BalanceCard';
import PositionList from '../components/PositionList';

const { Title, Text } = Typography;
const { Option } = Select;

export default function Trading() {
    const { user } = useAuth();
    const { isConnected, subscribe } = useWebSocket();

    // 화면 크기 감지
    const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

    useEffect(() => {
        const handleResize = () => setIsMobile(window.innerWidth < 768);
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    // Chart State
    const [symbol, setSymbol] = useState('BTCUSDT');
    const [timeframe, setTimeframe] = useState('1m');
    const [candles, setCandles] = useState([]);
    const [positions, setPositions] = useState([]);
    const [tradeMarkers, setTradeMarkers] = useState([]);
    const [chartLoading, setChartLoading] = useState(false);
    const [wsUpdateCallback, setWsUpdateCallback] = useState(null);

    // Bot State
    const [botStatus, setBotStatus] = useState(null);
    const [strategies, setStrategies] = useState([]);
    const [selectedStrategy, setSelectedStrategy] = useState('');
    const [botLoading, setBotLoading] = useState(false);
    const [showStartConfirm, setShowStartConfirm] = useState(false);
    const [showStopConfirm, setShowStopConfirm] = useState(false);

    const symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT'];
    const timeframes = [
        { value: '1m', label: '1분' },
        { value: '5m', label: '5분' },
        { value: '15m', label: '15분' },
        { value: '1h', label: '1시간' },
        { value: '4h', label: '4시간' },
        { value: '1d', label: '1일' },
    ];

    // Load Chart Data
    const loadChartData = useCallback(async () => {
        console.log(`[Trading] Loading chart data - Symbol: ${symbol}, Timeframe: ${timeframe}`);
        setChartLoading(true);
        try {
            const [candleData, positionData, markersData] = await Promise.all([
                chartAPI.getCandles(symbol, 200, true, timeframe),
                chartAPI.getCurrentPositions(symbol),
                chartAPI.getPositionMarkers(symbol, 30) // 최근 30일 마커
            ]);
            console.log(`[Trading] Received ${candleData.candles?.length || 0} candles for ${symbol} ${timeframe}`);
            console.log(`[Trading] Received ${markersData.markers?.length || 0} trade markers`);
            setCandles(candleData.candles || []);
            setPositions(positionData.positions || []);
            setTradeMarkers(markersData.markers || []);
        } catch (err) {
            console.error('[Trading] Chart load error:', err);
            message.error('차트 데이터 로드 실패');
        } finally {
            setChartLoading(false);
        }
    }, [symbol, timeframe]);

    // Load Bot Data
    const loadBotData = async () => {
        setBotLoading(true);
        try {
            const [statusData, aiStrategies, publicStrategies] = await Promise.all([
                botAPI.getBotStatus(),
                strategyAPI.getAIStrategies(),
                strategyAPI.getPublicStrategies()
            ]);

            setBotStatus(statusData);

            const aiStrategyList = aiStrategies.strategies || [];
            const publicStrategyList = Array.isArray(publicStrategies) ? publicStrategies : (publicStrategies.strategies || []);
            const allStrategies = [...aiStrategyList, ...publicStrategyList];
            setStrategies(allStrategies);

            if (statusData.strategy_id) {
                setSelectedStrategy(statusData.strategy_id.toString());
            }
        } catch (err) {
            console.error('[Trading] Bot data load error:', err);
        } finally {
            setBotLoading(false);
        }
    };

    // Initial Load
    useEffect(() => {
        loadChartData();
        loadBotData();
    }, []);

    // Reload on symbol/timeframe change
    useEffect(() => {
        console.log(`[Trading] useEffect triggered - Symbol: ${symbol}, Timeframe: ${timeframe}`);
        loadChartData();
    }, [symbol, timeframe, loadChartData]);

    // WebSocket for real-time candle updates
    useEffect(() => {
        if (!isConnected) return;

        const unsubscribe = subscribe('candle_update', (data) => {
            if (data.symbol === symbol && data.current_candle) {
                if (wsUpdateCallback) {
                    wsUpdateCallback(data.current_candle);
                }
                setCandles(prev => {
                    const newCandles = [...prev];
                    if (newCandles.length > 0) {
                        newCandles[newCandles.length - 1] = data.current_candle;
                    }
                    return newCandles;
                });
            }
        });

        return () => unsubscribe();
    }, [isConnected, symbol, subscribe, wsUpdateCallback]);

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

    const handleCandleUpdateCallback = useCallback((updateFn) => {
        setWsUpdateCallback(() => updateFn);
    }, []);

    const isRunning = botStatus?.is_running || false;
    const selectedStrategyObj = strategies.find(s => s.id === parseInt(selectedStrategy));
    const latestCandle = candles.length > 0 ? candles[candles.length - 1] : null;
    const priceChange = latestCandle && candles.length > 1
        ? ((latestCandle.close - candles[0].open) / candles[0].open * 100).toFixed(2)
        : 0;

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
                    {/* Combined Chart Card */}
                    <Card
                        style={{ marginBottom: isMobile ? 12 : 20 }}
                        styles={{ body: { padding: 0 } }}
                        extra={
                            <Button
                                icon={<ReloadOutlined />}
                                onClick={loadChartData}
                                loading={chartLoading}
                                size="small"
                                type="text"
                            >
                                {!isMobile && '새로고침'}
                            </Button>
                        }
                    >
                        {/* Chart - 고정 높이로 줄어듦 방지 */}
                        <div style={{
                            minHeight: isMobile ? 300 : 500,
                            position: 'relative',
                            display: 'flex',
                            alignItems: candles.length === 0 ? 'center' : 'stretch',
                            justifyContent: candles.length === 0 ? 'center' : 'flex-start'
                        }}>
                            {candles.length === 0 ? (
                                <div style={{ textAlign: 'center', color: chartLoading ? '#666' : '#c62828' }}>
                                    {chartLoading ? '차트 데이터를 불러오는 중...' : '차트 데이터가 없습니다. 새로고침을 눌러주세요.'}
                                </div>
                            ) : (
                                <>
                                    {/* 로딩 오버레이 - 기존 차트 위에 표시 */}
                                    {chartLoading && (
                                        <div style={{
                                            position: 'absolute',
                                            top: 8,
                                            right: 8,
                                            zIndex: 10,
                                            background: 'rgba(255,255,255,0.9)',
                                            padding: '4px 12px',
                                            borderRadius: 6,
                                            fontSize: 12,
                                            color: '#666',
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: 6
                                        }}>
                                            <span style={{
                                                width: 8,
                                                height: 8,
                                                borderRadius: '50%',
                                                background: '#52c41a',
                                                animation: 'pulse 1s infinite'
                                            }} />
                                            업데이트 중...
                                        </div>
                                    )}
                                    <TradingChart
                                        data={candles}
                                        symbol={symbol.replace('USDT', '/USDT')}
                                        positions={positions}
                                        tradeMarkers={tradeMarkers}
                                        height={isMobile ? 300 : 500}
                                        timeframe={timeframe}
                                        availableTimeframes={timeframes}
                                        onTimeframeChange={setTimeframe}
                                        onCandleUpdate={handleCandleUpdateCallback}
                                        availableSymbols={symbols}
                                        onSymbolChange={setSymbol}
                                    />
                                </>
                            )}
                        </div>
                    </Card>

                    {/* Position List */}
                    <PositionList currentPrices={{ [symbol]: latestCandle?.close || 0 }} />
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
                            {/* Bot Status */}
                            <div style={{
                                padding: '20px',
                                background: isRunning
                                    ? 'linear-gradient(135deg, #f6ffed 0%, #d9f7be 100%)'
                                    : '#f5f5f7',
                                borderRadius: 12,
                                textAlign: 'center',
                                border: isRunning ? '1px solid #b7eb8f' : '1px solid #e5e5e5'
                            }}>
                                <div style={{
                                    width: 48,
                                    height: 48,
                                    margin: '0 auto 12px',
                                    borderRadius: '50%',
                                    background: isRunning ? '#52c41a' : '#d9d9d9',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    boxShadow: isRunning ? '0 0 20px rgba(82, 196, 26, 0.4)' : 'none'
                                }}>
                                    {isRunning ? (
                                        <PauseCircleOutlined style={{ fontSize: 24, color: '#fff' }} />
                                    ) : (
                                        <PlayCircleOutlined style={{ fontSize: 24, color: '#fff' }} />
                                    )}
                                </div>
                                <Text strong style={{ fontSize: 16, color: isRunning ? '#389e0d' : '#8c8c8c' }}>
                                    {isRunning ? 'AI Bot 실행 중' : 'AI Bot 대기 중'}
                                </Text>
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
                                    <Space wrap>
                                        <Tag color="blue">{selectedStrategyObj.type}</Tag>
                                        <Tag color="purple">{selectedStrategyObj.symbol}</Tag>
                                        <Tag color="green">{selectedStrategyObj.timeframe}</Tag>
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
                                <Space wrap size={[8, 8]}>
                                    <Tag color="blue">{selectedStrategyObj.type || 'AI'}</Tag>
                                    <Tag color="purple">{selectedStrategyObj.symbol}</Tag>
                                    <Tag color="cyan">{selectedStrategyObj.timeframe}</Tag>
                                    {selectedStrategyObj.leverage && (
                                        <Tag color="orange">x{selectedStrategyObj.leverage}</Tag>
                                    )}
                                </Space>
                            </div>

                            {/* Description */}
                            <div style={{
                                background: '#fafafa',
                                padding: 12,
                                borderRadius: 8,
                                marginBottom: 12,
                                border: '1px solid #f0f0f0'
                            }}>
                                <Text style={{ color: '#666' }}>
                                    <InfoCircleOutlined style={{ marginRight: 8, color: '#1890ff' }} />
                                    {selectedStrategyObj.description || '이 전략은 AI 기반 자동 매매 전략입니다. 설정된 조건에 따라 자동으로 포지션을 진입/청산합니다.'}
                                </Text>
                            </div>

                            {/* Parameters */}
                            {selectedStrategyObj.params && Object.keys(selectedStrategyObj.params).length > 0 && (
                                <div>
                                    <Text strong style={{ display: 'block', marginBottom: 8 }}>파라미터</Text>
                                    <div style={{ background: '#f5f5f5', padding: 12, borderRadius: 8 }}>
                                        {Object.entries(selectedStrategyObj.params).map(([key, value]) => (
                                            <div key={key} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                                                <Text type="secondary">{key}:</Text>
                                                <Text strong>{String(value)}</Text>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Risk Level */}
                            <div style={{ marginTop: 12 }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <Text type="secondary">위험도</Text>
                                    <Tag color={selectedStrategyObj.risk_level === 'high' ? 'red' : selectedStrategyObj.risk_level === 'medium' ? 'orange' : 'green'}>
                                        {selectedStrategyObj.risk_level === 'high' ? '고위험' : selectedStrategyObj.risk_level === 'medium' ? '중위험' : '저위험'}
                                    </Tag>
                                </div>
                            </div>

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

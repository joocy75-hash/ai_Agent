import { useState, useEffect, useCallback } from 'react';
import {
    Card, Row, Col, Typography, Form, Select, InputNumber, DatePicker,
    Button, message, Progress, Statistic, Table, Tag, Alert, Tabs,
    Empty, Modal, Descriptions, Space, Tooltip, Divider, Spin
} from 'antd';
import {
    ExperimentOutlined,
    PlayCircleOutlined,
    CheckCircleOutlined,
    WarningOutlined,
    RiseOutlined,
    FallOutlined,
    DollarOutlined,
    HistoryOutlined,
    SwapOutlined,
    EyeOutlined,
    DeleteOutlined,
    ReloadOutlined,
    CloseCircleOutlined,
    LoadingOutlined,
    AreaChartOutlined,
    InfoCircleOutlined,
    DatabaseOutlined
} from '@ant-design/icons';
import { strategyAPI } from '../api/strategy';
import { backtestAPI } from '../api/backtest';
import EquityCurveChart from '../components/backtest/EquityCurveChart';
import { TermTooltip, ScoreCard, BacktestTips, PresetButtons } from '../components/backtest/BeginnerGuide';
import dayjs from 'dayjs';

const { Title, Text } = Typography;
const { Option } = Select;
const { RangePicker } = DatePicker;

export default function BacktestingPage() {
    // 화면 크기 감지
    const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

    useEffect(() => {
        const handleResize = () => setIsMobile(window.innerWidth < 768);
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    const [activeTab, setActiveTab] = useState('run');

    // 백테스트 실행 상태
    const [form] = Form.useForm();
    const [strategies, setStrategies] = useState([]);
    const [loading, setLoading] = useState(false);
    const [running, setRunning] = useState(false);
    const [progress, setProgress] = useState(0);
    const [result, setResult] = useState(null);

    // 이력 상태
    const [history, setHistory] = useState([]);
    const [historyLoading, setHistoryLoading] = useState(false);
    const [selectedResult, setSelectedResult] = useState(null);
    const [detailModalOpen, setDetailModalOpen] = useState(false);
    const [detailLoading, setDetailLoading] = useState(false);

    // 비교 상태
    const [selectedForCompare, setSelectedForCompare] = useState([]);

    // 캐시 정보 상태
    const [cacheInfo, setCacheInfo] = useState(null);
    const [availableSymbols, setAvailableSymbols] = useState([]);
    const [availableTimeframes, setAvailableTimeframes] = useState([]);

    // 전략 목록 및 캐시 정보 로드
    useEffect(() => {
        loadStrategies();
        loadHistory();
        loadCacheInfo();
    }, []);

    // 캐시 정보 로드
    const loadCacheInfo = async () => {
        try {
            const [cacheRes, symbolsRes] = await Promise.all([
                backtestAPI.getCacheInfo(),
                backtestAPI.getAvailableSymbols()
            ]);
            setCacheInfo(cacheRes);
            setAvailableSymbols(symbolsRes.symbols || ['BTCUSDT', 'ETHUSDT']);
            setAvailableTimeframes(symbolsRes.timeframes || ['1h', '4h', '1d']);
        } catch (error) {
            console.error('Failed to load cache info:', error);
        }
    };


    const loadStrategies = async () => {
        setLoading(true);
        try {
            const [aiRes, publicRes] = await Promise.all([
                strategyAPI.getAIStrategies(),
                strategyAPI.getPublicStrategies()
            ]);

            const aiList = aiRes.strategies || [];
            const publicList = Array.isArray(publicRes) ? publicRes : (publicRes.strategies || []);
            setStrategies([...aiList, ...publicList]);
        } catch (error) {
            console.error('Failed to load strategies:', error);
        } finally {
            setLoading(false);
        }
    };

    const loadHistory = async () => {
        setHistoryLoading(true);
        try {
            const response = await backtestAPI.getAllBacktests();
            setHistory(response.backtests || []);
        } catch (error) {
            console.error('Failed to load history:', error);
            message.error('백테스트 이력을 불러오지 못했습니다');
        } finally {
            setHistoryLoading(false);
        }
    };

    const handleRunBacktest = async (values) => {
        setRunning(true);
        setProgress(0);
        setResult(null);

        try {
            const selectedStrategy = strategies.find(s => s.id === values.strategy_id);

            const backtestRequest = {
                strategy_id: values.strategy_id,
                initial_balance: values.initial_balance,
                start_date: values.date_range[0].format('YYYY-MM-DD'),
                end_date: values.date_range[1].format('YYYY-MM-DD'),
                symbol: values.symbol,
                timeframe: values.timeframe,
            };

            console.log('[Backtest] Starting with:', backtestRequest);

            // 백테스트 시작
            const startResponse = await backtestAPI.runBacktest(backtestRequest);
            const resultId = startResponse.result_id;

            if (!resultId) {
                throw new Error('백테스트 ID를 받지 못했습니다');
            }

            message.info(`백테스트 #${resultId} 시작됨`);

            // 진행률 폴링
            let attempts = 0;
            const maxAttempts = 120;

            const pollInterval = setInterval(async () => {
                attempts++;
                setProgress(Math.min((attempts / maxAttempts) * 100, 95));

                try {
                    const resultResponse = await backtestAPI.getResult(resultId);
                    console.log('[Backtest] Poll result:', resultResponse);

                    if (resultResponse.status === 'completed') {
                        clearInterval(pollInterval);
                        setProgress(100);

                        // 결과 파싱
                        let metrics = {};
                        try {
                            metrics = typeof resultResponse.metrics === 'string'
                                ? JSON.parse(resultResponse.metrics)
                                : (resultResponse.metrics || {});
                        } catch (e) {
                            console.warn('Failed to parse metrics:', e);
                        }

                        setResult({
                            ...resultResponse,
                            total_return: metrics.total_return || 0,
                            win_rate: metrics.win_rate || 0,
                            max_drawdown: metrics.max_drawdown || 0,
                            total_trades: metrics.total_trades || 0,
                            profit_factor: metrics.profit_factor || 0,
                            sharpe_ratio: metrics.sharpe_ratio || 0,
                            equity_curve: resultResponse.equity_curve || [],
                            trades: resultResponse.trades || [],
                        });

                        setRunning(false);
                        message.success('백테스트가 완료되었습니다!');

                        // 이력 새로고침
                        loadHistory();

                    } else if (resultResponse.status === 'failed') {
                        clearInterval(pollInterval);
                        setRunning(false);
                        message.error(`백테스트 실패: ${resultResponse.error_message || '알 수 없는 오류'}`);
                    }

                    if (attempts >= maxAttempts) {
                        clearInterval(pollInterval);
                        setRunning(false);
                        message.warning('백테스트 시간 초과');
                    }
                } catch (err) {
                    console.error('Result polling error:', err);
                }
            }, 1000);

        } catch (error) {
            console.error('Backtest error:', error);
            message.error(error.response?.data?.detail || error.message || '백테스트 시작 실패');
            setRunning(false);
        }
    };

    const handleViewDetail = async (record) => {
        setDetailModalOpen(true);
        setDetailLoading(true);
        setSelectedResult(record);

        try {
            // 상세 정보 (equity_curve 포함) 가져오기
            const detailResult = await backtestAPI.getResult(record.id);
            setSelectedResult({
                ...record,
                ...detailResult,
                equity_curve: detailResult.equity_curve || [],
                trades: detailResult.trades || [],
            });
        } catch (error) {
            console.error('Failed to load backtest detail:', error);
            message.error('상세 정보를 불러오지 못했습니다');
        } finally {
            setDetailLoading(false);
        }
    };

    const handleDelete = async (id) => {
        Modal.confirm({
            title: '백테스트 결과 삭제',
            content: '이 백테스트 결과를 삭제하시겠습니까?',
            okText: '삭제',
            okType: 'danger',
            cancelText: '취소',
            onOk: async () => {
                try {
                    await backtestAPI.deleteResult(id);
                    message.success('삭제되었습니다');
                    loadHistory();
                } catch (error) {
                    message.error('삭제 실패');
                }
            }
        });
    };

    const toggleCompareSelect = (record) => {
        setSelectedForCompare(prev => {
            const exists = prev.find(r => r.id === record.id);
            if (exists) {
                return prev.filter(r => r.id !== record.id);
            }
            if (prev.length >= 4) {
                message.warning('최대 4개까지 비교 가능합니다');
                return prev;
            }
            return [...prev, record];
        });
    };

    const getStatusTag = (status) => {
        const statusConfig = {
            completed: { color: 'success', icon: <CheckCircleOutlined />, text: '완료' },
            running: { color: 'processing', icon: <LoadingOutlined />, text: '실행 중' },
            queued: { color: 'default', icon: <LoadingOutlined />, text: '대기 중' },
            pending: { color: 'default', icon: <LoadingOutlined />, text: '대기 중' },
            failed: { color: 'error', icon: <CloseCircleOutlined />, text: '실패' },
        };
        const config = statusConfig[status] || statusConfig.pending;
        return <Tag color={config.color} icon={config.icon}>{config.text}</Tag>;
    };
    // 백테스트 실행 탭
    const renderRunTab = () => (
        <Row gutter={isMobile ? [8, 8] : [24, 24]}>
            <Col xs={24} lg={10}>
                {/* 초보자 꿀팁 카드 */}
                <BacktestTips />

                <Card title="🎯 백테스트 설정" style={{ marginBottom: 24 }}>


                    <Form
                        form={form}
                        layout="vertical"
                        onFinish={handleRunBacktest}
                        initialValues={{
                            symbol: 'BTCUSDT',
                            timeframe: '1h',
                            initial_balance: 10000,
                            date_range: [dayjs().subtract(30, 'day'), dayjs()]
                        }}
                    >
                        <Form.Item
                            name="strategy_id"
                            label={<TermTooltip term="strategy">전략 선택</TermTooltip>}
                            rules={[{ required: true, message: '전략을 선택하세요' }]}
                        >
                            <Select
                                placeholder="전략을 선택하세요"
                                loading={loading}
                                size="large"
                                showSearch
                                optionFilterProp="children"
                            >
                                {strategies.map(s => (
                                    <Option key={s.id} value={s.id}>
                                        {s.name}
                                    </Option>
                                ))}
                            </Select>
                        </Form.Item>

                        <Row gutter={16}>
                            <Col span={12}>
                                <Form.Item
                                    name="symbol"
                                    label="거래 코인"
                                    rules={[{ required: true }]}
                                >
                                    <Select size="large">
                                        {(availableSymbols.length > 0 ? availableSymbols : ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT']).map(s => {
                                            const coinId = s.replace('USDT', '').toLowerCase();
                                            const logoUrl = `https://assets.coingecko.com/coins/images/${coinId === 'btc' ? '1/small/bitcoin.png' :
                                                coinId === 'eth' ? '279/small/ethereum.png' :
                                                    coinId === 'sol' ? '4128/small/solana.png' :
                                                        coinId === 'xrp' ? '44/small/xrp-symbol-white-128.png' :
                                                            coinId === 'doge' ? '5/small/dogecoin.png' :
                                                                coinId === 'ada' ? '975/small/cardano.png' :
                                                                    coinId === 'avax' ? '12559/small/Avalanche_Circle_RedWhite_Trans.png' :
                                                                        coinId === 'dot' ? '12171/small/polkadot.png' :
                                                                            coinId === 'link' ? '877/small/chainlink-new-logo.png' :
                                                                                coinId === 'matic' ? '4713/small/matic-token-icon.png' :
                                                                                    coinId === 'bnb' ? '825/small/bnb-icon2_2x.png' :
                                                                                        '1/small/bitcoin.png'
                                                }`;
                                            return (
                                                <Option key={s} value={s}>
                                                    <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                                        <img
                                                            src={logoUrl}
                                                            alt={coinId}
                                                            style={{ width: 20, height: 20, borderRadius: '50%' }}
                                                            onError={(e) => { e.target.style.display = 'none'; }}
                                                        />
                                                        {s.replace('USDT', '/USDT')}
                                                    </span>
                                                </Option>
                                            );
                                        })}
                                    </Select>
                                </Form.Item>
                            </Col>
                            <Col span={12}>
                                <Form.Item
                                    name="timeframe"
                                    label={<TermTooltip term="timeframe">시간봉</TermTooltip>}
                                    rules={[{ required: true }]}
                                >
                                    <Select size="large">
                                        {(availableTimeframes.length > 0 ? availableTimeframes : ['1h', '4h', '1d']).map(tf => (
                                            <Option key={tf} value={tf}>
                                                {tf === '1h' ? '1시간' : tf === '4h' ? '4시간' : tf === '1d' ? '1일' : tf}
                                            </Option>
                                        ))}
                                    </Select>
                                </Form.Item>
                            </Col>
                        </Row>

                        <Form.Item
                            name="initial_balance"
                            label={<TermTooltip term="initial_balance">초기 자금 (USDT)</TermTooltip>}
                            rules={[{ required: true }]}
                        >
                            <InputNumber
                                min={100}
                                max={1000000}
                                style={{ width: '100%' }}
                                size="large"
                                formatter={value => `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                            />
                        </Form.Item>

                        <Form.Item
                            name="date_range"
                            label="테스트 기간"
                            rules={[{ required: true, message: '기간을 선택하세요' }]}
                        >
                            <RangePicker
                                style={{ width: '100%' }}
                                size="large"
                                format="YYYY-MM-DD"
                            />
                        </Form.Item>



                        <Button
                            type="primary"
                            htmlType="submit"
                            icon={<PlayCircleOutlined />}
                            loading={running}
                            block
                            size="large"
                            style={{
                                height: 50,
                                fontSize: 16,
                                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                                border: 'none'
                            }}
                        >
                            {running ? '백테스트 실행 중...' : '🚀 백테스트 시작'}
                        </Button>
                    </Form>

                    {running && (
                        <div style={{ marginTop: 24 }}>
                            <Progress
                                percent={Math.round(progress)}
                                status="active"
                                strokeColor={{
                                    '0%': '#667eea',
                                    '100%': '#764ba2',
                                }}
                            />
                            <Text type="secondary">데이터 분석 중... ({Math.round(progress)}%)</Text>
                        </div>
                    )}
                </Card>
            </Col>

            <Col xs={24} lg={14}>
                {result ? (
                    <div>
                        <Card title="📊 백테스트 결과" style={{ marginBottom: 16 }}>
                            <Row gutter={[16, 16]}>
                                <Col span={8}>
                                    <Statistic
                                        title="총 수익률"
                                        value={Math.round(result.total_return || 0)}
                                        precision={0}
                                        suffix="%"
                                        valueStyle={{
                                            color: (result.total_return || 0) >= 0 ? '#3f8600' : '#cf1322'
                                        }}
                                        prefix={(result.total_return || 0) >= 0 ? <RiseOutlined /> : <FallOutlined />}
                                    />
                                </Col>
                                <Col span={8}>
                                    <Statistic
                                        title="최종 자금"
                                        value={Math.round(result.final_balance || 0)}
                                        precision={0}
                                        prefix={<DollarOutlined />}
                                    />
                                </Col>
                                <Col span={8}>
                                    <Statistic
                                        title="총 거래"
                                        value={result.total_trades || 0}
                                        suffix="회"
                                    />
                                </Col>
                                <Col span={8}>
                                    <Statistic
                                        title="승률"
                                        value={Math.round(result.win_rate || 0)}
                                        precision={0}
                                        suffix="%"
                                        valueStyle={{
                                            color: (result.win_rate || 0) >= 50 ? '#3f8600' : '#cf1322'
                                        }}
                                    />
                                </Col>
                                <Col span={8}>
                                    <Statistic
                                        title="최대 손실"
                                        value={Math.round(Math.abs(result.max_drawdown || 0))}
                                        precision={0}
                                        suffix="%"
                                        valueStyle={{ color: '#cf1322' }}
                                        prefix={<WarningOutlined />}
                                    />
                                </Col>
                                <Col span={8}>
                                    <Statistic
                                        title="Profit Factor"
                                        value={(result.profit_factor || 0).toFixed(1)}
                                        precision={1}
                                    />
                                </Col>
                            </Row>
                        </Card>

                        {/* 에쿼티 커브 차트 */}
                        {result.equity_curve && result.equity_curve.length > 0 && (
                            <EquityCurveChart
                                equityCurve={result.equity_curve}
                                initialBalance={result.initial_balance || 10000}
                                metrics={{
                                    total_return: result.total_return,
                                    win_rate: result.win_rate,
                                    max_drawdown: result.max_drawdown,
                                    total_trades: result.total_trades,
                                    profit_factor: result.profit_factor,
                                    sharpe_ratio: result.sharpe_ratio,
                                }}
                                trades={result.trades || []}
                                showStats={false}
                                height={300}
                            />
                        )}

                        {/* 🎓 초보자용 전략 점수표 */}
                        <ScoreCard
                            metrics={{
                                total_return: result.total_return,
                                win_rate: result.win_rate,
                                max_drawdown: result.max_drawdown,
                                profit_factor: result.profit_factor,
                                sharpe_ratio: result.sharpe_ratio,
                                total_trades: result.total_trades,
                            }}
                        />
                    </div>
                ) : (
                    <Card style={{ textAlign: 'center', padding: '60px 0' }}>
                        <ExperimentOutlined style={{ fontSize: 64, color: '#d9d9d9', marginBottom: 24 }} />
                        <Title level={4} type="secondary">백테스트 결과가 없습니다</Title>
                        <Text type="secondary">
                            왼쪽에서 설정을 완료하고 백테스트를 실행하세요
                        </Text>
                    </Card>
                )}
            </Col>
        </Row>
    );

    // 백테스트 이력 탭
    const renderHistoryTab = () => {
        const columns = [
            {
                title: '#',
                dataIndex: 'id',
                width: 60,
            },
            {
                title: '심볼',
                dataIndex: ['config', 'symbol'],
                width: 100,
                render: (text) => <Tag color="blue">{text}</Tag>,
            },
            {
                title: '수익률',
                dataIndex: ['metrics', 'total_return'],
                width: 120,
                render: (value) => (
                    <span style={{
                        color: value >= 0 ? '#52c41a' : '#ff4d4f',
                        fontWeight: 'bold'
                    }}>
                        {value >= 0 ? <RiseOutlined /> : <FallOutlined />}
                        {' '}{value?.toFixed(2)}%
                    </span>
                ),
            },
            {
                title: '거래',
                dataIndex: ['metrics', 'total_trades'],
                width: 70,
                render: (value) => `${value}회`,
            },
            {
                title: '승률',
                dataIndex: ['metrics', 'win_rate'],
                width: 80,
                render: (value) => `${value?.toFixed(1)}%`,
            },
            {
                title: '상태',
                dataIndex: 'status',
                width: 90,
                render: (status) => getStatusTag(status),
            },
            {
                title: '일시',
                dataIndex: 'created_at',
                width: 140,
                render: (text) => dayjs(text).format('MM-DD HH:mm'),
            },
            {
                title: '작업',
                width: 120,
                render: (_, record) => (
                    <Space>
                        <Tooltip title="상세 보기">
                            <Button
                                type="text"
                                icon={<EyeOutlined />}
                                onClick={() => handleViewDetail(record)}
                            />
                        </Tooltip>
                        <Tooltip title={selectedForCompare.find(r => r.id === record.id) ? '비교 해제' : '비교 추가'}>
                            <Button
                                type={selectedForCompare.find(r => r.id === record.id) ? 'primary' : 'text'}
                                icon={<SwapOutlined />}
                                onClick={() => toggleCompareSelect(record)}
                            />
                        </Tooltip>
                        <Tooltip title="삭제">
                            <Button
                                type="text"
                                danger
                                icon={<DeleteOutlined />}
                                onClick={() => handleDelete(record.id)}
                            />
                        </Tooltip>
                    </Space>
                ),
            },
        ];

        return (
            <div>
                <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
                    <div>
                        {selectedForCompare.length > 0 && (
                            <Space>
                                <Tag color="blue">{selectedForCompare.length}개 선택됨</Tag>
                                <Button
                                    type="primary"
                                    icon={<SwapOutlined />}
                                    onClick={() => setActiveTab('compare')}
                                    disabled={selectedForCompare.length < 2}
                                >
                                    비교하기
                                </Button>
                                <Button onClick={() => setSelectedForCompare([])}>선택 해제</Button>
                            </Space>
                        )}
                    </div>
                    <Button
                        icon={<ReloadOutlined />}
                        onClick={loadHistory}
                        loading={historyLoading}
                    >
                        새로고침
                    </Button>
                </div>

                <Table
                    columns={columns}
                    dataSource={history}
                    rowKey="id"
                    loading={historyLoading}
                    locale={{
                        emptyText: (
                            <Empty
                                description="백테스트 이력이 없습니다"
                                image={Empty.PRESENTED_IMAGE_SIMPLE}
                            />
                        )
                    }}
                    pagination={{
                        pageSize: 10,
                        showSizeChanger: true,
                        showTotal: (total) => `총 ${total}개`,
                    }}
                />
            </div>
        );
    };

    // 비교 탭
    const renderCompareTab = () => {
        if (selectedForCompare.length < 2) {
            return (
                <Card style={{ textAlign: 'center', padding: '60px 0' }}>
                    <SwapOutlined style={{ fontSize: 64, color: '#d9d9d9', marginBottom: 24 }} />
                    <Title level={4} type="secondary">비교할 백테스트를 선택하세요</Title>
                    <Text type="secondary">
                        이력 탭에서 2개 이상의 백테스트를 선택해주세요 (최대 4개)
                    </Text>
                    <br />
                    <Button
                        type="primary"
                        style={{ marginTop: 16 }}
                        onClick={() => setActiveTab('history')}
                    >
                        이력으로 이동
                    </Button>
                </Card>
            );
        }

        return (
            <div>
                <Alert
                    message={`${selectedForCompare.length}개 백테스트 비교 중`}
                    type="info"
                    showIcon
                    action={
                        <Button size="small" onClick={() => setSelectedForCompare([])}>
                            선택 해제
                        </Button>
                    }
                    style={{ marginBottom: 24 }}
                />

                <Row gutter={[16, 16]}>
                    {selectedForCompare.map((bt, idx) => (
                        <Col xs={24} sm={12} lg={6} key={bt.id}>
                            <Card
                                title={`#${bt.id} - ${bt.config?.symbol}`}
                                size="small"
                                extra={
                                    <Button
                                        type="text"
                                        size="small"
                                        danger
                                        icon={<CloseCircleOutlined />}
                                        onClick={() => toggleCompareSelect(bt)}
                                    />
                                }
                            >
                                <Statistic
                                    title="수익률"
                                    value={bt.metrics?.total_return || 0}
                                    precision={2}
                                    suffix="%"
                                    valueStyle={{
                                        color: (bt.metrics?.total_return || 0) >= 0 ? '#52c41a' : '#ff4d4f',
                                        fontSize: 24
                                    }}
                                />
                                <Divider style={{ margin: '12px 0' }} />
                                <Row gutter={8}>
                                    <Col span={12}>
                                        <Text type="secondary">승률</Text>
                                        <div>{bt.metrics?.win_rate?.toFixed(1)}%</div>
                                    </Col>
                                    <Col span={12}>
                                        <Text type="secondary">거래</Text>
                                        <div>{bt.metrics?.total_trades}회</div>
                                    </Col>
                                </Row>
                                <Row gutter={8} style={{ marginTop: 8 }}>
                                    <Col span={12}>
                                        <Text type="secondary">MDD</Text>
                                        <div style={{ color: '#ff4d4f' }}>
                                            {bt.metrics?.max_drawdown?.toFixed(2)}%
                                        </div>
                                    </Col>
                                    <Col span={12}>
                                        <Text type="secondary">PF</Text>
                                        <div>{bt.metrics?.profit_factor?.toFixed(2)}</div>
                                    </Col>
                                </Row>
                            </Card>
                        </Col>
                    ))}
                </Row>

                <Card title="📊 비교 테이블" style={{ marginTop: 24 }}>
                    <Table
                        dataSource={[
                            { metric: '총 수익률', ...Object.fromEntries(selectedForCompare.map((bt, i) => [`bt${i}`, `${bt.metrics?.total_return?.toFixed(2)}%`])) },
                            { metric: '승률', ...Object.fromEntries(selectedForCompare.map((bt, i) => [`bt${i}`, `${bt.metrics?.win_rate?.toFixed(1)}%`])) },
                            { metric: '거래 수', ...Object.fromEntries(selectedForCompare.map((bt, i) => [`bt${i}`, bt.metrics?.total_trades])) },
                            { metric: '최대 손실', ...Object.fromEntries(selectedForCompare.map((bt, i) => [`bt${i}`, `${bt.metrics?.max_drawdown?.toFixed(2)}%`])) },
                            { metric: 'Profit Factor', ...Object.fromEntries(selectedForCompare.map((bt, i) => [`bt${i}`, bt.metrics?.profit_factor?.toFixed(2)])) },
                            { metric: 'Sharpe Ratio', ...Object.fromEntries(selectedForCompare.map((bt, i) => [`bt${i}`, bt.metrics?.sharpe_ratio?.toFixed(2)])) },
                        ]}
                        columns={[
                            { title: '지표', dataIndex: 'metric', fixed: 'left', width: 120 },
                            ...selectedForCompare.map((bt, i) => ({
                                title: `#${bt.id}`,
                                dataIndex: `bt${i}`,
                                width: 100,
                            }))
                        ]}
                        pagination={false}
                        size="small"
                        rowKey="metric"
                    />
                </Card>
            </div>
        );
    };

    return (
        <div style={{ maxWidth: 1400, margin: '0 auto' }}>
            <div style={{ marginBottom: isMobile ? 12 : 24 }}>
                <Title level={isMobile ? 3 : 2}>
                    <ExperimentOutlined style={{ marginRight: 8 }} />
                    백테스팅
                </Title>
                {!isMobile && (
                    <Text type="secondary">
                        과거 데이터로 전략의 성과를 검증하고 비교하세요
                    </Text>
                )}
            </div>

            <Tabs
                activeKey={activeTab}
                onChange={setActiveTab}
                size="large"
                items={[
                    {
                        key: 'run',
                        label: (
                            <span>
                                <PlayCircleOutlined />
                                백테스트 실행
                            </span>
                        ),
                        children: renderRunTab()
                    },
                    {
                        key: 'history',
                        label: (
                            <span>
                                <HistoryOutlined />
                                백테스트 이력
                                {history.length > 0 && (
                                    <Tag color="blue" style={{ marginLeft: 8 }}>{history.length}</Tag>
                                )}
                            </span>
                        ),
                        children: renderHistoryTab()
                    },
                    {
                        key: 'compare',
                        label: (
                            <span>
                                <SwapOutlined />
                                백테스트 비교
                                {selectedForCompare.length > 0 && (
                                    <Tag color="green" style={{ marginLeft: 8 }}>{selectedForCompare.length}</Tag>
                                )}
                            </span>
                        ),
                        children: renderCompareTab()
                    }
                ]}
            />

            {/* 상세 보기 모달 */}
            <Modal
                title={
                    <Space>
                        <AreaChartOutlined style={{ color: '#1890ff' }} />
                        <span>백테스트 상세 결과 #{selectedResult?.id}</span>
                    </Space>
                }
                open={detailModalOpen}
                onCancel={() => setDetailModalOpen(false)}
                footer={[
                    <Button key="close" onClick={() => setDetailModalOpen(false)}>
                        닫기
                    </Button>
                ]}
                width={1000}
                bodyStyle={{ maxHeight: '80vh', overflowY: 'auto' }}
            >
                {detailLoading ? (
                    <div style={{ textAlign: 'center', padding: 60 }}>
                        <Spin size="large" />
                        <p style={{ marginTop: 16, color: '#666' }}>상세 정보 로딩 중...</p>
                    </div>
                ) : selectedResult && (
                    <div>
                        {/* 기본 정보 요약 */}
                        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
                            <Col xs={12} sm={8} md={4}>
                                <Statistic
                                    title="총 수익률"
                                    value={selectedResult.metrics?.total_return || 0}
                                    precision={2}
                                    suffix="%"
                                    valueStyle={{
                                        color: (selectedResult.metrics?.total_return || 0) >= 0 ? '#52c41a' : '#ff4d4f'
                                    }}
                                    prefix={(selectedResult.metrics?.total_return || 0) >= 0 ? <RiseOutlined /> : <FallOutlined />}
                                />
                            </Col>
                            <Col xs={12} sm={8} md={4}>
                                <Statistic
                                    title="최종 자금"
                                    value={selectedResult.final_balance || selectedResult.initial_balance || 0}
                                    precision={2}
                                    prefix="$"
                                />
                            </Col>
                            <Col xs={12} sm={8} md={4}>
                                <Statistic
                                    title="승률"
                                    value={selectedResult.metrics?.win_rate || 0}
                                    precision={1}
                                    suffix="%"
                                    valueStyle={{
                                        color: (selectedResult.metrics?.win_rate || 0) >= 50 ? '#52c41a' : '#faad14'
                                    }}
                                />
                            </Col>
                            <Col xs={12} sm={8} md={4}>
                                <Statistic
                                    title="총 거래"
                                    value={selectedResult.metrics?.total_trades || 0}
                                    suffix="회"
                                />
                            </Col>
                            <Col xs={12} sm={8} md={4}>
                                <Statistic
                                    title="최대 손실"
                                    value={Math.abs(selectedResult.metrics?.max_drawdown || 0)}
                                    precision={2}
                                    suffix="%"
                                    valueStyle={{ color: '#ff4d4f' }}
                                    prefix={<WarningOutlined />}
                                />
                            </Col>
                            <Col xs={12} sm={8} md={4}>
                                <Statistic
                                    title="Profit Factor"
                                    value={selectedResult.metrics?.profit_factor || 0}
                                    precision={2}
                                    valueStyle={{
                                        color: (selectedResult.metrics?.profit_factor || 0) >= 1.5 ? '#52c41a' :
                                            (selectedResult.metrics?.profit_factor || 0) >= 1 ? '#faad14' : '#ff4d4f'
                                    }}
                                />
                            </Col>
                        </Row>

                        {/* 설명 정보 */}
                        <Descriptions
                            bordered
                            size="small"
                            column={{ xs: 1, sm: 2, md: 3 }}
                            style={{ marginBottom: 24 }}
                        >
                            <Descriptions.Item label="심볼">
                                <Tag color="blue">{selectedResult.config?.symbol || selectedResult.pair}</Tag>
                            </Descriptions.Item>
                            <Descriptions.Item label="타임프레임">
                                {selectedResult.config?.timeframe || selectedResult.timeframe}
                            </Descriptions.Item>
                            <Descriptions.Item label="초기 자금">
                                ${(selectedResult.initial_balance || 10000).toLocaleString()}
                            </Descriptions.Item>
                            <Descriptions.Item label="Sharpe Ratio">
                                {selectedResult.metrics?.sharpe_ratio?.toFixed(2) || 'N/A'}
                            </Descriptions.Item>
                            <Descriptions.Item label="상태">
                                {getStatusTag(selectedResult.status)}
                            </Descriptions.Item>
                            <Descriptions.Item label="실행 일시">
                                {dayjs(selectedResult.created_at).format('YYYY-MM-DD HH:mm:ss')}
                            </Descriptions.Item>
                        </Descriptions>

                        {/* 에쿼티 커브 차트 */}
                        {selectedResult.equity_curve && selectedResult.equity_curve.length > 0 ? (
                            <EquityCurveChart
                                equityCurve={selectedResult.equity_curve}
                                initialBalance={selectedResult.initial_balance || 10000}
                                metrics={selectedResult.metrics || {}}
                                trades={selectedResult.trades || []}
                                showStats={false}
                                height={350}
                            />
                        ) : (
                            <Card style={{ textAlign: 'center', padding: 40 }}>
                                <AreaChartOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />
                                <p style={{ marginTop: 16, color: '#999' }}>
                                    에쿼티 커브 데이터가 없습니다
                                </p>
                            </Card>
                        )}
                    </div>
                )}
            </Modal>

            <Alert
                message="💡 팁"
                description="백테스트 결과는 과거 데이터 기반입니다. 실제 거래에서는 다른 결과가 나올 수 있습니다."
                type="info"
                showIcon
                style={{ marginTop: 24 }}
            />
        </div>
    );
}

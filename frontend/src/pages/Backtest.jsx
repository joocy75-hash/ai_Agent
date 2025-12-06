import { useState, useEffect } from 'react';
import { Card, Row, Col, Typography, Form, Select, InputNumber, DatePicker, Button, message, Progress, Statistic, Table, Tag, Alert } from 'antd';
import {
    ExperimentOutlined,
    PlayCircleOutlined,
    CheckCircleOutlined,
    WarningOutlined,
    RiseOutlined,
    FallOutlined,
    DollarOutlined
} from '@ant-design/icons';
import { strategyAPI } from '../api/strategy';
import { backtestAPI } from '../api/backtest';
import dayjs from 'dayjs';

const { Title, Text } = Typography;
const { Option } = Select;
const { RangePicker } = DatePicker;

export default function Backtest() {
    const [form] = Form.useForm();
    const [strategies, setStrategies] = useState([]);
    const [loading, setLoading] = useState(false);
    const [running, setRunning] = useState(false);
    const [progress, setProgress] = useState(0);
    const [result, setResult] = useState(null);

    // 전략 목록 로드
    useEffect(() => {
        loadStrategies();
    }, []);

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
                strategy_type: selectedStrategy?.type || 'TREND_FOLLOWING',
                strategy_params: selectedStrategy?.parameters || {},
            };

            // 백테스트 시작
            const startResponse = await backtestAPI.runBacktest(backtestRequest);
            const resultId = startResponse.backtest_result_id;

            // 진행률 폴링
            let attempts = 0;
            const maxAttempts = 120;

            const pollInterval = setInterval(async () => {
                attempts++;
                setProgress(Math.min((attempts / maxAttempts) * 100, 95));

                try {
                    const resultResponse = await backtestAPI.getResult(resultId);

                    if (resultResponse.status === 'completed') {
                        clearInterval(pollInterval);
                        setProgress(100);
                        setResult(resultResponse);
                        setRunning(false);
                        message.success('백테스트가 완료되었습니다!');
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
            message.error(error.response?.data?.detail || '백테스트 시작 실패');
            setRunning(false);
        }
    };

    return (
        <div style={{ padding: 24 }}>
            <Title level={2}>
                <ExperimentOutlined style={{ marginRight: 12 }} />
                백테스트 실행
            </Title>
            <Text type="secondary" style={{ marginBottom: 24, display: 'block' }}>
                과거 데이터로 전략의 성과를 테스트해보세요
            </Text>

            <Row gutter={24}>
                {/* 설정 패널 */}
                <Col xs={24} lg={10}>
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
                                label="전략 선택"
                                rules={[{ required: true, message: '전략을 선택하세요' }]}
                            >
                                <Select
                                    placeholder="전략을 선택하세요"
                                    loading={loading}
                                    size="large"
                                >
                                    {strategies.map(s => (
                                        <Option key={s.id} value={s.id}>
                                            {s.name}
                                        </Option>
                                    ))}
                                </Select>
                            </Form.Item>

                            <Form.Item
                                name="symbol"
                                label="거래 코인"
                                rules={[{ required: true }]}
                            >
                                <Select size="large">
                                    <Option value="BTCUSDT">🟡 BTC/USDT</Option>
                                    <Option value="ETHUSDT">🔷 ETH/USDT</Option>
                                    <Option value="XRPUSDT">⚪ XRP/USDT</Option>
                                    <Option value="SOLUSDT">🟣 SOL/USDT</Option>
                                </Select>
                            </Form.Item>

                            <Form.Item
                                name="timeframe"
                                label="시간봉"
                                rules={[{ required: true }]}
                            >
                                <Select size="large">
                                    <Option value="15m">15분</Option>
                                    <Option value="1h">1시간</Option>
                                    <Option value="4h">4시간</Option>
                                    <Option value="1d">1일</Option>
                                </Select>
                            </Form.Item>

                            <Form.Item
                                name="initial_balance"
                                label="초기 자금 (USDT)"
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

                {/* 결과 패널 */}
                <Col xs={24} lg={14}>
                    {result ? (
                        <Card title="📊 백테스트 결과">
                            <Row gutter={[16, 16]}>
                                <Col span={8}>
                                    <Statistic
                                        title="총 수익률"
                                        value={result.total_return || 0}
                                        precision={2}
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
                                        value={result.final_balance || 0}
                                        precision={2}
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
                                        value={result.win_rate || 0}
                                        precision={1}
                                        suffix="%"
                                        valueStyle={{
                                            color: (result.win_rate || 0) >= 50 ? '#3f8600' : '#cf1322'
                                        }}
                                    />
                                </Col>
                                <Col span={8}>
                                    <Statistic
                                        title="최대 손실"
                                        value={result.max_drawdown || 0}
                                        precision={2}
                                        suffix="%"
                                        valueStyle={{ color: '#cf1322' }}
                                        prefix={<WarningOutlined />}
                                    />
                                </Col>
                                <Col span={8}>
                                    <Statistic
                                        title="Profit Factor"
                                        value={result.profit_factor || 0}
                                        precision={2}
                                    />
                                </Col>
                            </Row>

                            {result.trades && result.trades.length > 0 && (
                                <div style={{ marginTop: 24 }}>
                                    <Title level={5}>최근 거래 내역</Title>
                                    <Table
                                        dataSource={result.trades.slice(0, 10)}
                                        columns={[
                                            {
                                                title: '타입', dataIndex: 'side', render: v => (
                                                    <Tag color={v === 'buy' ? 'green' : 'red'}>{v}</Tag>
                                                )
                                            },
                                            { title: '진입가', dataIndex: 'entry', render: v => `$${v?.toFixed(2)}` },
                                            { title: '청산가', dataIndex: 'exit', render: v => `$${v?.toFixed(2)}` },
                                            {
                                                title: '손익', dataIndex: 'pnl', render: v => (
                                                    <span style={{ color: v >= 0 ? '#3f8600' : '#cf1322' }}>
                                                        {v >= 0 ? '+' : ''}{v?.toFixed(2)}
                                                    </span>
                                                )
                                            },
                                        ]}
                                        size="small"
                                        pagination={false}
                                        rowKey={(_, idx) => idx}
                                    />
                                </div>
                            )}
                        </Card>
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

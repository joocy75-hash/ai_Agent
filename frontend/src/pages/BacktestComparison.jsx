import { useState, useEffect } from 'react';
import { Card, Table, Button, Select, DatePicker, Row, Col, Statistic, Spin, message, Typography, Space, Tag, Tooltip } from 'antd';
import {
    LineChartOutlined,
    BarChartOutlined,
    SwapOutlined,
    ReloadOutlined,
    TrophyOutlined,
    RiseOutlined,
    FallOutlined,
    DollarOutlined,
} from '@ant-design/icons';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer } from 'recharts';
import backtestAPI from '../api/backtest';
import dayjs from 'dayjs';

const { Title } = Typography;
const { RangePicker } = DatePicker;
const { Option } = Select;

export default function BacktestComparison() {
    const [backtests, setBacktests] = useState([]);
    const [selectedBacktests, setSelectedBacktests] = useState([]);
    const [comparisonData, setComparisonData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [dateRange, setDateRange] = useState([dayjs().subtract(30, 'days'), dayjs()]);

    useEffect(() => {
        loadBacktests();
    }, []);

    const loadBacktests = async () => {
        setLoading(true);
        try {
            const data = await backtestAPI.getAllBacktests();
            setBacktests(data.backtests || []);
        } catch (error) {
            console.error('Failed to load backtests:', error);
            message.error('백테스트 목록을 불러오는데 실패했습니다');
        } finally {
            setLoading(false);
        }
    };

    const handleCompare = async () => {
        if (selectedBacktests.length < 2) {
            message.warning('비교할 백테스트를 최소 2개 선택해주세요');
            return;
        }

        setLoading(true);
        try {
            const results = await Promise.all(
                selectedBacktests.map(id => backtestAPI.getBacktestResult(id))
            );

            const comparison = processComparisonData(results);
            setComparisonData(comparison);
        } catch (error) {
            console.error('Failed to compare backtests:', error);
            message.error('백테스트 비교에 실패했습니다');
        } finally {
            setLoading(false);
        }
    };

    const processComparisonData = (results) => {
        // Extract metrics from each backtest
        const comparison = {
            backtests: results.map((result, index) => {
                const config = result.config || {};
                const metrics = result.metrics || {};

                return {
                    id: result.id,
                    name: `백테스트 ${index + 1}`,
                    symbol: config.symbol || 'N/A',
                    strategy: config.strategy_type || 'N/A',
                    totalReturn: metrics.total_return || 0,
                    winRate: metrics.win_rate || 0,
                    sharpeRatio: metrics.sharpe_ratio || 0,
                    maxDrawdown: metrics.max_drawdown || 0,
                    totalTrades: metrics.total_trades || 0,
                    profitFactor: metrics.profit_factor || 0,
                    avgProfit: metrics.avg_profit || 0,
                    avgLoss: metrics.avg_loss || 0,
                };
            }),
            equityCurves: results.map((result, index) => ({
                name: `백테스트 ${index + 1}`,
                data: result.equity_curve || [],
            })),
        };

        return comparison;
    };

    const columns = [
        {
            title: '지표',
            dataIndex: 'metric',
            key: 'metric',
            fixed: 'left',
            width: 150,
            render: (text) => <strong>{text}</strong>,
        },
        ...selectedBacktests.map((id, index) => ({
            title: `백테스트 ${index + 1}`,
            dataIndex: `backtest_${index}`,
            key: `backtest_${index}`,
            width: 150,
            render: (value, record) => {
                if (record.type === 'percentage') {
                    const isPositive = parseFloat(value) > 0;
                    return (
                        <span style={{ color: isPositive ? '#52c41a' : '#f5222d' }}>
                            {isPositive ? <RiseOutlined /> : <FallOutlined />} {value}%
                        </span>
                    );
                }
                if (record.type === 'currency') {
                    return `$${parseFloat(value).toFixed(2)}`;
                }
                return value;
            },
        })),
    ];

    const getComparisonTableData = () => {
        if (!comparisonData) return [];

        const metrics = [
            { key: 'symbol', label: '심볼', type: 'text' },
            { key: 'strategy', label: '전략', type: 'text' },
            { key: 'totalReturn', label: '총 수익률', type: 'percentage' },
            { key: 'winRate', label: '승률', type: 'percentage' },
            { key: 'sharpeRatio', label: 'Sharpe Ratio', type: 'number' },
            { key: 'maxDrawdown', label: '최대 낙폭', type: 'percentage' },
            { key: 'totalTrades', label: '총 거래 수', type: 'number' },
            { key: 'profitFactor', label: 'Profit Factor', type: 'number' },
            { key: 'avgProfit', label: '평균 수익', type: 'currency' },
            { key: 'avgLoss', label: '평균 손실', type: 'currency' },
        ];

        return metrics.map(metric => {
            const row = {
                key: metric.key,
                metric: metric.label,
                type: metric.type,
            };

            comparisonData.backtests.forEach((backtest, index) => {
                row[`backtest_${index}`] = backtest[metric.key];
            });

            return row;
        });
    };

    const getEquityCurveData = () => {
        if (!comparisonData || !comparisonData.equityCurves) return [];

        // Find the maximum length
        const maxLength = Math.max(
            ...comparisonData.equityCurves.map(curve => curve.data.length)
        );

        // Merge all equity curves into one dataset
        const mergedData = [];
        for (let i = 0; i < maxLength; i++) {
            const point = { index: i };
            comparisonData.equityCurves.forEach((curve, curveIndex) => {
                if (curve.data[i]) {
                    point[`backtest_${curveIndex}`] = curve.data[i].equity || 0;
                }
            });
            mergedData.push(point);
        }

        return mergedData;
    };

    const getReturnsComparisonData = () => {
        if (!comparisonData) return [];

        return comparisonData.backtests.map((backtest, index) => ({
            name: `백테스트 ${index + 1}`,
            return: backtest.totalReturn,
        }));
    };

    const getBestBacktest = () => {
        if (!comparisonData || comparisonData.backtests.length === 0) return null;

        // Find backtest with highest Sharpe ratio
        return comparisonData.backtests.reduce((best, current) => {
            return current.sharpeRatio > best.sharpeRatio ? current : best;
        });
    };

    return (
        <div style={{ padding: 24 }}>
            {/* 페이지 헤더 */}
            <div style={{ marginBottom: 24 }}>
                <Title level={2}>
                    <SwapOutlined style={{ marginRight: 12 }} />
                    백테스트 비교
                </Title>
                <p style={{ color: '#888', margin: 0 }}>
                    여러 백테스트 결과를 비교하고 최적의 전략을 찾아보세요
                </p>
            </div>

            {/* 백테스트 선택 */}
            <Card style={{ marginBottom: 24 }}>
                <Space direction="vertical" style={{ width: '100%' }} size="large">
                    <div>
                        <label style={{ display: 'block', marginBottom: 8, fontWeight: 'bold' }}>
                            비교할 백테스트 선택 (최소 2개)
                        </label>
                        <Select
                            mode="multiple"
                            style={{ width: '100%' }}
                            placeholder="백테스트를 선택하세요"
                            value={selectedBacktests}
                            onChange={setSelectedBacktests}
                            maxTagCount="responsive"
                        >
                            {backtests.map(backtest => (
                                <Option key={backtest.id} value={backtest.id}>
                                    {backtest.config?.symbol || 'N/A'} - {backtest.config?.strategy_type || 'N/A'} ({new Date(backtest.created_at).toLocaleDateString('ko-KR')})
                                </Option>
                            ))}
                        </Select>
                    </div>

                    <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
                        <Button icon={<ReloadOutlined />} onClick={loadBacktests}>
                            새로고침
                        </Button>
                        <Button
                            type="primary"
                            icon={<SwapOutlined />}
                            onClick={handleCompare}
                            disabled={selectedBacktests.length < 2}
                            loading={loading}
                        >
                            비교하기
                        </Button>
                    </div>
                </Space>
            </Card>

            {/* 최우수 전략 */}
            {comparisonData && getBestBacktest() && (
                <Card
                    style={{
                        marginBottom: 24,
                        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                        color: '#fff',
                    }}
                >
                    <Row gutter={[16, 16]} align="middle">
                        <Col span={4}>
                            <TrophyOutlined style={{ fontSize: 64, color: '#ffd700' }} />
                        </Col>
                        <Col span={20}>
                            <Title level={3} style={{ color: '#fff', marginBottom: 8 }}>
                                최우수 전략
                            </Title>
                            <Row gutter={[16, 16]}>
                                <Col span={6}>
                                    <Statistic
                                        title={<span style={{ color: '#fff' }}>심볼</span>}
                                        value={getBestBacktest().symbol}
                                        valueStyle={{ color: '#fff' }}
                                    />
                                </Col>
                                <Col span={6}>
                                    <Statistic
                                        title={<span style={{ color: '#fff' }}>전략</span>}
                                        value={getBestBacktest().strategy}
                                        valueStyle={{ color: '#fff' }}
                                    />
                                </Col>
                                <Col span={6}>
                                    <Statistic
                                        title={<span style={{ color: '#fff' }}>Sharpe Ratio</span>}
                                        value={getBestBacktest().sharpeRatio}
                                        precision={2}
                                        valueStyle={{ color: '#ffd700' }}
                                    />
                                </Col>
                                <Col span={6}>
                                    <Statistic
                                        title={<span style={{ color: '#fff' }}>총 수익률</span>}
                                        value={getBestBacktest().totalReturn}
                                        precision={2}
                                        suffix="%"
                                        valueStyle={{ color: '#52c41a' }}
                                    />
                                </Col>
                            </Row>
                        </Col>
                    </Row>
                </Card>
            )}

            {/* 비교 결과 */}
            {loading && (
                <Card>
                    <div style={{ textAlign: 'center', padding: 60 }}>
                        <Spin size="large" />
                        <p style={{ marginTop: 16, color: '#888' }}>비교 중...</p>
                    </div>
                </Card>
            )}

            {!loading && comparisonData && (
                <>
                    {/* 수익 곡선 비교 */}
                    <Card title="수익 곡선 비교" style={{ marginBottom: 24 }}>
                        <ResponsiveContainer width="100%" height={400}>
                            <LineChart data={getEquityCurveData()}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="index" label={{ value: '거래 횟수', position: 'insideBottom', offset: -5 }} />
                                <YAxis label={{ value: '자본 ($)', angle: -90, position: 'insideLeft' }} />
                                <RechartsTooltip />
                                <Legend />
                                {comparisonData.backtests.map((_, index) => (
                                    <Line
                                        key={index}
                                        type="monotone"
                                        dataKey={`backtest_${index}`}
                                        name={`백테스트 ${index + 1}`}
                                        stroke={['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1'][index % 5]}
                                        strokeWidth={2}
                                        dot={false}
                                    />
                                ))}
                            </LineChart>
                        </ResponsiveContainer>
                    </Card>

                    {/* 수익률 비교 차트 */}
                    <Card title="총 수익률 비교" style={{ marginBottom: 24 }}>
                        <ResponsiveContainer width="100%" height={300}>
                            <BarChart data={getReturnsComparisonData()}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="name" />
                                <YAxis label={{ value: '수익률 (%)', angle: -90, position: 'insideLeft' }} />
                                <RechartsTooltip />
                                <Bar dataKey="return" fill="#1890ff" />
                            </BarChart>
                        </ResponsiveContainer>
                    </Card>

                    {/* 상세 비교 테이블 */}
                    <Card title="상세 지표 비교">
                        <Table
                            columns={columns}
                            dataSource={getComparisonTableData()}
                            pagination={false}
                            scroll={{ x: 800 }}
                            bordered
                        />
                    </Card>
                </>
            )}

            {!loading && !comparisonData && (
                <Card>
                    <div style={{ textAlign: 'center', padding: 60, color: '#888' }}>
                        <SwapOutlined style={{ fontSize: 64, marginBottom: 16 }} />
                        <p>백테스트를 선택하고 비교하기 버튼을 눌러주세요</p>
                    </div>
                </Card>
            )}
        </div>
    );
}

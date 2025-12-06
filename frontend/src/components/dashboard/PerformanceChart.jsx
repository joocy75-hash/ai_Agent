import { useEffect, useState } from 'react';
import { Card, Select, Row, Col, Statistic } from 'antd';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
    Area,
    AreaChart,
} from 'recharts';
import {
    RiseOutlined,
    FallOutlined,
    LineChartOutlined,
} from '@ant-design/icons';
import { analyticsAPI } from '../../api/analytics';

const { Option } = Select;

export default function PerformanceChart() {
    const [data, setData] = useState([]);
    const [period, setPeriod] = useState('1m');
    const [loading, setLoading] = useState(true);
    const [stats, setStats] = useState({
        totalReturn: 0,
        dailyReturn: 0,
        maxValue: 0,
        minValue: 0,
    });

    useEffect(() => {
        loadData();
    }, [period]);

    const loadData = async () => {
        setLoading(true);
        try {
            // Mock 데이터 생성 (백엔드 API 구현 전까지)
            const mockData = generateMockData(period);
            setData(mockData);
            calculateStats(mockData);
            setLoading(false);

            // 실제 API 호출 (주석 처리)
            // const response = await analyticsAPI.getEquityCurve(period);
            // setData(response.data);
            // calculateStats(response.data);
        } catch (error) {
            console.error('[PerformanceChart] Error loading data:', error);
            setLoading(false);
        }
    };

    const generateMockData = (period) => {
        const dataPoints = {
            '1d': 24,
            '1w': 7,
            '1m': 30,
            '3m': 90,
            '1y': 365,
            'all': 365,
        };

        const points = dataPoints[period] || 30;
        const data = [];
        let baseValue = 0; // 가상 데이터를 0으로 변경

        for (let i = 0; i < points; i++) {
            const date = new Date();
            date.setDate(date.getDate() - (points - i));

            data.push({
                date: date.toISOString().split('T')[0],
                equity: 0, // 가상 데이터를 0으로 변경
                benchmark: 0, // 가상 데이터를 0으로 변경
            });
        }

        return data;
    };

    const calculateStats = (data) => {
        if (!data || data.length === 0) return;

        const firstValue = data[0].equity;
        const lastValue = data[data.length - 1].equity;
        const maxValue = Math.max(...data.map(d => d.equity));
        const minValue = Math.min(...data.map(d => d.equity));

        const totalReturn = ((lastValue - firstValue) / firstValue) * 100;

        // 일일 수익률 (최근 2일 비교)
        const dailyReturn = data.length > 1
            ? ((data[data.length - 1].equity - data[data.length - 2].equity) / data[data.length - 2].equity) * 100
            : 0;

        setStats({
            totalReturn,
            dailyReturn,
            maxValue,
            minValue,
        });
    };

    const CustomTooltip = ({ active, payload }) => {
        if (active && payload && payload.length) {
            return (
                <div
                    style={{
                        background: 'rgba(255, 255, 255, 0.95)',
                        border: '1px solid #d9d9d9',
                        borderRadius: 4,
                        padding: 12,
                        boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                    }}
                >
                    <div style={{ marginBottom: 8, fontWeight: 'bold' }}>
                        {payload[0].payload.date}
                    </div>
                    {payload.map((entry, index) => (
                        <div
                            key={index}
                            style={{
                                color: entry.color,
                                fontSize: 14,
                                marginBottom: 4,
                            }}
                        >
                            {entry.name}: ${entry.value.toFixed(2)}
                        </div>
                    ))}
                </div>
            );
        }
        return null;
    };

    return (
        <Card
            title={
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>
                        <LineChartOutlined style={{ marginRight: 8 }} />
                        성과 추이
                    </span>
                    <Select
                        value={period}
                        onChange={setPeriod}
                        style={{ width: 120 }}
                        size="small"
                    >
                        <Option value="1d">1일</Option>
                        <Option value="1w">1주</Option>
                        <Option value="1m">1개월</Option>
                        <Option value="3m">3개월</Option>
                        <Option value="1y">1년</Option>
                        <Option value="all">전체</Option>
                    </Select>
                </div>
            }
            loading={loading}
        >
            {/* 통계 요약 */}
            <Row gutter={16} style={{ marginBottom: 24 }}>
                <Col span={8}>
                    <Statistic
                        title="총 수익률"
                        value={stats.totalReturn}
                        precision={2}
                        suffix="%"
                        valueStyle={{
                            color: stats.totalReturn >= 0 ? '#3f8600' : '#cf1322',
                            fontSize: 20,
                        }}
                        prefix={stats.totalReturn >= 0 ? <RiseOutlined /> : <FallOutlined />}
                    />
                </Col>
                <Col span={8}>
                    <Statistic
                        title="일일 수익률"
                        value={stats.dailyReturn}
                        precision={2}
                        suffix="%"
                        valueStyle={{
                            color: stats.dailyReturn >= 0 ? '#3f8600' : '#cf1322',
                            fontSize: 20,
                        }}
                        prefix={stats.dailyReturn >= 0 ? <RiseOutlined /> : <FallOutlined />}
                    />
                </Col>
                <Col span={8}>
                    <Statistic
                        title="현재 자산"
                        value={data.length > 0 ? data[data.length - 1].equity : 0}
                        precision={2}
                        prefix="$"
                        valueStyle={{ fontSize: 20 }}
                    />
                </Col>
            </Row>

            {/* 차트 */}
            <ResponsiveContainer width="100%" height={400}>
                <AreaChart
                    data={data}
                    margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
                >
                    <defs>
                        <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#1890ff" stopOpacity={0.8} />
                            <stop offset="95%" stopColor="#1890ff" stopOpacity={0.1} />
                        </linearGradient>
                        <linearGradient id="colorBenchmark" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#52c41a" stopOpacity={0.8} />
                            <stop offset="95%" stopColor="#52c41a" stopOpacity={0.1} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis
                        dataKey="date"
                        tick={{ fontSize: 12 }}
                        tickFormatter={(value) => {
                            const date = new Date(value);
                            return `${date.getMonth() + 1}/${date.getDate()}`;
                        }}
                    />
                    <YAxis
                        tick={{ fontSize: 12 }}
                        tickFormatter={(value) => `$${value}`}
                        domain={['dataMin - 50', 'dataMax + 50']}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend
                        wrapperStyle={{ paddingTop: 20 }}
                        iconType="line"
                    />
                    <Area
                        type="monotone"
                        dataKey="equity"
                        stroke="#1890ff"
                        strokeWidth={2}
                        fillOpacity={1}
                        fill="url(#colorEquity)"
                        name="내 자산"
                    />
                    <Area
                        type="monotone"
                        dataKey="benchmark"
                        stroke="#52c41a"
                        strokeWidth={2}
                        fillOpacity={1}
                        fill="url(#colorBenchmark)"
                        name="BTC 보유"
                        strokeDasharray="5 5"
                    />
                </AreaChart>
            </ResponsiveContainer>

            {/* 범례 설명 */}
            <div style={{ marginTop: 16, fontSize: 12, color: '#888', textAlign: 'center' }}>
                <span style={{ marginRight: 16 }}>
                    <span style={{ color: '#1890ff', fontWeight: 'bold' }}>━━</span> 내 자산 (전략 수익)
                </span>
                <span>
                    <span style={{ color: '#52c41a', fontWeight: 'bold' }}>┉┉</span> BTC 보유 (벤치마크)
                </span>
            </div>
        </Card>
    );
}

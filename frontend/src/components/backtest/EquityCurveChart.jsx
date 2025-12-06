import { useMemo } from 'react';
import { Card, Empty, Spin, Row, Col, Statistic, Typography, Space, Tag } from 'antd';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, Area, AreaChart, ReferenceLine
} from 'recharts';
import {
    RiseOutlined, FallOutlined, DollarOutlined, PercentageOutlined,
    TrophyOutlined, WarningOutlined, LineChartOutlined, AreaChartOutlined
} from '@ant-design/icons';

const { Title, Text } = Typography;

/**
 * 백테스트 에쿼티 커브 차트 컴포넌트
 * @param {Object} props
 * @param {number[]} props.equityCurve - 잔고 배열 (equity curve)
 * @param {number} props.initialBalance - 초기 자본
 * @param {Object} props.metrics - 백테스트 메트릭 (선택)
 * @param {Array} props.trades - 거래 내역 (선택)
 * @param {boolean} props.loading - 로딩 상태
 * @param {boolean} props.showStats - 통계 표시 여부 (기본: true)
 * @param {number} props.height - 차트 높이 (기본: 400)
 * @param {boolean} props.isMobile - 모바일 여부
 */
export default function EquityCurveChart({
    equityCurve = [],
    initialBalance = 10000,
    metrics = {},
    trades = [],
    loading = false,
    showStats = true,
    height = 400,
    isMobile = false,
}) {
    // 차트 데이터 변환
    const chartData = useMemo(() => {
        if (!equityCurve || equityCurve.length === 0) return [];

        return equityCurve.map((balance, index) => {
            const returnPct = ((balance - initialBalance) / initialBalance) * 100;
            const drawdown = calculateDrawdownAtPoint(equityCurve.slice(0, index + 1));

            return {
                index,
                balance: Number(balance.toFixed(2)),
                return: Number(returnPct.toFixed(2)),
                drawdown: Number(drawdown.toFixed(2)),
                label: `#${index + 1}`,
            };
        });
    }, [equityCurve, initialBalance]);

    // 드로다운 계산
    function calculateDrawdownAtPoint(curve) {
        if (curve.length === 0) return 0;
        let peak = curve[0];
        let currentValue = curve[curve.length - 1];

        for (const value of curve) {
            if (value > peak) peak = value;
        }

        if (peak === 0) return 0;
        return ((currentValue - peak) / peak) * 100;
    }

    // 통계 계산
    const stats = useMemo(() => {
        if (!equityCurve || equityCurve.length === 0) {
            return {
                finalBalance: initialBalance,
                totalReturn: 0,
                maxDrawdown: 0,
                winRate: 0,
                profitFactor: 0,
                sharpeRatio: 0,
                totalTrades: 0,
            };
        }

        const finalBalance = equityCurve[equityCurve.length - 1];
        const totalReturn = ((finalBalance - initialBalance) / initialBalance) * 100;

        // 최대 드로다운 계산
        let peak = equityCurve[0];
        let maxDrawdown = 0;
        for (const balance of equityCurve) {
            if (balance > peak) peak = balance;
            const drawdown = ((balance - peak) / peak) * 100;
            if (drawdown < maxDrawdown) maxDrawdown = drawdown;
        }

        return {
            finalBalance: Number(finalBalance.toFixed(2)),
            totalReturn: Number(totalReturn.toFixed(2)),
            maxDrawdown: Number(maxDrawdown.toFixed(2)),
            winRate: metrics.win_rate || 0,
            profitFactor: metrics.profit_factor || 0,
            sharpeRatio: metrics.sharpe_ratio || 0,
            totalTrades: metrics.total_trades || trades.length || 0,
        };
    }, [equityCurve, initialBalance, metrics, trades]);

    // 커스텀 툴팁
    const CustomTooltip = ({ active, payload, label }) => {
        if (!active || !payload || !payload.length) return null;

        const data = payload[0].payload;
        return (
            <div style={{
                background: 'rgba(255, 255, 255, 0.95)',
                border: '1px solid #e5e7eb',
                borderRadius: 8,
                padding: '12px 16px',
                boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
            }}>
                <Text strong style={{ display: 'block', marginBottom: 8 }}>
                    포인트 {data.index + 1}
                </Text>
                <div style={{ marginBottom: 4 }}>
                    <Text type="secondary">잔고: </Text>
                    <Text strong style={{ color: '#1890ff' }}>
                        ${data.balance.toLocaleString()}
                    </Text>
                </div>
                <div style={{ marginBottom: 4 }}>
                    <Text type="secondary">수익률: </Text>
                    <Text strong style={{ color: data.return >= 0 ? '#52c41a' : '#f5222d' }}>
                        {data.return >= 0 ? '+' : ''}{data.return}%
                    </Text>
                </div>
                <div>
                    <Text type="secondary">드로다운: </Text>
                    <Text strong style={{ color: data.drawdown < -10 ? '#f5222d' : '#faad14' }}>
                        {data.drawdown.toFixed(2)}%
                    </Text>
                </div>
            </div>
        );
    };

    // 차트 그라데이션 색상
    const isProfit = stats.totalReturn >= 0;
    const gradientColor = isProfit ? '#52c41a' : '#f5222d';
    const gradientColorLight = isProfit ? 'rgba(82, 196, 26, 0.2)' : 'rgba(245, 34, 45, 0.2)';

    if (loading) {
        return (
            <Card>
                <div style={{ textAlign: 'center', padding: 60 }}>
                    <Spin size="large" />
                    <p style={{ marginTop: 16, color: '#666' }}>차트 데이터 로딩 중...</p>
                </div>
            </Card>
        );
    }

    if (!equityCurve || equityCurve.length === 0) {
        return (
            <Card>
                <Empty
                    description="에쿼티 커브 데이터가 없습니다"
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                />
            </Card>
        );
    }

    return (
        <Card
            title={
                <Space>
                    <AreaChartOutlined style={{ color: '#1890ff' }} />
                    <span>에쿼티 커브</span>
                    <Tag color={isProfit ? 'success' : 'error'}>
                        {isProfit ? '수익' : '손실'}
                    </Tag>
                </Space>
            }
            extra={
                <Text type="secondary" style={{ fontSize: 12 }}>
                    {equityCurve.length}개 데이터 포인트
                </Text>
            }
        >
            {/* 통계 요약 */}
            {showStats && (
                <Row gutter={[isMobile ? 8 : 16, isMobile ? 8 : 16]} style={{ marginBottom: 24 }}>
                    <Col xs={12} sm={8} md={4}>
                        <Statistic
                            title={<span style={{ fontSize: isMobile ? 10 : 12 }}>최종 잔고</span>}
                            value={stats.finalBalance}
                            prefix="$"
                            valueStyle={{
                                fontSize: isMobile ? 16 : 20,
                                fontWeight: 600,
                                color: isProfit ? '#52c41a' : '#f5222d'
                            }}
                        />
                    </Col>
                    <Col xs={12} sm={8} md={4}>
                        <Statistic
                            title={<span style={{ fontSize: isMobile ? 10 : 12 }}>총 수익률</span>}
                            value={stats.totalReturn}
                            prefix={isProfit ? <RiseOutlined /> : <FallOutlined />}
                            suffix="%"
                            valueStyle={{
                                fontSize: isMobile ? 16 : 20,
                                fontWeight: 600,
                                color: isProfit ? '#52c41a' : '#f5222d'
                            }}
                        />
                    </Col>
                    <Col xs={12} sm={8} md={4}>
                        <Statistic
                            title={<span style={{ fontSize: isMobile ? 10 : 12 }}>최대 드로다운</span>}
                            value={Math.abs(stats.maxDrawdown)}
                            prefix={<WarningOutlined />}
                            suffix="%"
                            valueStyle={{
                                fontSize: isMobile ? 16 : 20,
                                fontWeight: 600,
                                color: stats.maxDrawdown < -20 ? '#f5222d' : '#faad14'
                            }}
                        />
                    </Col>
                    <Col xs={12} sm={8} md={4}>
                        <Statistic
                            title={<span style={{ fontSize: isMobile ? 10 : 12 }}>승률</span>}
                            value={stats.winRate}
                            prefix={<TrophyOutlined />}
                            suffix="%"
                            valueStyle={{
                                fontSize: isMobile ? 16 : 20,
                                fontWeight: 600,
                                color: stats.winRate >= 50 ? '#52c41a' : '#faad14'
                            }}
                        />
                    </Col>
                    <Col xs={12} sm={8} md={4}>
                        <Statistic
                            title={<span style={{ fontSize: isMobile ? 10 : 12 }}>Profit Factor</span>}
                            value={stats.profitFactor}
                            valueStyle={{
                                fontSize: isMobile ? 16 : 20,
                                fontWeight: 600,
                                color: stats.profitFactor >= 1.5 ? '#52c41a' : stats.profitFactor >= 1 ? '#faad14' : '#f5222d'
                            }}
                        />
                    </Col>
                    <Col xs={12} sm={8} md={4}>
                        <Statistic
                            title={<span style={{ fontSize: isMobile ? 10 : 12 }}>총 거래</span>}
                            value={stats.totalTrades}
                            suffix="회"
                            valueStyle={{
                                fontSize: isMobile ? 16 : 20,
                                fontWeight: 600,
                            }}
                        />
                    </Col>
                </Row>
            )}

            {/* 에쿼티 커브 차트 */}
            <div style={{ height: isMobile ? 250 : height }}>
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                        <defs>
                            <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor={gradientColor} stopOpacity={0.3} />
                                <stop offset="95%" stopColor={gradientColor} stopOpacity={0.05} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis
                            dataKey="index"
                            tick={{ fontSize: 11 }}
                            tickFormatter={(value) => `${value}`}
                            interval="preserveStartEnd"
                        />
                        <YAxis
                            tick={{ fontSize: 11 }}
                            tickFormatter={(value) => `$${(value / 1000).toFixed(1)}k`}
                            domain={['auto', 'auto']}
                        />
                        <Tooltip content={<CustomTooltip />} />
                        <ReferenceLine
                            y={initialBalance}
                            stroke="#999"
                            strokeDasharray="5 5"
                            label={{
                                value: '초기 자본',
                                position: 'right',
                                fontSize: 11,
                                fill: '#666'
                            }}
                        />
                        <Area
                            type="monotone"
                            dataKey="balance"
                            stroke={gradientColor}
                            strokeWidth={2}
                            fill="url(#equityGradient)"
                            dot={false}
                            activeDot={{ r: 4, strokeWidth: 2 }}
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>

            {/* 드로다운 차트 */}
            <div style={{ marginTop: 24 }}>
                <Title level={5} style={{ marginBottom: 16 }}>
                    <WarningOutlined style={{ marginRight: 8, color: '#faad14' }} />
                    드로다운
                </Title>
                <div style={{ height: isMobile ? 150 : 200 }}>
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                            <defs>
                                <linearGradient id="drawdownGradient" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#f5222d" stopOpacity={0.3} />
                                    <stop offset="95%" stopColor="#f5222d" stopOpacity={0.05} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                            <XAxis
                                dataKey="index"
                                tick={{ fontSize: 10 }}
                                interval="preserveStartEnd"
                            />
                            <YAxis
                                tick={{ fontSize: 10 }}
                                tickFormatter={(value) => `${value}%`}
                                domain={['auto', 0]}
                            />
                            <Tooltip
                                formatter={(value) => [`${value}%`, '드로다운']}
                                contentStyle={{
                                    background: 'rgba(255, 255, 255, 0.95)',
                                    border: '1px solid #e5e7eb',
                                    borderRadius: 8,
                                }}
                            />
                            <ReferenceLine y={0} stroke="#52c41a" strokeWidth={2} />
                            <Area
                                type="monotone"
                                dataKey="drawdown"
                                stroke="#f5222d"
                                strokeWidth={2}
                                fill="url(#drawdownGradient)"
                                dot={false}
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </Card>
    );
}

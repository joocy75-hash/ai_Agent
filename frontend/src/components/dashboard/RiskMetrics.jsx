import { useEffect, useState } from 'react';
import { Card, Row, Col, Statistic, Progress } from 'antd';
import {
    FallOutlined,
    RiseOutlined,
    TrophyOutlined,
    ThunderboltOutlined,
    LineChartOutlined,
    PercentageOutlined,
} from '@ant-design/icons';
import { analyticsAPI } from '../../api/analytics';

export default function RiskMetrics() {
    const [metrics, setMetrics] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadMetrics();
        const interval = setInterval(loadMetrics, 30000); // 30초마다 갱신
        return () => clearInterval(interval);
    }, []);

    const loadMetrics = async () => {
        try {
            // Mock 데이터를 0으로 설정 (백엔드 API 구현 전까지)
            const mockData = {
                max_drawdown: 0,
                sharpe_ratio: 0,
                win_rate: 0,
                profit_loss_ratio: 0,
                daily_volatility: 0,
                total_trades: 0,
            };

            setMetrics(mockData);
            setLoading(false);

            // 실제 API 호출 (주석 처리)
            // const data = await analyticsAPI.getRiskMetrics();
            // setMetrics(data);
        } catch (error) {
            console.error('[RiskMetrics] Error loading metrics:', error);
            setLoading(false);
        }
    };

    const getDrawdownColor = (value) => {
        const absValue = Math.abs(value);
        if (absValue < 10) return '#52c41a'; // 녹색
        if (absValue < 20) return '#faad14'; // 노란색
        return '#f5222d'; // 빨간색
    };

    const getSharpeColor = (value) => {
        if (value > 2) return '#52c41a';
        if (value > 1) return '#faad14';
        return '#f5222d';
    };

    const getWinRateColor = (value) => {
        if (value > 60) return '#52c41a';
        if (value > 50) return '#faad14';
        return '#f5222d';
    };

    return (
        <Card title="핵심 리스크 지표" loading={loading}>
            <Row gutter={[16, 16]}>
                {/* MDD (Max Drawdown) */}
                <Col xs={24} sm={12} md={8}>
                    <Card
                        style={{
                            textAlign: 'center',
                            borderLeft: `4px solid ${getDrawdownColor(metrics?.max_drawdown)}`,
                        }}
                    >
                        <FallOutlined
                            style={{
                                fontSize: 32,
                                color: getDrawdownColor(metrics?.max_drawdown),
                                marginBottom: 12,
                            }}
                        />
                        <Statistic
                            title="최대 낙폭 (MDD)"
                            value={Math.abs(metrics?.max_drawdown || 0)}
                            precision={1}
                            suffix="%"
                            valueStyle={{
                                color: getDrawdownColor(metrics?.max_drawdown),
                                fontSize: 28,
                            }}
                            prefix="-"
                        />
                        <Progress
                            percent={Math.min(Math.abs(metrics?.max_drawdown || 0), 100)}
                            strokeColor={getDrawdownColor(metrics?.max_drawdown)}
                            showInfo={false}
                            style={{ marginTop: 12 }}
                        />
                        <div style={{ marginTop: 8, fontSize: 12, color: '#888' }}>
                            {Math.abs(metrics?.max_drawdown || 0) < 10 ? '✅ 안전' :
                                Math.abs(metrics?.max_drawdown || 0) < 20 ? '⚠️ 주의' : '🔴 위험'}
                        </div>
                    </Card>
                </Col>

                {/* Sharpe Ratio */}
                <Col xs={24} sm={12} md={8}>
                    <Card
                        style={{
                            textAlign: 'center',
                            borderLeft: `4px solid ${getSharpeColor(metrics?.sharpe_ratio)}`,
                        }}
                    >
                        <LineChartOutlined
                            style={{
                                fontSize: 32,
                                color: getSharpeColor(metrics?.sharpe_ratio),
                                marginBottom: 12,
                            }}
                        />
                        <Statistic
                            title="샤프 비율"
                            value={metrics?.sharpe_ratio || 0}
                            precision={2}
                            valueStyle={{
                                color: getSharpeColor(metrics?.sharpe_ratio),
                                fontSize: 28,
                            }}
                        />
                        <Progress
                            percent={Math.min((metrics?.sharpe_ratio || 0) * 33.33, 100)}
                            strokeColor={getSharpeColor(metrics?.sharpe_ratio)}
                            showInfo={false}
                            style={{ marginTop: 12 }}
                        />
                        <div style={{ marginTop: 8, fontSize: 12, color: '#888' }}>
                            {(metrics?.sharpe_ratio || 0) > 2 ? '🌟 우수' :
                                (metrics?.sharpe_ratio || 0) > 1 ? '👍 양호' : '📉 개선 필요'}
                        </div>
                    </Card>
                </Col>

                {/* Win Rate */}
                <Col xs={24} sm={12} md={8}>
                    <Card
                        style={{
                            textAlign: 'center',
                            borderLeft: `4px solid ${getWinRateColor(metrics?.win_rate)}`,
                        }}
                    >
                        <TrophyOutlined
                            style={{
                                fontSize: 32,
                                color: getWinRateColor(metrics?.win_rate),
                                marginBottom: 12,
                            }}
                        />
                        <Statistic
                            title="승률"
                            value={metrics?.win_rate || 0}
                            precision={1}
                            suffix="%"
                            valueStyle={{
                                color: getWinRateColor(metrics?.win_rate),
                                fontSize: 28,
                            }}
                        />
                        <Progress
                            percent={metrics?.win_rate || 0}
                            strokeColor={getWinRateColor(metrics?.win_rate)}
                            showInfo={false}
                            style={{ marginTop: 12 }}
                        />
                        <div style={{ marginTop: 8, fontSize: 12, color: '#888' }}>
                            {(metrics?.win_rate || 0) > 60 ? '🎯 높음' :
                                (metrics?.win_rate || 0) > 50 ? '✓ 보통' : '📊 낮음'}
                        </div>
                    </Card>
                </Col>

                {/* Profit/Loss Ratio */}
                <Col xs={24} sm={12} md={8}>
                    <Card style={{ textAlign: 'center' }}>
                        <RiseOutlined
                            style={{ fontSize: 32, color: '#1890ff', marginBottom: 12 }}
                        />
                        <Statistic
                            title="평균 손익비"
                            value={metrics?.profit_loss_ratio || 0}
                            precision={2}
                            valueStyle={{ color: '#1890ff', fontSize: 24 }}
                        />
                        <div style={{ marginTop: 12, fontSize: 12, color: '#888' }}>
                            수익 거래 / 손실 거래 비율
                        </div>
                    </Card>
                </Col>

                {/* Daily Volatility */}
                <Col xs={24} sm={12} md={8}>
                    <Card style={{ textAlign: 'center' }}>
                        <ThunderboltOutlined
                            style={{ fontSize: 32, color: '#faad14', marginBottom: 12 }}
                        />
                        <Statistic
                            title="일일 변동성"
                            value={metrics?.daily_volatility || 0}
                            precision={1}
                            suffix="%"
                            valueStyle={{ color: '#faad14', fontSize: 24 }}
                        />
                        <div style={{ marginTop: 12, fontSize: 12, color: '#888' }}>
                            일일 수익률 표준편차
                        </div>
                    </Card>
                </Col>

                {/* Total Trades */}
                <Col xs={24} sm={12} md={8}>
                    <Card style={{ textAlign: 'center' }}>
                        <PercentageOutlined
                            style={{ fontSize: 32, color: '#52c41a', marginBottom: 12 }}
                        />
                        <Statistic
                            title="총 거래 수"
                            value={metrics?.total_trades || 0}
                            valueStyle={{ color: '#52c41a', fontSize: 24 }}
                        />
                        <div style={{ marginTop: 12, fontSize: 12, color: '#888' }}>
                            전체 기간 거래 횟수
                        </div>
                    </Card>
                </Col>
            </Row>
        </Card>
    );
}

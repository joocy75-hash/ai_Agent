import { useState } from 'react';
import { Card, Form, Select, DatePicker, InputNumber, Button, Space, Progress, Statistic, Row, Col, Divider, Alert, message } from 'antd';
import {
    ThunderboltOutlined,
    PlayCircleOutlined,
    StopOutlined,
    DownloadOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { backtestAPI } from '../../api/backtest';

const { Option } = Select;
const { RangePicker } = DatePicker;

export default function BacktestRunner({ strategies }) {
    const [form] = Form.useForm();
    const [running, setRunning] = useState(false);
    const [progress, setProgress] = useState(0);
    const [result, setResult] = useState(null);
    const [resultId, setResultId] = useState(null);

    const handleRun = async (values) => {
        setRunning(true);
        setProgress(0);
        setResult(null);

        try {
            // 선택된 전략 정보 가져오기
            const selectedStrategy = strategies.find(s => s.id === values.strategyId);
            if (!selectedStrategy) {
                throw new Error('전략을 찾을 수 없습니다');
            }

            // 백테스트 요청 데이터 준비
            const backtestRequest = {
                strategy_id: values.strategyId,
                initial_balance: values.initialBalance,
                start_date: values.dateRange[0].format('YYYY-MM-DD'),
                end_date: values.dateRange[1].format('YYYY-MM-DD'),
            };

            message.info('Bitget API에서 과거 데이터를 가져오는 중...');

            // 백테스트 시작
            const startResponse = await backtestAPI.start(backtestRequest);
            const backtest_result_id = startResponse.result_id;
            setResultId(backtest_result_id);

            message.success('백테스트가 시작되었습니다');

            // 진행률 시뮬레이션 및 결과 폴링
            const checkResult = async () => {
                let attempts = 0;
                const maxAttempts = 120; // 최대 2분 대기

                const interval = setInterval(async () => {
                    attempts++;
                    setProgress(Math.min((attempts / maxAttempts) * 100, 95));

                    try {
                        const resultResponse = await backtestAPI.getResult(backtest_result_id);

                        if (resultResponse.status === 'completed') {
                            clearInterval(interval);
                            setProgress(100);

                            // 결과 변환
                            const metrics = typeof resultResponse.metrics === 'string'
                                ? JSON.parse(resultResponse.metrics)
                                : resultResponse.metrics;

                            const formattedResult = {
                                strategyName: selectedStrategy.name,
                                period: {
                                    start: values.dateRange[0].format('YYYY-MM-DD'),
                                    end: values.dateRange[1].format('YYYY-MM-DD'),
                                },
                                initialBalance: resultResponse.initial_balance,
                                finalBalance: resultResponse.final_balance,
                                totalReturn: metrics.total_return || 0,
                                totalTrades: metrics.total_trades || 0,
                                winningTrades: metrics.winning_trades || 0,
                                losingTrades: metrics.losing_trades || 0,
                                winRate: metrics.win_rate || 0,
                                profitFactor: metrics.profit_factor || 0,
                                sharpeRatio: metrics.sharpe_ratio || 0,
                                maxDrawdown: metrics.max_drawdown || 0,
                                avgProfit: metrics.avg_profit || 0,
                                avgLoss: metrics.avg_loss || 0,
                                bestTrade: metrics.best_trade || 0,
                                worstTrade: metrics.worst_trade || 0,
                                totalFees: metrics.total_fees || 0,
                            };

                            setResult(formattedResult);
                            setRunning(false);
                            message.success('백테스트가 완료되었습니다');
                        } else if (resultResponse.status === 'failed') {
                            clearInterval(interval);
                            setRunning(false);
                            message.error(`백테스트 실패: ${resultResponse.error_message || '알 수 없는 오류'}`);
                        }

                        if (attempts >= maxAttempts) {
                            clearInterval(interval);
                            setRunning(false);
                            message.warning('백테스트가 시간 초과되었습니다. 나중에 결과를 확인해주세요.');
                        }
                    } catch (err) {
                        console.error('결과 조회 오류:', err);
                    }
                }, 1000);
            };

            checkResult();

        } catch (err) {
            console.error('[BacktestRunner] Error:', err);
            message.error(err.response?.data?.detail || err.message || '백테스트 시작에 실패했습니다');
            setRunning(false);
        }
    };

    const handleStop = () => {
        setRunning(false);
        setProgress(0);
        message.info('백테스트가 중지되었습니다');
    };

    const exportResults = () => {
        if (!result) return;

        const csvContent = [
            ['백테스트 결과'],
            ['전략명', result.strategyName],
            ['기간', `${result.period.start} ~ ${result.period.end}`],
            ['초기 자본', result.initialBalance],
            ['최종 자본', result.finalBalance.toFixed(2)],
            ['총 수익률', `${result.totalReturn.toFixed(2)}%`],
            ['총 거래', result.totalTrades],
            ['승률', `${result.winRate.toFixed(2)}%`],
            ['Profit Factor', result.profitFactor.toFixed(2)],
            ['Sharpe Ratio', result.sharpeRatio.toFixed(2)],
            ['MDD', `${result.maxDrawdown.toFixed(2)}%`],
        ].map(row => row.join(',')).join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `backtest-result-${Date.now()}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    };

    return (
        <Card
            title={
                <span>
                    <ThunderboltOutlined style={{ marginRight: 8 }} />
                    백테스트 실행
                </span>
            }
        >
            {/* 백테스트 권장사항 및 제한사항 안내 */}
            <Alert
                message="📊 백테스트 권장사항"
                description={
                    <div style={{ fontSize: '13px' }}>
                        <p style={{ marginBottom: 8 }}><strong>✅ 권장 설정:</strong></p>
                        <ul style={{ margin: 0, paddingLeft: 20 }}>
                            <li><b>타임프레임:</b> 1h, 4h (가장 안정적)</li>
                            <li><b>기간:</b> 최근 30일 이내 (데이터 정확도 높음)</li>
                            <li><b>심볼:</b> BTC, ETH, SOL, XRP, DOGE 등 메이저 코인</li>
                        </ul>
                        <p style={{ marginTop: 12, marginBottom: 8 }}><strong>⚠️ 제한사항:</strong></p>
                        <ul style={{ margin: 0, paddingLeft: 20 }}>
                            <li>Bitget API는 <b>최근 40일</b> 과거 데이터만 제공</li>
                            <li>1분봉은 데이터량이 많아 처리 시간이 길어질 수 있음</li>
                            <li>동시 백테스트 요청 시 Rate Limit 발생 가능</li>
                        </ul>
                        <p style={{ marginTop: 12, marginBottom: 0, color: '#1890ff' }}>
                            💡 <b>팁:</b> 캐시된 데이터가 있으면 즉시 실행됩니다. 첫 요청만 시간이 걸립니다.
                        </p>
                    </div>
                }
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
            />

            <Form
                form={form}
                layout="vertical"
                onFinish={handleRun}
                initialValues={{
                    initialBalance: 10000,
                    dateRange: [dayjs().subtract(1, 'month'), dayjs()],
                }}
            >
                <Row gutter={16}>
                    <Col span={12}>
                        <Form.Item
                            label="전략 선택"
                            name="strategyId"
                            rules={[{ required: true, message: '전략을 선택하세요' }]}
                        >
                            <Select placeholder="백테스트할 전략을 선택하세요">
                                {strategies?.map(strategy => (
                                    <Option key={strategy.id} value={strategy.id}>
                                        {strategy.name}
                                    </Option>
                                ))}
                            </Select>
                        </Form.Item>
                    </Col>
                    <Col span={12}>
                        <Form.Item
                            label="초기 자본 (USDT)"
                            name="initialBalance"
                            rules={[{ required: true, message: '초기 자본을 입력하세요' }]}
                        >
                            <InputNumber
                                min={100}
                                max={1000000}
                                step={100}
                                style={{ width: '100%' }}
                                placeholder="10000"
                            />
                        </Form.Item>
                    </Col>
                    <Col span={24}>
                        <Form.Item
                            label="백테스트 기간"
                            name="dateRange"
                            rules={[{ required: true, message: '기간을 선택하세요' }]}
                        >
                            <RangePicker
                                style={{ width: '100%' }}
                                format="YYYY-MM-DD"
                                placeholder={['시작일', '종료일']}
                                disabledDate={(current) => {
                                    // 오늘 이후 날짜 비활성화
                                    return current && current > dayjs().endOf('day');
                                }}
                            />
                        </Form.Item>
                    </Col>
                </Row>

                <Form.Item>
                    <Space>
                        <Button
                            type="primary"
                            htmlType="submit"
                            icon={<PlayCircleOutlined />}
                            loading={running}
                            disabled={running}
                        >
                            백테스트 시작
                        </Button>
                        {running && (
                            <Button
                                danger
                                icon={<StopOutlined />}
                                onClick={handleStop}
                            >
                                중지
                            </Button>
                        )}
                        {result && (
                            <Button
                                icon={<DownloadOutlined />}
                                onClick={exportResults}
                            >
                                결과 다운로드
                            </Button>
                        )}
                    </Space>
                </Form.Item>
            </Form>

            {running && (
                <div style={{ marginTop: 24 }}>
                    <Alert
                        message="백테스트 실행 중..."
                        description="Bitget API에서 과거 데이터를 가져와 전략을 시뮬레이션하고 있습니다."
                        type="info"
                        showIcon
                        style={{ marginBottom: 16 }}
                    />
                    <Progress percent={Math.floor(progress)} status="active" />
                </div>
            )}

            {result && !running && (
                <div style={{ marginTop: 24 }}>
                    <Divider orientation="left">백테스트 결과</Divider>

                    <Alert
                        message={`총 수익률: ${result.totalReturn >= 0 ? '+' : ''}${result.totalReturn.toFixed(2)}%`}
                        type={result.totalReturn >= 0 ? 'success' : 'error'}
                        showIcon
                        style={{ marginBottom: 16 }}
                    />

                    <Row gutter={[16, 16]}>
                        <Col xs={12} sm={8} md={6}>
                            <Statistic
                                title="초기 자본"
                                value={result.initialBalance}
                                precision={2}
                                prefix="$"
                            />
                        </Col>
                        <Col xs={12} sm={8} md={6}>
                            <Statistic
                                title="최종 자본"
                                value={result.finalBalance}
                                precision={2}
                                prefix="$"
                                valueStyle={{ color: result.finalBalance >= result.initialBalance ? '#3f8600' : '#cf1322' }}
                            />
                        </Col>
                        <Col xs={12} sm={8} md={6}>
                            <Statistic
                                title="총 거래"
                                value={result.totalTrades}
                            />
                        </Col>
                        <Col xs={12} sm={8} md={6}>
                            <Statistic
                                title="승률"
                                value={result.winRate}
                                precision={1}
                                suffix="%"
                            />
                        </Col>
                        <Col xs={12} sm={8} md={6}>
                            <Statistic
                                title="Profit Factor"
                                value={result.profitFactor}
                                precision={2}
                            />
                        </Col>
                        <Col xs={12} sm={8} md={6}>
                            <Statistic
                                title="Sharpe Ratio"
                                value={result.sharpeRatio}
                                precision={2}
                            />
                        </Col>
                        <Col xs={12} sm={8} md={6}>
                            <Statistic
                                title="MDD"
                                value={Math.abs(result.maxDrawdown)}
                                precision={2}
                                suffix="%"
                                prefix="-"
                                valueStyle={{ color: '#cf1322' }}
                            />
                        </Col>
                        <Col xs={12} sm={8} md={6}>
                            <Statistic
                                title="총 수수료"
                                value={result.totalFees}
                                precision={2}
                                prefix="$"
                                valueStyle={{ color: '#cf1322' }}
                            />
                        </Col>
                    </Row>
                </div>
            )}
        </Card>
    );
}

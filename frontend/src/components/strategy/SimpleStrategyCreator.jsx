import { useState } from 'react';
import { Card, Row, Col, Button, InputNumber, Select, Slider, Switch, Divider, Typography, Alert, Steps, message, Tooltip } from 'antd';
import {
    RocketOutlined,
    QuestionCircleOutlined,
    ThunderboltOutlined,
    SafetyCertificateOutlined,
    ArrowUpOutlined,
    ArrowDownOutlined,
    CheckCircleOutlined,
    InfoCircleOutlined,
    LineChartOutlined,
    RiseOutlined,
    FallOutlined,
    BarChartOutlined
} from '@ant-design/icons';
import { strategyAPI } from '../../api/strategy';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { Step } = Steps;

export default function SimpleStrategyCreator({ onStrategyCreated }) {
    const [currentStep, setCurrentStep] = useState(0);
    const [loading, setLoading] = useState(false);

    // 전략 설정
    const [strategyName, setStrategyName] = useState('');
    const [strategyType, setStrategyType] = useState('golden_cross');
    const [symbol, setSymbol] = useState('BTCUSDT');
    const [timeframe, setTimeframe] = useState('1h');

    // 진입 조건
    const [entryCondition, setEntryCondition] = useState('rsi_oversold');
    const [rsiPeriod, setRsiPeriod] = useState(14);
    const [rsiBuy, setRsiBuy] = useState(30);
    const [rsiSell, setRsiSell] = useState(70);
    const [emaShort, setEmaShort] = useState(9);
    const [emaLong, setEmaLong] = useState(21);

    // 리스크 관리
    const [stopLoss, setStopLoss] = useState(2.0);
    const [takeProfit, setTakeProfit] = useState(4.0);
    const [positionSize, setPositionSize] = useState(10);
    const [leverage, setLeverage] = useState(1);

    // 추가 옵션
    const [trailingStop, setTrailingStop] = useState(false);
    const [trailingDistance, setTrailingDistance] = useState(1.0);

    // 전략 유형 설명
    const strategyTypes = {
        golden_cross: {
            name: '골든크로스 전략',
            icon: <RiseOutlined />,
            description: '단기 이동평균선이 장기 이동평균선을 위로 돌파할 때 매수',
            difficulty: '쉬움',
        },
        rsi_reversal: {
            name: 'RSI 반전 전략',
            icon: <FallOutlined />,
            description: 'RSI가 과매도/과매수 구간에서 반전할 때 진입',
            difficulty: '쉬움',
        },
        trend_following: {
            name: '추세추종 전략',
            icon: <LineChartOutlined />,
            description: '강한 추세가 형성되면 해당 방향으로 진입',
            difficulty: '보통',
        },
        breakout: {
            name: '돌파 전략',
            icon: <ThunderboltOutlined />,
            description: '가격이 저항선을 돌파할 때 진입',
            difficulty: '보통',
        }
    };

    // 전략 생성
    const handleCreateStrategy = async () => {
        if (!strategyName.trim()) {
            message.warning('전략 이름을 입력해주세요');
            return;
        }

        setLoading(true);
        try {
            const strategyData = {
                name: strategyName || `${strategyTypes[strategyType].name}_${Date.now()}`,
                description: strategyTypes[strategyType].description,
                type: strategyType,
                symbol: symbol,
                timeframe: timeframe,
                parameters: {
                    // 진입 조건
                    entry_condition: entryCondition,
                    rsi_period: rsiPeriod,
                    rsi_buy: rsiBuy,
                    rsi_sell: rsiSell,
                    ema_short: emaShort,
                    ema_long: emaLong,
                    // 리스크 관리
                    stop_loss: stopLoss,
                    take_profit: takeProfit,
                    position_size: positionSize,
                    leverage: leverage,
                    // 추가 옵션
                    trailing_stop: trailingStop,
                    trailing_distance: trailingDistance
                }
            };

            // API 호출
            const response = await strategyAPI.createStrategy(strategyData);

            message.success('전략이 성공적으로 생성되었습니다.');

            if (onStrategyCreated) {
                onStrategyCreated(response);
            }

            // 초기화
            setCurrentStep(3);

        } catch (error) {
            console.error('Strategy creation error:', error);
            message.error(error.response?.data?.detail || '전략 생성에 실패했습니다');
        } finally {
            setLoading(false);
        }
    };

    // Step 1: 전략 유형 선택
    const renderStep1 = () => (
        <div style={{ padding: '20px 0' }}>
            <Alert
                message="초보자 팁"
                description="처음 시작하신다면 '골든크로스 전략'을 추천드립니다. 가장 이해하기 쉽고 널리 사용되는 전략입니다."
                type="info"
                showIcon
                style={{ marginBottom: 24, background: '#f5f5f7', border: '1px solid #d2d2d7' }}
            />

            <Row gutter={[16, 16]}>
                {Object.entries(strategyTypes).map(([key, strategy]) => (
                    <Col xs={24} sm={12} key={key}>
                        <Card
                            hoverable
                            onClick={() => setStrategyType(key)}
                            style={{
                                borderColor: strategyType === key ? '#1890ff' : '#f0f0f0',
                                borderWidth: strategyType === key ? 2 : 1,
                                background: strategyType === key ? '#f0f5ff' : 'white'
                            }}
                        >
                            <div style={{ textAlign: 'center' }}>
                                <div style={{ fontSize: 32, marginBottom: 12, color: strategyType === key ? '#1890ff' : '#595959' }}>
                                    {strategy.icon}
                                </div>
                                <Title level={4} style={{ margin: 0, color: '#1d1d1f' }}>
                                    {strategy.name}
                                </Title>
                                <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
                                    {strategy.description}
                                </Text>
                                <div style={{ marginTop: 12 }}>
                                    <span style={{
                                        padding: '4px 12px',
                                        borderRadius: 12,
                                        background: '#f5f5f7',
                                        color: '#595959',
                                        fontSize: 12,
                                        border: '1px solid #d9d9d9'
                                    }}>
                                        난이도: {strategy.difficulty}
                                    </span>
                                </div>
                            </div>
                        </Card>
                    </Col>
                ))}
            </Row>
        </div>
    );

    // Step 2: 진입 조건 설정
    const renderStep2 = () => (
        <div style={{ padding: '20px 0' }}>
            <Row gutter={24}>
                <Col xs={24} lg={12}>
                    <Card
                        title={<><ThunderboltOutlined /> 진입 조건</>}
                        style={{ marginBottom: 16 }}
                    >
                        <div style={{ marginBottom: 24 }}>
                            <Text strong>거래 코인</Text>
                            <Select
                                value={symbol}
                                onChange={setSymbol}
                                style={{ width: '100%', marginTop: 8 }}
                                size="large"
                            >
                                <Option value="BTCUSDT">비트코인 (BTC/USDT)</Option>
                                <Option value="ETHUSDT">이더리움 (ETH/USDT)</Option>
                                <Option value="XRPUSDT">리플 (XRP/USDT)</Option>
                                <Option value="SOLUSDT">솔라나 (SOL/USDT)</Option>
                            </Select>
                        </div>

                        <div style={{ marginBottom: 24 }}>
                            <Text strong>시간봉 (타임프레임)</Text>
                            <Select
                                value={timeframe}
                                onChange={setTimeframe}
                                style={{ width: '100%', marginTop: 8 }}
                                size="large"
                            >
                                <Option value="15m">15분봉</Option>
                                <Option value="1h">1시간봉 (추천)</Option>
                                <Option value="4h">4시간봉</Option>
                                <Option value="1d">일봉</Option>
                            </Select>
                        </div>

                        <Divider />

                        {(strategyType === 'rsi_reversal' || strategyType === 'golden_cross') && (
                            <>
                                <div style={{ marginBottom: 24 }}>
                                    <Text strong>RSI 설정</Text>
                                    <div style={{ marginTop: 16 }}>
                                        <Text type="secondary">RSI 기간: {rsiPeriod}</Text>
                                        <Slider
                                            value={rsiPeriod}
                                            onChange={setRsiPeriod}
                                            min={5}
                                            max={30}
                                            marks={{ 5: '5', 14: '14', 30: '30' }}
                                        />
                                    </div>

                                    <Row gutter={16} style={{ marginTop: 16 }}>
                                        <Col span={12}>
                                            <Text type="secondary">매수 기준 (과매도)</Text>
                                            <InputNumber
                                                value={rsiBuy}
                                                onChange={setRsiBuy}
                                                min={10}
                                                max={40}
                                                style={{ width: '100%', marginTop: 4 }}
                                                addonAfter="이하"
                                            />
                                        </Col>
                                        <Col span={12}>
                                            <Text type="secondary">매도 기준 (과매수)</Text>
                                            <InputNumber
                                                value={rsiSell}
                                                onChange={setRsiSell}
                                                min={60}
                                                max={90}
                                                style={{ width: '100%', marginTop: 4 }}
                                                addonAfter="이상"
                                            />
                                        </Col>
                                    </Row>
                                </div>
                            </>
                        )}

                        {(strategyType === 'golden_cross' || strategyType === 'trend_following') && (
                            <div style={{ marginBottom: 24 }}>
                                <Text strong>이동평균선 (EMA) 설정</Text>
                                <Row gutter={16} style={{ marginTop: 12 }}>
                                    <Col span={12}>
                                        <Text type="secondary">단기 EMA</Text>
                                        <InputNumber
                                            value={emaShort}
                                            onChange={setEmaShort}
                                            min={3}
                                            max={50}
                                            style={{ width: '100%', marginTop: 4 }}
                                            addonAfter="봉"
                                        />
                                    </Col>
                                    <Col span={12}>
                                        <Text type="secondary">장기 EMA</Text>
                                        <InputNumber
                                            value={emaLong}
                                            onChange={setEmaLong}
                                            min={10}
                                            max={200}
                                            style={{ width: '100%', marginTop: 4 }}
                                            addonAfter="봉"
                                        />
                                    </Col>
                                </Row>
                            </div>
                        )}
                    </Card>
                </Col>

                <Col xs={24} lg={12}>
                    <Card
                        title={<><SafetyCertificateOutlined /> 리스크 관리</>}
                        style={{ marginBottom: 16 }}
                    >
                        <Alert
                            message="중요: 손절은 반드시 설정하세요!"
                            description="손절 없이 거래하면 큰 손실을 볼 수 있습니다. 처음에는 2~3%를 추천합니다."
                            type="warning"
                            showIcon
                            style={{ marginBottom: 20 }}
                        />

                        <div style={{ marginBottom: 24 }}>
                            <Text strong style={{ color: '#ff4d4f' }}>손절 (Stop Loss)</Text>
                            <div style={{ marginTop: 8 }}>
                                <Slider
                                    value={stopLoss}
                                    onChange={setStopLoss}
                                    min={0.5}
                                    max={10}
                                    step={0.5}
                                    marks={{ 0.5: '0.5%', 2: '2%', 5: '5%', 10: '10%' }}
                                />
                                <Text type="danger" style={{ fontSize: 16, fontWeight: 'bold' }}>
                                    -{stopLoss}% 에서 손절
                                </Text>
                            </div>
                        </div>

                        <div style={{ marginBottom: 24 }}>
                            <Text strong style={{ color: '#52c41a' }}>익절 (Take Profit)</Text>
                            <div style={{ marginTop: 8 }}>
                                <Slider
                                    value={takeProfit}
                                    onChange={setTakeProfit}
                                    min={1}
                                    max={20}
                                    step={0.5}
                                    marks={{ 1: '1%', 4: '4%', 10: '10%', 20: '20%' }}
                                />
                                <Text type="success" style={{ fontSize: 16, fontWeight: 'bold' }}>
                                    +{takeProfit}% 에서 익절
                                </Text>
                            </div>
                        </div>

                        <Divider />

                        <div style={{ marginBottom: 24 }}>
                            <Text strong>포지션 크기</Text>
                            <Slider
                                value={positionSize}
                                onChange={setPositionSize}
                                min={5}
                                max={100}
                                step={5}
                                marks={{ 5: '5%', 25: '25%', 50: '50%', 100: '100%' }}
                                style={{ marginTop: 8 }}
                            />
                            <Text>자금의 <Text strong>{positionSize}%</Text>를 사용</Text>
                        </div>

                        <div style={{ marginBottom: 24 }}>
                            <Text strong>레버리지</Text>
                            <Slider
                                value={leverage}
                                onChange={setLeverage}
                                min={1}
                                max={20}
                                marks={{ 1: '1x', 5: '5x', 10: '10x', 20: '20x' }}
                                style={{ marginTop: 8 }}
                            />
                            <Text type={leverage > 5 ? 'danger' : 'secondary'}>
                                {leverage > 5 && '⚠️ '}레버리지 {leverage}배
                            </Text>
                        </div>

                        <Divider />

                        <div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <div>
                                    <Text strong>트레일링 스탑</Text>
                                </div>
                                <Switch
                                    checked={trailingStop}
                                    onChange={setTrailingStop}
                                />
                            </div>

                            {trailingStop && (
                                <div style={{ marginTop: 12 }}>
                                    <Text type="secondary">트레일링 거리: {trailingDistance}%</Text>
                                    <Slider
                                        value={trailingDistance}
                                        onChange={setTrailingDistance}
                                        min={0.5}
                                        max={5}
                                        step={0.5}
                                    />
                                </div>
                            )}
                        </div>
                    </Card>
                </Col>
            </Row>
        </div>
    );

    // Step 3: 확인 및 저장
    const renderStep3 = () => (
        <div style={{ padding: '20px 0' }}>
            <Card title="전략 이름 설정" style={{ marginBottom: 24 }}>
                <div style={{ marginBottom: 16 }}>
                    <Text strong>전략 이름</Text>
                    <input
                        type="text"
                        value={strategyName}
                        onChange={(e) => setStrategyName(e.target.value)}
                        placeholder="예: 내 첫 번째 골든크로스 전략"
                        style={{
                            width: '100%',
                            padding: '12px',
                            fontSize: '16px',
                            border: '1px solid #d9d9d9',
                            borderRadius: '8px',
                            marginTop: '8px'
                        }}
                    />
                </div>
            </Card>

            <Card title="전략 요약" style={{ marginBottom: 24 }}>
                <Row gutter={[16, 16]}>
                    <Col span={12}>
                        <div style={{ padding: 16, background: '#f5f5f7', borderRadius: 8 }}>
                            <Text type="secondary">전략 유형</Text>
                            <div>
                                <Text strong style={{ fontSize: 16 }}>
                                    {strategyTypes[strategyType].name}
                                </Text>
                            </div>
                        </div>
                    </Col>
                    <Col span={12}>
                        <div style={{ padding: 16, background: '#f5f5f7', borderRadius: 8 }}>
                            <Text type="secondary">거래 코인</Text>
                            <div>
                                <Text strong style={{ fontSize: 16 }}>{symbol}</Text>
                            </div>
                        </div>
                    </Col>
                    <Col span={12}>
                        <div style={{ padding: 16, background: '#fff1f0', borderRadius: 8 }}>
                            <Text type="secondary">손절</Text>
                            <div>
                                <Text strong style={{ fontSize: 16, color: '#ff4d4f' }}>-{stopLoss}%</Text>
                            </div>
                        </div>
                    </Col>
                    <Col span={12}>
                        <div style={{ padding: 16, background: '#f6ffed', borderRadius: 8 }}>
                            <Text type="secondary">익절</Text>
                            <div>
                                <Text strong style={{ fontSize: 16, color: '#52c41a' }}>+{takeProfit}%</Text>
                            </div>
                        </div>
                    </Col>
                    <Col span={12}>
                        <div style={{ padding: 16, background: '#f5f5f7', borderRadius: 8 }}>
                            <Text type="secondary">레버리지</Text>
                            <div>
                                <Text strong style={{ fontSize: 16 }}>{leverage}x</Text>
                            </div>
                        </div>
                    </Col>
                    <Col span={12}>
                        <div style={{ padding: 16, background: '#f5f5f7', borderRadius: 8 }}>
                            <Text type="secondary">포지션 크기</Text>
                            <div>
                                <Text strong style={{ fontSize: 16 }}>{positionSize}%</Text>
                            </div>
                        </div>
                    </Col>
                </Row>

                <Divider />

                <div style={{
                    padding: 16,
                    background: '#f0f5ff',
                    borderRadius: 8,
                    color: '#1d1d1f',
                    textAlign: 'center',
                    border: '1px solid #d6e4ff'
                }}>
                    <Text style={{ fontSize: 14, color: '#595959' }}>예상 손익비 (Risk:Reward)</Text>
                    <div style={{ fontSize: 24, fontWeight: 'bold', marginTop: 4, color: '#1d1d1f' }}>
                        1 : {(takeProfit / stopLoss).toFixed(1)}
                    </div>
                </div>
            </Card>

            <Button
                type="primary"
                size="large"
                icon={<RocketOutlined />}
                onClick={handleCreateStrategy}
                loading={loading}
                block
                style={{
                    height: 56,
                    fontSize: 18,
                    background: '#1890ff',
                    border: 'none'
                }}
            >
                {loading ? '전략 생성 중...' : '전략 생성하기'}
            </Button>
        </div>
    );

    // Step 4: 완료
    const renderStep4 = () => (
        <div style={{ textAlign: 'center', padding: '60px 20px' }}>
            <CheckCircleOutlined style={{ fontSize: 80, color: '#52c41a', marginBottom: 24 }} />
            <Title level={2}>전략이 생성되었습니다!</Title>
            <Paragraph type="secondary" style={{ fontSize: 16 }}>
                이제 백테스트를 실행하여 전략의 성과를 확인해보세요.
            </Paragraph>
            <Row gutter={16} justify="center" style={{ marginTop: 32 }}>
                <Col>
                    <Button
                        size="large"
                        onClick={() => {
                            setCurrentStep(0);
                            setStrategyName('');
                        }}
                    >
                        새 전략 만들기
                    </Button>
                </Col>
                <Col>
                    <Button
                        type="primary"
                        size="large"
                        onClick={() => window.location.href = '/strategy'}
                    >
                        전략 관리로 이동
                    </Button>
                </Col>
            </Row>
        </div>
    );

    const steps = [
        { title: '전략 선택', icon: <RocketOutlined /> },
        { title: '조건 설정', icon: <ThunderboltOutlined /> },
        { title: '저장', icon: <CheckCircleOutlined /> },
    ];

    return (
        <Card
            style={{
                maxWidth: 1000,
                margin: '0 auto',
                boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
                borderRadius: 16
            }}
        >
            <div style={{ textAlign: 'center', marginBottom: 32 }}>
                <Title level={2} style={{ marginBottom: 8 }}>
                    간단 전략 생성기
                </Title>
                <Text type="secondary" style={{ fontSize: 16 }}>
                    3단계로 나만의 트레이딩 전략을 만들어보세요
                </Text>
            </div>

            {currentStep < 3 && (
                <Steps current={currentStep} style={{ marginBottom: 32 }}>
                    {steps.map((step, index) => (
                        <Step
                            key={index}
                            title={step.title}
                            icon={step.icon}
                        />
                    ))}
                </Steps>
            )}

            {currentStep === 0 && renderStep1()}
            {currentStep === 1 && renderStep2()}
            {currentStep === 2 && renderStep3()}
            {currentStep === 3 && renderStep4()}

            {currentStep < 3 && currentStep !== 3 && (
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    marginTop: 24,
                    paddingTop: 24,
                    borderTop: '1px solid #f0f0f0'
                }}>
                    <Button
                        size="large"
                        disabled={currentStep === 0}
                        onClick={() => setCurrentStep(currentStep - 1)}
                    >
                        이전
                    </Button>
                    <Button
                        type="primary"
                        size="large"
                        onClick={() => {
                            if (currentStep < 2) {
                                setCurrentStep(currentStep + 1);
                            }
                        }}
                    >
                        {currentStep === 2 ? '' : '다음'}
                    </Button>
                </div>
            )}
        </Card>
    );
}

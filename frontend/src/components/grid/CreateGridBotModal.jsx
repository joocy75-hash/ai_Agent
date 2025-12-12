/**
 * CreateGridBotModal Component
 *
 * 그리드 봇 생성/편집을 위한 풀스크린 모달
 * 라이트 테마 버전
 *
 * 특징:
 * - 3단계 위저드 형식 (기본 설정 → 그리드 설정 → 확인)
 * - 실시간 그리드 미리보기
 * - 24시간 고저가 기반 추천 범위
 * - 예상 수익 계산기
 */

import { useState, useEffect, useMemo } from 'react';
import {
    Modal,
    Form,
    Input,
    InputNumber,
    Select,
    Slider,
    Button,
    Space,
    Typography,
    Row,
    Col,
    Divider,
    Alert,
    Steps,
    Card,
    Tooltip,
    Spin,
    message,
} from 'antd';
import {
    ThunderboltOutlined,
    DollarOutlined,
    LineChartOutlined,
    SettingOutlined,
    CheckCircleOutlined,
    InfoCircleOutlined,
    ArrowLeftOutlined,
    ArrowRightOutlined,
    RocketOutlined,
} from '@ant-design/icons';

import GridVisualizer from './GridVisualizer';
import gridBotAPI from '../../api/gridBot';
import botInstancesAPI from '../../api/botInstances';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

// 인기 심볼 목록
const POPULAR_SYMBOLS = [
    { value: 'BTCUSDT', label: 'BTC/USDT', icon: '₿' },
    { value: 'ETHUSDT', label: 'ETH/USDT', icon: 'Ξ' },
    { value: 'SOLUSDT', label: 'SOL/USDT', icon: '◎' },
    { value: 'BNBUSDT', label: 'BNB/USDT', icon: '◆' },
    { value: 'XRPUSDT', label: 'XRP/USDT', icon: '✕' },
];

export default function CreateGridBotModal({
    open,
    onClose,
    onSuccess,
    maxAllocation = 100,
    editBot = null, // 수정 모드일 때 기존 봇 데이터
}) {
    const [form] = Form.useForm();
    const [currentStep, setCurrentStep] = useState(0);
    const [loading, setLoading] = useState(false);
    const [marketData, setMarketData] = useState(null);
    const [previewData, setPreviewData] = useState(null);

    // 폼 값 실시간 추적
    const [formValues, setFormValues] = useState({
        name: '',
        symbol: 'BTCUSDT',
        allocation_percent: 10,
        lower_price: 0,
        upper_price: 0,
        grid_count: 10,
        grid_mode: 'arithmetic',
        total_investment: 1000,
    });

    // 수정 모드 초기화
    useEffect(() => {
        if (editBot && open) {
            const initialValues = {
                name: editBot.name,
                symbol: editBot.symbol,
                allocation_percent: editBot.allocation_percent,
                lower_price: editBot.grid_config?.lower_price || 0,
                upper_price: editBot.grid_config?.upper_price || 0,
                grid_count: editBot.grid_config?.grid_count || 10,
                grid_mode: editBot.grid_config?.grid_mode || 'arithmetic',
                total_investment: editBot.grid_config?.total_investment || 1000,
            };
            form.setFieldsValue(initialValues);
            setFormValues(initialValues);
        } else if (open) {
            form.resetFields();
            setFormValues({
                name: '',
                symbol: 'BTCUSDT',
                allocation_percent: 10,
                lower_price: 0,
                upper_price: 0,
                grid_count: 10,
                grid_mode: 'arithmetic',
                total_investment: 1000,
            });
            setCurrentStep(0);
        }
    }, [editBot, open, form]);

    // 심볼 변경 시 시장 데이터 로드
    useEffect(() => {
        if (open && formValues.symbol) {
            loadMarketData(formValues.symbol);
        }
    }, [formValues.symbol, open]);

    // 시장 데이터 로드
    const loadMarketData = async (symbol) => {
        try {
            const data = await gridBotAPI.getMarketPrice(symbol);
            setMarketData(data);

            // 24시간 고저가 기반 추천 범위 설정
            if (!editBot && data.low_24h && data.high_24h) {
                const padding = (data.high_24h - data.low_24h) * 0.1;
                const recommendedLower = Math.floor(data.low_24h - padding);
                const recommendedUpper = Math.ceil(data.high_24h + padding);

                form.setFieldsValue({
                    lower_price: recommendedLower,
                    upper_price: recommendedUpper,
                });
                setFormValues((prev) => ({
                    ...prev,
                    lower_price: recommendedLower,
                    upper_price: recommendedUpper,
                }));
            }
        } catch (err) {
            console.error('시장 데이터 로드 실패:', err);
            // 기본값 설정
            setMarketData({ price: 95000, high_24h: 98000, low_24h: 92000 });
        }
    };

    // 그리드 미리보기 계산
    useEffect(() => {
        const { lower_price, upper_price, grid_count, grid_mode, total_investment } =
            formValues;

        if (lower_price > 0 && upper_price > lower_price && grid_count >= 2) {
            // 로컬 계산 (API 호출 없이)
            const grids = [];
            const priceRange = upper_price - lower_price;
            const perGridAmount = total_investment / grid_count;
            const gridProfit = (priceRange / grid_count / lower_price) * 100;

            for (let i = 0; i < grid_count; i++) {
                let price;
                if (grid_mode === 'geometric') {
                    const ratio = Math.pow(upper_price / lower_price, i / (grid_count - 1));
                    price = lower_price * ratio;
                } else {
                    price = lower_price + (priceRange * i) / (grid_count - 1);
                }

                grids.push({
                    grid_index: i,
                    price,
                    status: 'pending',
                });
            }

            setPreviewData({
                grids,
                per_grid_amount: perGridAmount,
                expected_profit_per_grid: gridProfit,
                total_grids: grid_count,
            });
        }
    }, [formValues]);

    // 폼 값 변경 핸들러
    const handleValuesChange = (changedValues, allValues) => {
        setFormValues((prev) => ({ ...prev, ...changedValues }));
    };

    // 다음 단계
    const handleNext = async () => {
        try {
            if (currentStep === 0) {
                await form.validateFields(['name', 'symbol', 'allocation_percent']);
            } else if (currentStep === 1) {
                await form.validateFields([
                    'lower_price',
                    'upper_price',
                    'grid_count',
                    'total_investment',
                ]);
            }
            setCurrentStep(currentStep + 1);
        } catch (err) {
            // 유효성 검사 실패
        }
    };

    // 이전 단계
    const handlePrev = () => {
        setCurrentStep(currentStep - 1);
    };

    // 제출
    const handleSubmit = async () => {
        setLoading(true);
        try {
            const values = await form.validateFields();

            if (editBot) {
                // 수정 모드
                await botInstancesAPI.update(editBot.id, {
                    name: values.name,
                    symbol: values.symbol,
                    allocation_percent: values.allocation_percent,
                });
                await gridBotAPI.saveConfig(editBot.id, {
                    lower_price: values.lower_price,
                    upper_price: values.upper_price,
                    grid_count: values.grid_count,
                    grid_mode: values.grid_mode,
                    total_investment: values.total_investment,
                });
                message.success('그리드 봇이 수정되었습니다');
            } else {
                // 생성 모드
                const createResponse = await botInstancesAPI.create({
                    name: values.name,
                    bot_type: 'grid',
                    symbol: values.symbol,
                    allocation_percent: values.allocation_percent,
                });

                await gridBotAPI.saveConfig(createResponse.bot_id, {
                    lower_price: values.lower_price,
                    upper_price: values.upper_price,
                    grid_count: values.grid_count,
                    grid_mode: values.grid_mode,
                    total_investment: values.total_investment,
                });
                message.success('그리드 봇이 생성되었습니다');
            }

            onSuccess?.();
            onClose();
        } catch (err) {
            message.error(err.response?.data?.detail || '저장 실패');
        } finally {
            setLoading(false);
        }
    };

    // 스텝 정의
    const steps = [
        {
            title: '기본 설정',
            icon: <SettingOutlined />,
            description: '봇 이름 및 심볼',
        },
        {
            title: '그리드 설정',
            icon: <LineChartOutlined />,
            description: '가격 범위 및 그리드',
        },
        {
            title: '확인',
            icon: <CheckCircleOutlined />,
            description: '설정 검토',
        },
    ];

    // 예상 수익 계산
    const expectedStats = useMemo(() => {
        if (!previewData) return null;

        const { per_grid_amount, expected_profit_per_grid, total_grids } = previewData;
        const dailyTrades = 3; // 예상 일일 거래 수
        const dailyProfit = per_grid_amount * (expected_profit_per_grid / 100) * dailyTrades;
        const monthlyProfit = dailyProfit * 30;

        return {
            perGridProfit: expected_profit_per_grid.toFixed(2),
            dailyProfit: dailyProfit.toFixed(2),
            monthlyProfit: monthlyProfit.toFixed(2),
            apr: ((monthlyProfit * 12) / formValues.total_investment * 100).toFixed(1),
        };
    }, [previewData, formValues.total_investment]);

    return (
        <Modal
            open={open}
            onCancel={onClose}
            footer={null}
            width={900}
            centered
            destroyOnClose
            styles={{
                content: {
                    background: '#ffffff',
                    border: '1px solid #f0f0f0',
                    borderRadius: 20,
                    padding: 0,
                    overflow: 'hidden',
                    boxShadow: '0 20px 60px rgba(0, 0, 0, 0.15)',
                },
                header: { display: 'none' },
                body: { padding: 0 },
            }}
        >
            {/* 헤더 */}
            <div
                style={{
                    background: 'linear-gradient(135deg, #00C076 0%, #00A8FF 100%)',
                    padding: '24px 32px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 16,
                }}
            >
                <div
                    style={{
                        width: 48,
                        height: 48,
                        borderRadius: 12,
                        background: 'rgba(255,255,255,0.2)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                    }}
                >
                    <LineChartOutlined style={{ fontSize: 24, color: '#fff' }} />
                </div>
                <div>
                    <Title level={4} style={{ margin: 0, color: '#fff' }}>
                        {editBot ? '그리드 봇 수정' : '새 그리드 봇 만들기'}
                    </Title>
                    <Text style={{ color: 'rgba(255,255,255,0.8)' }}>
                        가격 범위 내에서 자동으로 매수/매도를 반복합니다
                    </Text>
                </div>
            </div>

            {/* 스텝 인디케이터 */}
            <div style={{ padding: '24px 32px 0', background: '#ffffff' }}>
                <Steps
                    current={currentStep}
                    items={steps.map((step, index) => ({
                        title: (
                            <Text style={{ color: '#1d1d1f', fontSize: 13, fontWeight: 500 }}>{step.title}</Text>
                        ),
                        description: (
                            <Text style={{ color: '#86868b', fontSize: 11 }}>
                                {step.description}
                            </Text>
                        ),
                        icon: (
                            <div
                                style={{
                                    color:
                                        currentStep >= index
                                            ? '#00C076'
                                            : '#d2d2d7',
                                }}
                            >
                                {step.icon}
                            </div>
                        ),
                    }))}
                    style={{
                        marginBottom: 24,
                    }}
                />
            </div>

            {/* 폼 내용 */}
            <Form
                form={form}
                layout="vertical"
                onValuesChange={handleValuesChange}
                initialValues={formValues}
                style={{ padding: '0 32px 24px', background: '#ffffff' }}
            >
                {/* Step 1: 기본 설정 */}
                {currentStep === 0 && (
                    <div style={{ minHeight: 300 }}>
                        <Row gutter={24}>
                            <Col span={12}>
                                <Form.Item
                                    name="name"
                                    label={
                                        <Text style={{ color: '#1d1d1f', fontWeight: 500 }}>
                                            봇 이름
                                        </Text>
                                    }
                                    rules={[{ required: true, message: '봇 이름을 입력하세요' }]}
                                >
                                    <Input
                                        placeholder="예: BTC 그리드 #1"
                                        size="large"
                                        style={{
                                            background: '#f5f5f7',
                                            border: '1px solid #e5e5ea',
                                            color: '#1d1d1f',
                                            borderRadius: 10,
                                        }}
                                    />
                                </Form.Item>
                            </Col>
                            <Col span={12}>
                                <Form.Item
                                    name="symbol"
                                    label={
                                        <Text style={{ color: '#1d1d1f', fontWeight: 500 }}>
                                            거래 페어
                                        </Text>
                                    }
                                    rules={[{ required: true }]}
                                >
                                    <Select
                                        size="large"
                                        style={{ width: '100%' }}
                                    >
                                        {POPULAR_SYMBOLS.map((s) => (
                                            <Option key={s.value} value={s.value}>
                                                <Space>
                                                    <span style={{ fontSize: 16 }}>{s.icon}</span>
                                                    {s.label}
                                                </Space>
                                            </Option>
                                        ))}
                                    </Select>
                                </Form.Item>
                            </Col>
                        </Row>

                        <Form.Item
                            name="allocation_percent"
                            label={
                                <Space>
                                    <Text style={{ color: '#1d1d1f', fontWeight: 500 }}>
                                        잔고 할당
                                    </Text>
                                    <Tooltip title="전체 잔고 중 이 봇에 할당할 비율">
                                        <InfoCircleOutlined
                                            style={{ color: '#86868b' }}
                                        />
                                    </Tooltip>
                                </Space>
                            }
                            rules={[{ required: true }]}
                        >
                            <Slider
                                min={1}
                                max={maxAllocation}
                                marks={{
                                    1: <span style={{ color: '#1d1d1f' }}>1%</span>,
                                    25: <span style={{ color: '#1d1d1f' }}>25%</span>,
                                    50: <span style={{ color: '#1d1d1f' }}>50%</span>,
                                    75: <span style={{ color: '#1d1d1f' }}>75%</span>,
                                    [maxAllocation]: <span style={{ color: '#1d1d1f' }}>{maxAllocation}%</span>,
                                }}
                                tooltip={{ formatter: (v) => `${v}%` }}
                                styles={{
                                    track: { background: '#0071e3' },
                                    rail: { background: '#e5e5ea' },
                                }}
                            />
                        </Form.Item>

                        {/* 시장 정보 카드 */}
                        {marketData && (
                            <Card
                                style={{
                                    background: '#f5f5f7',
                                    border: '1px solid #e5e5ea',
                                    borderRadius: 12,
                                    marginTop: 24,
                                }}
                                styles={{ body: { padding: 16 } }}
                            >
                                <Row gutter={16}>
                                    <Col span={8}>
                                        <Text
                                            style={{
                                                color: '#86868b',
                                                fontSize: 12,
                                                display: 'block',
                                            }}
                                        >
                                            현재가
                                        </Text>
                                        <Text
                                            style={{
                                                color: '#ff9500',
                                                fontSize: 20,
                                                fontWeight: 700,
                                            }}
                                        >
                                            ${marketData.price?.toLocaleString()}
                                        </Text>
                                    </Col>
                                    <Col span={8}>
                                        <Text
                                            style={{
                                                color: '#86868b',
                                                fontSize: 12,
                                                display: 'block',
                                            }}
                                        >
                                            24H 고가
                                        </Text>
                                        <Text
                                            style={{
                                                color: '#34c759',
                                                fontSize: 20,
                                                fontWeight: 700,
                                            }}
                                        >
                                            ${marketData.high_24h?.toLocaleString()}
                                        </Text>
                                    </Col>
                                    <Col span={8}>
                                        <Text
                                            style={{
                                                color: '#86868b',
                                                fontSize: 12,
                                                display: 'block',
                                            }}
                                        >
                                            24H 저가
                                        </Text>
                                        <Text
                                            style={{
                                                color: '#ff3b30',
                                                fontSize: 20,
                                                fontWeight: 700,
                                            }}
                                        >
                                            ${marketData.low_24h?.toLocaleString()}
                                        </Text>
                                    </Col>
                                </Row>
                            </Card>
                        )}
                    </div>
                )}

                {/* Step 2: 그리드 설정 */}
                {currentStep === 1 && (
                    <Row gutter={24}>
                        <Col span={12}>
                            <Space direction="vertical" style={{ width: '100%' }} size={16}>
                                <Row gutter={12}>
                                    <Col span={12}>
                                        <Form.Item
                                            name="lower_price"
                                            label={
                                                <Text style={{ color: '#ff3b30', fontWeight: 500 }}>
                                                    하한가 ($)
                                                </Text>
                                            }
                                            rules={[{ required: true, message: '필수' }]}
                                        >
                                            <InputNumber
                                                size="large"
                                                style={{
                                                    width: '100%',
                                                    background: '#f5f5f7',
                                                    borderRadius: 10,
                                                }}
                                                min={0}
                                                formatter={(v) =>
                                                    `${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
                                                }
                                                parser={(v) => v.replace(/\$\s?|(,*)/g, '')}
                                            />
                                        </Form.Item>
                                    </Col>
                                    <Col span={12}>
                                        <Form.Item
                                            name="upper_price"
                                            label={
                                                <Text style={{ color: '#34c759', fontWeight: 500 }}>
                                                    상한가 ($)
                                                </Text>
                                            }
                                            rules={[{ required: true, message: '필수' }]}
                                        >
                                            <InputNumber
                                                size="large"
                                                style={{
                                                    width: '100%',
                                                    background: '#f5f5f7',
                                                    borderRadius: 10,
                                                }}
                                                min={0}
                                                formatter={(v) =>
                                                    `${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
                                                }
                                                parser={(v) => v.replace(/\$\s?|(,*)/g, '')}
                                            />
                                        </Form.Item>
                                    </Col>
                                </Row>

                                <Form.Item
                                    name="grid_count"
                                    label={
                                        <Text style={{ color: '#1d1d1f', fontWeight: 500 }}>
                                            그리드 개수
                                        </Text>
                                    }
                                    rules={[{ required: true }]}
                                >
                                    <Slider
                                        min={2}
                                        max={50}
                                        marks={{
                                            2: <span style={{ color: '#1d1d1f' }}>2</span>,
                                            10: <span style={{ color: '#1d1d1f' }}>10</span>,
                                            25: <span style={{ color: '#1d1d1f' }}>25</span>,
                                            50: <span style={{ color: '#1d1d1f' }}>50</span>,
                                        }}
                                        styles={{
                                            track: { background: '#0071e3' },
                                            rail: { background: '#e5e5ea' },
                                        }}
                                    />
                                </Form.Item>

                                <Form.Item
                                    name="grid_mode"
                                    label={
                                        <Text style={{ color: '#1d1d1f', fontWeight: 500 }}>
                                            그리드 모드
                                        </Text>
                                    }
                                >
                                    <Select size="large">
                                        <Option value="arithmetic">
                                            균등 간격 (Arithmetic)
                                        </Option>
                                        <Option value="geometric">
                                            기하 간격 (Geometric)
                                        </Option>
                                    </Select>
                                </Form.Item>

                                <Form.Item
                                    name="total_investment"
                                    label={
                                        <Text style={{ color: '#1d1d1f', fontWeight: 500 }}>
                                            총 투자금 (USDT)
                                        </Text>
                                    }
                                    rules={[{ required: true }]}
                                >
                                    <InputNumber
                                        size="large"
                                        style={{ width: '100%', background: '#f5f5f7', borderRadius: 10 }}
                                        min={10}
                                        max={100000}
                                        formatter={(v) =>
                                            `$ ${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
                                        }
                                        parser={(v) => v.replace(/\$\s?|(,*)/g, '')}
                                    />
                                </Form.Item>
                            </Space>
                        </Col>

                        {/* 그리드 미리보기 */}
                        <Col span={12}>
                            <Text
                                style={{
                                    color: '#1d1d1f',
                                    fontSize: 13,
                                    fontWeight: 500,
                                    display: 'block',
                                    marginBottom: 8,
                                }}
                            >
                                그리드 미리보기
                            </Text>
                            <GridVisualizer
                                lowerPrice={formValues.lower_price || 85000}
                                upperPrice={formValues.upper_price || 100000}
                                gridCount={formValues.grid_count || 10}
                                gridMode={formValues.grid_mode}
                                currentPrice={marketData?.price || 95000}
                                orders={previewData?.grids || []}
                                height={280}
                                lightMode={true}
                            />
                        </Col>
                    </Row>
                )}

                {/* Step 3: 확인 */}
                {currentStep === 2 && (
                    <Row gutter={24}>
                        <Col span={12}>
                            <Card
                                style={{
                                    background: '#f5f5f7',
                                    border: '1px solid #e5e5ea',
                                    borderRadius: 12,
                                }}
                                styles={{ body: { padding: 20 } }}
                            >
                                <Title
                                    level={5}
                                    style={{ color: '#1d1d1f', marginBottom: 20 }}
                                >
                                    설정 요약
                                </Title>

                                <Space direction="vertical" style={{ width: '100%' }} size={12}>
                                    <div
                                        style={{
                                            display: 'flex',
                                            justifyContent: 'space-between',
                                        }}
                                    >
                                        <Text style={{ color: '#86868b' }}>
                                            봇 이름
                                        </Text>
                                        <Text style={{ color: '#1d1d1f', fontWeight: 600 }}>
                                            {formValues.name}
                                        </Text>
                                    </div>
                                    <div
                                        style={{
                                            display: 'flex',
                                            justifyContent: 'space-between',
                                        }}
                                    >
                                        <Text style={{ color: '#86868b' }}>
                                            거래 페어
                                        </Text>
                                        <Text style={{ color: '#0071e3', fontWeight: 600 }}>
                                            {formValues.symbol}
                                        </Text>
                                    </div>
                                    <Divider style={{ borderColor: '#e5e5ea', margin: '12px 0' }} />
                                    <div
                                        style={{
                                            display: 'flex',
                                            justifyContent: 'space-between',
                                        }}
                                    >
                                        <Text style={{ color: '#86868b' }}>
                                            가격 범위
                                        </Text>
                                        <Text style={{ color: '#1d1d1f' }}>
                                            <span style={{ color: '#ff3b30' }}>
                                                ${formValues.lower_price?.toLocaleString()}
                                            </span>
                                            {' - '}
                                            <span style={{ color: '#34c759' }}>
                                                ${formValues.upper_price?.toLocaleString()}
                                            </span>
                                        </Text>
                                    </div>
                                    <div
                                        style={{
                                            display: 'flex',
                                            justifyContent: 'space-between',
                                        }}
                                    >
                                        <Text style={{ color: '#86868b' }}>
                                            그리드 개수
                                        </Text>
                                        <Text style={{ color: '#1d1d1f', fontWeight: 600 }}>
                                            {formValues.grid_count}개
                                        </Text>
                                    </div>
                                    <div
                                        style={{
                                            display: 'flex',
                                            justifyContent: 'space-between',
                                        }}
                                    >
                                        <Text style={{ color: '#86868b' }}>
                                            총 투자금
                                        </Text>
                                        <Text style={{ color: '#ff9500', fontWeight: 600 }}>
                                            ${formValues.total_investment?.toLocaleString()}
                                        </Text>
                                    </div>
                                    <div
                                        style={{
                                            display: 'flex',
                                            justifyContent: 'space-between',
                                        }}
                                    >
                                        <Text style={{ color: '#86868b' }}>
                                            그리드당 투자금
                                        </Text>
                                        <Text style={{ color: '#1d1d1f' }}>
                                            ${previewData?.per_grid_amount?.toFixed(2)}
                                        </Text>
                                    </div>
                                </Space>
                            </Card>
                        </Col>

                        <Col span={12}>
                            <Card
                                style={{
                                    background:
                                        'linear-gradient(135deg, rgba(52, 199, 89, 0.08) 0%, rgba(0, 113, 227, 0.08) 100%)',
                                    border: '1px solid rgba(52, 199, 89, 0.3)',
                                    borderRadius: 12,
                                }}
                                styles={{ body: { padding: 20 } }}
                            >
                                <Title
                                    level={5}
                                    style={{ color: '#34c759', marginBottom: 20 }}
                                >
                                    <ThunderboltOutlined /> 예상 수익
                                </Title>

                                {expectedStats && (
                                    <Space
                                        direction="vertical"
                                        style={{ width: '100%' }}
                                        size={12}
                                    >
                                        <div
                                            style={{
                                                display: 'flex',
                                                justifyContent: 'space-between',
                                            }}
                                        >
                                            <Text style={{ color: '#86868b' }}>
                                                그리드당 수익률
                                            </Text>
                                            <Text style={{ color: '#34c759', fontWeight: 600 }}>
                                                {expectedStats.perGridProfit}%
                                            </Text>
                                        </div>
                                        <div
                                            style={{
                                                display: 'flex',
                                                justifyContent: 'space-between',
                                            }}
                                        >
                                            <Text style={{ color: '#86868b' }}>
                                                예상 일일 수익
                                            </Text>
                                            <Text style={{ color: '#34c759', fontWeight: 600 }}>
                                                ~${expectedStats.dailyProfit}
                                            </Text>
                                        </div>
                                        <div
                                            style={{
                                                display: 'flex',
                                                justifyContent: 'space-between',
                                            }}
                                        >
                                            <Text style={{ color: '#86868b' }}>
                                                예상 월간 수익
                                            </Text>
                                            <Text
                                                style={{
                                                    color: '#34c759',
                                                    fontWeight: 700,
                                                    fontSize: 18,
                                                }}
                                            >
                                                ~${expectedStats.monthlyProfit}
                                            </Text>
                                        </div>
                                        <Divider
                                            style={{
                                                borderColor: 'rgba(52, 199, 89, 0.3)',
                                                margin: '12px 0',
                                            }}
                                        />
                                        <div
                                            style={{
                                                display: 'flex',
                                                justifyContent: 'space-between',
                                            }}
                                        >
                                            <Text style={{ color: '#86868b' }}>
                                                예상 연 수익률 (APR)
                                            </Text>
                                            <Text
                                                style={{
                                                    color: '#ff9500',
                                                    fontWeight: 700,
                                                    fontSize: 20,
                                                }}
                                            >
                                                {expectedStats.apr}%
                                            </Text>
                                        </div>
                                    </Space>
                                )}

                                <Alert
                                    type="info"
                                    showIcon={false}
                                    style={{
                                        marginTop: 16,
                                        background: 'rgba(0, 113, 227, 0.08)',
                                        border: 'none',
                                        borderRadius: 8,
                                    }}
                                    message={
                                        <Text style={{ color: '#86868b', fontSize: 11 }}>
                                            ⚠️ 예상 수익은 시장 상황에 따라 달라질 수 있습니다
                                        </Text>
                                    }
                                />
                            </Card>
                        </Col>
                    </Row>
                )}
            </Form>

            {/* 푸터 버튼 */}
            <div
                style={{
                    padding: '16px 32px 24px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    background: '#ffffff',
                    borderTop: '1px solid #f0f0f0',
                }}
            >
                <Button
                    onClick={currentStep === 0 ? onClose : handlePrev}
                    icon={currentStep > 0 ? <ArrowLeftOutlined /> : null}
                    style={{
                        background: '#f5f5f7',
                        border: '1px solid #e5e5ea',
                        color: '#1d1d1f',
                        height: 44,
                        borderRadius: 10,
                        fontWeight: 500,
                    }}
                >
                    {currentStep === 0 ? '취소' : '이전'}
                </Button>

                {currentStep < 2 ? (
                    <Button
                        type="primary"
                        onClick={handleNext}
                        icon={<ArrowRightOutlined />}
                        iconPosition="end"
                        style={{
                            background: '#0071e3',
                            border: 'none',
                            height: 44,
                            borderRadius: 10,
                            fontWeight: 600,
                        }}
                    >
                        다음
                    </Button>
                ) : (
                    <Button
                        type="primary"
                        onClick={handleSubmit}
                        loading={loading}
                        icon={<RocketOutlined />}
                        style={{
                            background: '#34c759',
                            border: 'none',
                            height: 44,
                            borderRadius: 10,
                            fontWeight: 600,
                            minWidth: 140,
                        }}
                    >
                        {editBot ? '저장하기' : '봇 생성'}
                    </Button>
                )}
            </div>
        </Modal>
    );
}

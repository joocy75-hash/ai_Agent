import { useState, useEffect } from 'react';
import { Card, Form, Input, Select, InputNumber, Button, Space, message, Row, Col, Divider } from 'antd';
import {
    EditOutlined,
    SaveOutlined,
    CloseOutlined,
} from '@ant-design/icons';
import { strategyAPI } from '../../api/strategy';

const { Option } = Select;
const { TextArea } = Input;

export default function StrategyEditor({ strategy, onSave, onCancel }) {
    const [form] = Form.useForm();
    const [loading, setLoading] = useState(false);
    const [strategyType, setStrategyType] = useState('TREND_FOLLOWING');

    useEffect(() => {
        if (strategy) {
            form.setFieldsValue(strategy);
            setStrategyType(strategy.type);
        } else {
            form.resetFields();
        }
    }, [strategy, form]);

    const handleSubmit = async (values) => {
        setLoading(true);
        try {
            // 전략 데이터 구성
            const strategyData = {
                name: values.name,
                description: values.description,
                type: values.type,
                symbol: values.symbols?.[0] || 'BTCUSDT',
                timeframe: values.timeframe,
                parameters: values.parameters || {}
            };

            // 실제 API 호출
            await strategyAPI.createStrategy(strategyData);

            message.success(strategy ? '전략이 수정되었습니다' : '전략이 생성되었습니다');
            onSave && onSave(values);
            setLoading(false);
        } catch (error) {
            console.error('[StrategyEditor] Error saving strategy:', error);
            message.error(error.response?.data?.detail || '전략 저장에 실패했습니다');
            setLoading(false);
        }
    };

    const getParameterFields = () => {
        const commonFields = (
            <>
                <Col span={12}>
                    <Form.Item
                        label="Stop Loss (%)"
                        name={['parameters', 'stopLoss']}
                        rules={[{ required: true, message: 'Stop Loss를 입력하세요' }]}
                    >
                        <InputNumber
                            min={0}
                            max={100}
                            step={0.1}
                            style={{ width: '100%' }}
                            placeholder="예: 2.0"
                        />
                    </Form.Item>
                </Col>
                <Col span={12}>
                    <Form.Item
                        label="Take Profit (%)"
                        name={['parameters', 'takeProfit']}
                        rules={[{ required: true, message: 'Take Profit을 입력하세요' }]}
                    >
                        <InputNumber
                            min={0}
                            max={1000}
                            step={0.1}
                            style={{ width: '100%' }}
                            placeholder="예: 5.0"
                        />
                    </Form.Item>
                </Col>
                <Col span={12}>
                    <Form.Item
                        label="포지션 크기 (%)"
                        name={['parameters', 'positionSize']}
                        rules={[{ required: true, message: '포지션 크기를 입력하세요' }]}
                    >
                        <InputNumber
                            min={1}
                            max={100}
                            step={1}
                            style={{ width: '100%' }}
                            placeholder="예: 10"
                        />
                    </Form.Item>
                </Col>
                <Col span={12}>
                    <Form.Item
                        label="레버리지"
                        name={['parameters', 'leverage']}
                        rules={[{ required: true, message: '레버리지를 입력하세요' }]}
                    >
                        <InputNumber
                            min={1}
                            max={125}
                            step={1}
                            style={{ width: '100%' }}
                            placeholder="예: 5"
                        />
                    </Form.Item>
                </Col>
            </>
        );

        switch (strategyType) {
            case 'TREND_FOLLOWING':
                return (
                    <>
                        {commonFields}
                        <Col span={12}>
                            <Form.Item
                                label="EMA 단기"
                                name={['parameters', 'emaShort']}
                                rules={[{ required: true, message: 'EMA 단기를 입력하세요' }]}
                            >
                                <InputNumber
                                    min={1}
                                    max={200}
                                    step={1}
                                    style={{ width: '100%' }}
                                    placeholder="예: 12"
                                />
                            </Form.Item>
                        </Col>
                        <Col span={12}>
                            <Form.Item
                                label="EMA 장기"
                                name={['parameters', 'emaLong']}
                                rules={[{ required: true, message: 'EMA 장기를 입력하세요' }]}
                            >
                                <InputNumber
                                    min={1}
                                    max={200}
                                    step={1}
                                    style={{ width: '100%' }}
                                    placeholder="예: 26"
                                />
                            </Form.Item>
                        </Col>
                    </>
                );

            case 'MEAN_REVERSION':
                return (
                    <>
                        {commonFields}
                        <Col span={12}>
                            <Form.Item
                                label="볼린저 밴드 기간"
                                name={['parameters', 'bbPeriod']}
                                rules={[{ required: true, message: '볼린저 밴드 기간을 입력하세요' }]}
                            >
                                <InputNumber
                                    min={1}
                                    max={200}
                                    step={1}
                                    style={{ width: '100%' }}
                                    placeholder="예: 20"
                                />
                            </Form.Item>
                        </Col>
                        <Col span={12}>
                            <Form.Item
                                label="표준편차 배수"
                                name={['parameters', 'bbStdDev']}
                                rules={[{ required: true, message: '표준편차 배수를 입력하세요' }]}
                            >
                                <InputNumber
                                    min={0.1}
                                    max={5}
                                    step={0.1}
                                    style={{ width: '100%' }}
                                    placeholder="예: 2.0"
                                />
                            </Form.Item>
                        </Col>
                    </>
                );

            case 'BREAKOUT':
                return (
                    <>
                        {commonFields}
                        <Col span={12}>
                            <Form.Item
                                label="돌파 기간"
                                name={['parameters', 'breakoutPeriod']}
                                rules={[{ required: true, message: '돌파 기간을 입력하세요' }]}
                            >
                                <InputNumber
                                    min={1}
                                    max={100}
                                    step={1}
                                    style={{ width: '100%' }}
                                    placeholder="예: 20"
                                />
                            </Form.Item>
                        </Col>
                        <Col span={12}>
                            <Form.Item
                                label="최소 변동폭 (%)"
                                name={['parameters', 'minVolatility']}
                                rules={[{ required: true, message: '최소 변동폭을 입력하세요' }]}
                            >
                                <InputNumber
                                    min={0.1}
                                    max={10}
                                    step={0.1}
                                    style={{ width: '100%' }}
                                    placeholder="예: 1.0"
                                />
                            </Form.Item>
                        </Col>
                    </>
                );

            case 'GRID':
                return (
                    <>
                        {commonFields}
                        <Col span={12}>
                            <Form.Item
                                label="그리드 수"
                                name={['parameters', 'gridLevels']}
                                rules={[{ required: true, message: '그리드 수를 입력하세요' }]}
                            >
                                <InputNumber
                                    min={2}
                                    max={50}
                                    step={1}
                                    style={{ width: '100%' }}
                                    placeholder="예: 10"
                                />
                            </Form.Item>
                        </Col>
                        <Col span={12}>
                            <Form.Item
                                label="그리드 간격 (%)"
                                name={['parameters', 'gridSpacing']}
                                rules={[{ required: true, message: '그리드 간격을 입력하세요' }]}
                            >
                                <InputNumber
                                    min={0.1}
                                    max={10}
                                    step={0.1}
                                    style={{ width: '100%' }}
                                    placeholder="예: 0.5"
                                />
                            </Form.Item>
                        </Col>
                    </>
                );

            default:
                return commonFields;
        }
    };

    return (
        <Card
            title={
                <span>
                    <EditOutlined style={{ marginRight: 8 }} />
                    {strategy ? '전략 수정' : '새 전략 생성'}
                </span>
            }
        >
            <Form
                form={form}
                layout="vertical"
                onFinish={handleSubmit}
                initialValues={{
                    type: 'TREND_FOLLOWING',
                    timeframe: '1h',
                    symbols: [],
                    parameters: {
                        stopLoss: 2.0,
                        takeProfit: 5.0,
                        positionSize: 10,
                        leverage: 5,
                    },
                }}
            >
                <Divider orientation="left">기본 정보</Divider>
                <Row gutter={16}>
                    <Col span={12}>
                        <Form.Item
                            label="전략명"
                            name="name"
                            rules={[{ required: true, message: '전략명을 입력하세요' }]}
                        >
                            <Input placeholder="예: Momentum Trading" />
                        </Form.Item>
                    </Col>
                    <Col span={12}>
                        <Form.Item
                            label="전략 유형"
                            name="type"
                            rules={[{ required: true, message: '전략 유형을 선택하세요' }]}
                        >
                            <Select onChange={setStrategyType}>
                                <Option value="TREND_FOLLOWING">추세 추종</Option>
                                <Option value="MEAN_REVERSION">평균 회귀</Option>
                                <Option value="BREAKOUT">돌파</Option>
                                <Option value="GRID">그리드</Option>
                                <Option value="SCALPING">스캘핑</Option>
                            </Select>
                        </Form.Item>
                    </Col>
                    <Col span={24}>
                        <Form.Item
                            label="설명"
                            name="description"
                            rules={[{ required: true, message: '설명을 입력하세요' }]}
                        >
                            <TextArea
                                rows={3}
                                placeholder="전략에 대한 간단한 설명을 입력하세요"
                            />
                        </Form.Item>
                    </Col>
                </Row>

                <Divider orientation="left">거래 설정</Divider>
                <Row gutter={16}>
                    <Col span={12}>
                        <Form.Item
                            label="심볼"
                            name="symbols"
                            rules={[{ required: true, message: '최소 1개 심볼을 선택하세요' }]}
                        >
                            <Select mode="multiple" placeholder="거래할 심볼을 선택하세요">
                                <Option value="BTC/USDT">BTC/USDT</Option>
                                <Option value="ETH/USDT">ETH/USDT</Option>
                                <Option value="BNB/USDT">BNB/USDT</Option>
                                <Option value="SOL/USDT">SOL/USDT</Option>
                                <Option value="XRP/USDT">XRP/USDT</Option>
                                <Option value="ADA/USDT">ADA/USDT</Option>
                                <Option value="DOGE/USDT">DOGE/USDT</Option>
                            </Select>
                        </Form.Item>
                    </Col>
                    <Col span={12}>
                        <Form.Item
                            label="타임프레임"
                            name="timeframe"
                            rules={[{ required: true, message: '타임프레임을 선택하세요' }]}
                        >
                            <Select>
                                <Option value="1m">1분</Option>
                                <Option value="5m">5분</Option>
                                <Option value="15m">15분</Option>
                                <Option value="30m">30분</Option>
                                <Option value="1h">1시간</Option>
                                <Option value="4h">4시간</Option>
                                <Option value="1d">1일</Option>
                            </Select>
                        </Form.Item>
                    </Col>
                </Row>

                <Divider orientation="left">전략 파라미터</Divider>
                <Row gutter={16}>
                    {getParameterFields()}
                </Row>

                <Divider />
                <Form.Item>
                    <Space>
                        <Button
                            type="primary"
                            htmlType="submit"
                            icon={<SaveOutlined />}
                            loading={loading}
                        >
                            저장
                        </Button>
                        <Button
                            icon={<CloseOutlined />}
                            onClick={() => onCancel && onCancel()}
                        >
                            취소
                        </Button>
                    </Space>
                </Form.Item>
            </Form>
        </Card>
    );
}

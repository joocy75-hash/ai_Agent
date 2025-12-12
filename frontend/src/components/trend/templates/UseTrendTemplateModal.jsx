/**
 * UseTrendTemplateModal - AI 추세 봇 템플릿 사용 모달
 *
 * - USDT 정수 금액 입력
 * - 레버리지 선택
 * - 가용 잔액 표시
 * - 전략 정보 표시
 */
import React, { useState, useEffect } from 'react';
import {
    Modal,
    InputNumber,
    Select,
    Button,
    Collapse,
    Descriptions,
    message,
    Tag,
} from 'antd';
import {
    DownOutlined,
    ThunderboltOutlined,
    SafetyOutlined,
    ArrowUpOutlined,
    ArrowDownOutlined,
} from '@ant-design/icons';
import { trendTemplateAPI } from '../../../api/trendTemplate';
import './UseTrendTemplateModal.css';

const { Panel } = Collapse;
const { Option } = Select;

const LEVERAGE_OPTIONS = [1, 2, 3, 5, 10, 20, 25, 50, 75, 100, 125];

const UseTrendTemplateModal = ({
    visible,
    template,
    onClose,
    onSuccess,
    availableBalance = 0,
}) => {
    const [investmentAmount, setInvestmentAmount] = useState(0);
    const [leverage, setLeverage] = useState(5);
    const [loading, setLoading] = useState(false);

    // 템플릿 변경 시 초기값 설정
    useEffect(() => {
        if (template) {
            const minInv = Math.ceil(parseFloat(template.min_investment) || 50);
            setInvestmentAmount(minInv);
            setLeverage(template.leverage || 5);
        }
    }, [template]);

    const handleAmountChange = (value) => {
        // 정수만 허용
        setInvestmentAmount(Math.floor(value || 0));
    };

    const handleConfirm = async () => {
        if (!template) return;

        // 검증
        const minInv = Math.ceil(parseFloat(template.min_investment));
        if (investmentAmount < minInv) {
            message.error(`최소 투자금액은 ${minInv} USDT 입니다`);
            return;
        }

        if (investmentAmount > availableBalance) {
            message.error('잔액이 부족합니다');
            return;
        }

        setLoading(true);
        try {
            const result = await trendTemplateAPI.useTemplate(template.id, {
                investment_amount: investmentAmount,
                leverage: leverage,
            });

            message.success('AI 추세 봇이 생성되었습니다!');
            onSuccess?.(result);
            onClose();
        } catch (error) {
            console.error('Failed to create trend bot:', error);
            message.error(error.response?.data?.detail || '봇 생성 실패');
        } finally {
            setLoading(false);
        }
    };

    if (!template) return null;

    const minInvestment = Math.ceil(parseFloat(template.min_investment) || 50);
    const roiValue = template.backtest_roi_30d || 0;
    const winRate = template.backtest_win_rate || 0;
    const isLong = template.direction === 'long';
    const isBoth = template.direction === 'both';

    const getRiskLabel = (level) => {
        switch (level) {
            case 'low': return '저위험';
            case 'medium': return '중위험';
            case 'high': return '고위험';
            default: return level;
        }
    };

    const getRiskColor = (level) => {
        switch (level) {
            case 'low': return '#34c759';
            case 'medium': return '#ff9500';
            case 'high': return '#ff3b30';
            default: return '#86868b';
        }
    };

    const getStrategyLabel = (type) => {
        switch (type) {
            case 'ema_crossover': return 'EMA 크로스오버';
            case 'rsi_divergence': return 'RSI 다이버전스';
            case 'macd_trend': return 'MACD 추세';
            case 'bollinger_bands': return '볼린저밴드';
            default: return type;
        }
    };

    return (
        <Modal
            open={visible}
            onCancel={onClose}
            footer={null}
            width={500}
            className="use-trend-template-modal"
            title={null}
            closable={true}
        >
            <div className="modal-content">
                {/* 헤더: 템플릿 정보 */}
                <div className="modal-header">
                    <h2>{template.symbol}</h2>
                    <div className="header-tags">
                        <span className="tag strategy">
                            <ThunderboltOutlined /> {getStrategyLabel(template.strategy_type)}
                        </span>
                        <span className={`tag ${template.direction}`}>
                            {isBoth ? '양방향' :
                                isLong ? <><ArrowUpOutlined /> Long</> :
                                    <><ArrowDownOutlined /> Short</>}
                        </span>
                        <span className="tag">{template.leverage}x</span>
                    </div>
                </div>

                {/* 통계 정보 */}
                <div className="modal-stats">
                    <div className="stat-item">
                        <span className="stat-label">30일 백테스트 ROI</span>
                        <span className={`stat-value ${roiValue >= 0 ? 'positive' : 'negative'}`}>
                            {roiValue >= 0 ? '+' : ''}{roiValue.toFixed(2)}%
                        </span>
                    </div>
                    <div className="stat-item">
                        <span className="stat-label">승률</span>
                        <span className={`stat-value ${winRate >= 50 ? 'positive' : 'negative'}`}>
                            {winRate.toFixed(1)}%
                        </span>
                    </div>
                    <div className="stat-item">
                        <span className="stat-label">최대 손실</span>
                        <span className="stat-value">{(template.backtest_max_drawdown || 0).toFixed(2)}%</span>
                    </div>
                </div>

                {/* 리스크 레벨 */}
                <div className="risk-level-section">
                    <SafetyOutlined style={{ color: getRiskColor(template.risk_level) }} />
                    <span style={{ color: getRiskColor(template.risk_level) }}>
                        {getRiskLabel(template.risk_level)}
                    </span>
                    <Tag color="default" className="risk-tags">
                        SL: {template.stop_loss_percent}% / TP: {template.take_profit_percent}%
                    </Tag>
                </div>

                {/* 투자금액 입력 */}
                <div className="investment-section">
                    <h3>투자 금액 설정</h3>

                    <div className="margin-input">
                        <label>투자금액 (USDT)</label>
                        <div className="input-row">
                            <InputNumber
                                value={investmentAmount}
                                onChange={handleAmountChange}
                                min={minInvestment}
                                max={Math.floor(availableBalance)}
                                step={10}
                                precision={0}
                                className="amount-input"
                                style={{ width: '100%' }}
                                placeholder={`최소 ${minInvestment} USDT`}
                            />
                        </div>
                    </div>

                    <div className="margin-input" style={{ marginTop: 16 }}>
                        <label>레버리지</label>
                        <div className="input-row">
                            <Select
                                value={leverage}
                                onChange={setLeverage}
                                className="leverage-select"
                                style={{ width: '100%' }}
                            >
                                {LEVERAGE_OPTIONS.map((lev) => (
                                    <Option key={lev} value={lev}>{lev}x</Option>
                                ))}
                            </Select>
                        </div>
                    </div>

                    {/* 가용 잔액 */}
                    <div className="balance-row" style={{ marginTop: 16 }}>
                        <span className="balance-label">가용 잔액</span>
                        <span className="balance-value">{Math.floor(availableBalance)} USDT</span>
                    </div>
                </div>

                {/* 파라미터 펼치기 */}
                <Collapse
                    ghost
                    expandIcon={({ isActive }) => <DownOutlined rotate={isActive ? 180 : 0} />}
                    className="parameters-collapse"
                >
                    <Panel header="전략 상세 정보" key="1">
                        <Descriptions column={1} size="small">
                            <Descriptions.Item label="전략 타입">
                                {getStrategyLabel(template.strategy_type)}
                            </Descriptions.Item>
                            <Descriptions.Item label="방향">
                                {isBoth ? '양방향' : isLong ? 'Long (매수)' : 'Short (매도)'}
                            </Descriptions.Item>
                            <Descriptions.Item label="손절">
                                {template.stop_loss_percent}%
                            </Descriptions.Item>
                            <Descriptions.Item label="익절">
                                {template.take_profit_percent}%
                            </Descriptions.Item>
                            <Descriptions.Item label="최소 투자금">
                                {minInvestment} USDT
                            </Descriptions.Item>
                            <Descriptions.Item label="리스크 레벨">
                                <span style={{ color: getRiskColor(template.risk_level) }}>
                                    {getRiskLabel(template.risk_level)}
                                </span>
                            </Descriptions.Item>
                        </Descriptions>
                    </Panel>
                </Collapse>

                {/* 확인 버튼 */}
                <Button
                    type="primary"
                    block
                    size="large"
                    onClick={handleConfirm}
                    loading={loading}
                    disabled={investmentAmount < minInvestment}
                    className="confirm-button"
                    style={{ marginTop: 20 }}
                >
                    AI 추세 봇 생성
                </Button>
            </div>
        </Modal>
    );
};

export default UseTrendTemplateModal;

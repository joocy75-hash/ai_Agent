/**
 * UseTrendTemplateModal - AI 추세 봇 생성 모달
 * 
 * 라이트 모드 + 코인 로고 + Long/Short 영어
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

// 코인 로고 URL 생성
const getCoinLogoUrl = (symbol) => {
    const coin = symbol.replace('USDT', '').replace('BUSD', '').toLowerCase();
    return `https://assets.coincap.io/assets/icons/${coin}@2x.png`;
};

// 심볼 포맷팅 (BTCUSDT -> BTC/USDT)
const formatSymbol = (symbol) => {
    if (symbol.endsWith('USDT')) {
        return symbol.replace('USDT', '/USDT');
    }
    if (symbol.endsWith('BUSD')) {
        return symbol.replace('BUSD', '/BUSD');
    }
    return symbol;
};

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

    useEffect(() => {
        if (template) {
            const minInv = Math.ceil(parseFloat(template.min_investment) || 50);
            setInvestmentAmount(minInv);
            setLeverage(template.leverage || 5);
        }
    }, [template]);

    const handleAmountChange = (value) => {
        setInvestmentAmount(Math.floor(value || 0));
    };

    const handleConfirm = async () => {
        if (!template) return;

        const minInv = Math.ceil(parseFloat(template.min_investment));
        if (investmentAmount < minInv) {
            message.error(`최소 ${minInv} USDT 이상 입력해주세요`);
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

            message.success('🎉 AI 추세 봇이 생성되었습니다!');
            onSuccess?.(result);
            onClose();
        } catch (error) {
            console.error('Failed to create trend bot:', error);
            message.error(error.response?.data?.detail || '봇 생성에 실패했습니다. 다시 시도해주세요.');
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
            case 'low': return '안전';
            case 'medium': return '보통';
            case 'high': return '공격적';
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
            case 'ema_crossover': return 'EMA 교차 전략';
            case 'rsi_divergence': return 'RSI 반전 전략';
            case 'macd_trend': return 'MACD 추세 전략';
            case 'bollinger_bands': return '볼린저밴드 전략';
            default: return type;
        }
    };

    const getDirectionText = () => {
        if (isBoth) return 'Long/Short (상승/하락 모두)';
        if (isLong) return 'Long (상승 시 수익)';
        return 'Short (하락 시 수익)';
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
                {/* 헤더 */}
                <div className="modal-header">
                    <div className="symbol-with-logo">
                        <img
                            src={getCoinLogoUrl(template.symbol)}
                            alt={template.symbol}
                            className="coin-logo-large"
                            onError={(e) => { e.target.style.display = 'none'; }}
                        />
                        <h2>{formatSymbol(template.symbol)}</h2>
                    </div>
                    <div className="header-tags">
                        <span className="tag strategy">
                            <ThunderboltOutlined /> {getStrategyLabel(template.strategy_type)}
                        </span>
                        <span className={`tag ${template.direction}`}>
                            {isBoth ? 'Long/Short' :
                                isLong ? <><ArrowUpOutlined /> Long</> :
                                    <><ArrowDownOutlined /> Short</>}
                        </span>
                        <span className="tag">{template.leverage}X</span>
                    </div>
                </div>

                {/* 예상 성과 */}
                <div className="modal-stats">
                    <div className="stat-item">
                        <span className="stat-label">30일 예상 수익률</span>
                        <span className={`stat-value ${roiValue >= 0 ? 'positive' : 'negative'}`}>
                            {roiValue >= 0 ? '+' : ''}{roiValue.toFixed(1)}%
                        </span>
                    </div>
                    <div className="stat-item">
                        <span className="stat-label">승률</span>
                        <span className={`stat-value ${winRate >= 50 ? 'positive' : 'negative'}`}>
                            {winRate.toFixed(0)}%
                        </span>
                    </div>
                    <div className="stat-item">
                        <span className="stat-label">최대 손실</span>
                        <span className="stat-value">-{(template.backtest_max_drawdown || 0).toFixed(1)}%</span>
                    </div>
                </div>

                {/* 위험도 */}
                <div className="risk-level-section">
                    <SafetyOutlined style={{ color: getRiskColor(template.risk_level) }} />
                    <span style={{ color: getRiskColor(template.risk_level) }}>
                        위험도: {getRiskLabel(template.risk_level)}
                    </span>
                    <Tag className="risk-tags">
                        손절 {template.stop_loss_percent}% / 익절 {template.take_profit_percent}%
                    </Tag>
                </div>

                {/* 투자 설정 */}
                <div className="investment-section">
                    <h3>💰 투자 금액 설정</h3>

                    <div className="margin-input">
                        <label>투자할 금액 (USDT)</label>
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
                        <label>레버리지 (배율)</label>
                        <div className="input-row">
                            <Select
                                value={leverage}
                                onChange={setLeverage}
                                className="leverage-select"
                                style={{ width: '100%' }}
                            >
                                {LEVERAGE_OPTIONS.map((lev) => (
                                    <Option key={lev} value={lev}>{lev}X</Option>
                                ))}
                            </Select>
                        </div>
                    </div>

                    {/* 사용 가능 잔액 */}
                    <div className="balance-row" style={{ marginTop: 16 }}>
                        <span className="balance-label">사용 가능 금액</span>
                        <span className="balance-value">{Math.floor(availableBalance).toLocaleString()} USDT</span>
                    </div>
                </div>

                {/* 상세 정보 */}
                <Collapse
                    ghost
                    expandIcon={({ isActive }) => <DownOutlined rotate={isActive ? 180 : 0} />}
                    className="parameters-collapse"
                >
                    <Panel header="📋 전략 상세 정보 보기" key="1">
                        <Descriptions column={1} size="small">
                            <Descriptions.Item label="전략 유형">
                                {getStrategyLabel(template.strategy_type)}
                            </Descriptions.Item>
                            <Descriptions.Item label="거래 방향">
                                {getDirectionText()}
                            </Descriptions.Item>
                            <Descriptions.Item label="손절 설정">
                                가격이 {template.stop_loss_percent}% 하락 시 자동 매도
                            </Descriptions.Item>
                            <Descriptions.Item label="익절 설정">
                                가격이 {template.take_profit_percent}% 상승 시 자동 매도
                            </Descriptions.Item>
                            <Descriptions.Item label="최소 투자금">
                                {minInvestment.toLocaleString()} USDT
                            </Descriptions.Item>
                            <Descriptions.Item label="위험도">
                                <span style={{ color: getRiskColor(template.risk_level) }}>
                                    {getRiskLabel(template.risk_level)}
                                </span>
                            </Descriptions.Item>
                        </Descriptions>
                    </Panel>
                </Collapse>

                {/* 시작 버튼 */}
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
                    🚀 AI 봇 시작하기
                </Button>
            </div>
        </Modal>
    );
};

export default UseTrendTemplateModal;

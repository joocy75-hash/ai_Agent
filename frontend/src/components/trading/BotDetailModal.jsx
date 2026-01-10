/**
 * BotDetailModal - 봇 상세 정보 및 시작 모달
 *
 * Bitget 스타일 다크 테마 모달
 * - 템플릿 상세 정보 표시
 * - 투자 금액 입력
 * - 잔고 검증
 * - 봇 시작
 */
import React, { useState, useEffect } from 'react';
import {
    Modal,
    InputNumber,
    Button,
    Space,
    Tag,
    Statistic,
    Row,
    Col,
    Alert,
    Divider,
} from 'antd';
import {
    ArrowUpOutlined,
    ArrowDownOutlined,
    ThunderboltOutlined,
    DollarOutlined,
    PercentageOutlined,
    SafetyOutlined,
    RocketOutlined,
    UserOutlined,
} from '@ant-design/icons';
import multibotAPI from '../../api/multibot';
import './styles/BotDetailModal.css';

const BotDetailModal = ({
    open,
    template,
    onClose,
    onStart,
    availableBalance = 0,
}) => {
    const [amount, setAmount] = useState(100);
    const [loading, setLoading] = useState(false);
    const [balanceCheck, setBalanceCheck] = useState(null);
    const [checkingBalance, setCheckingBalance] = useState(false);

    // 템플릿 변경 시 금액 초기화
    useEffect(() => {
        if (template) {
            const defaultAmount = Math.max(
                template.min_investment || 50,
                100
            );
            setAmount(defaultAmount);
            setBalanceCheck(null);
        }
    }, [template]);

    // 금액 변경 시 잔고 확인
    useEffect(() => {
        if (!open || !amount) return;

        const checkBalance = async () => {
            setCheckingBalance(true);
            try {
                const result = await multibotAPI.checkBalance(amount);
                setBalanceCheck(result);
            } catch (err) {
                setBalanceCheck({ available: false, message: err.message });
            } finally {
                setCheckingBalance(false);
            }
        };

        const debounce = setTimeout(checkBalance, 300);
        return () => clearTimeout(debounce);
    }, [amount, open]);

    if (!template) return null;

    const {
        symbol,
        direction,
        leverage,
        backtest_roi_30d,
        min_investment,
        max_investment,
        stop_loss_percent,
        take_profit_percent,
        active_users,
        is_featured,
        strategy_type,
        description,
    } = template;

    const isLong = direction === 'long';
    const isBoth = direction === 'both';
    const roiValue = backtest_roi_30d || 0;
    const isPositiveRoi = roiValue >= 0;
    const minInvest = min_investment || 50;
    const maxInvest = max_investment || 10000;

    // 퍼센트 버튼 클릭
    const handlePercentClick = (percent) => {
        const newAmount = Math.floor(availableBalance * percent);
        setAmount(Math.max(minInvest, Math.min(newAmount, maxInvest)));
    };

    // 시작 버튼 클릭
    const handleStart = async () => {
        if (amount < minInvest) {
            return;
        }
        if (!balanceCheck?.available) {
            return;
        }

        setLoading(true);
        try {
            await onStart(template.id, amount);
        } finally {
            setLoading(false);
        }
    };

    // 검증 상태
    const isAmountValid = amount >= minInvest && amount <= maxInvest;
    const canStart = isAmountValid && balanceCheck?.available && !loading;

    return (
        <Modal
            className="bot-detail-modal"
            open={open}
            onCancel={onClose}
            footer={null}
            width={520}
            centered
            destroyOnClose
        >
            {/* 헤더 */}
            <div className="modal-header">
                <div className="header-left">
                    <h2 className="symbol-title">
                        {symbol?.replace('USDT', '/USDT')}
                    </h2>
                    <div className="header-tags">
                        <Tag className={`direction-tag ${isLong ? 'long' : isBoth ? 'both' : 'short'}`}>
                            {isBoth ? 'Long/Short' :
                                isLong ? <><ArrowUpOutlined /> Long</> :
                                    <><ArrowDownOutlined /> Short</>}
                        </Tag>
                        <Tag className="leverage-tag">{leverage}x</Tag>
                        {is_featured && (
                            <Tag className="hot-tag">
                                <ThunderboltOutlined /> HOT
                            </Tag>
                        )}
                    </div>
                </div>
            </div>

            <Divider className="modal-divider" />

            {/* 통계 그리드 */}
            <Row gutter={[16, 16]} className="stats-grid">
                <Col span={12}>
                    <Statistic
                        title="30-day APY"
                        value={roiValue}
                        precision={2}
                        prefix={isPositiveRoi ? '+' : ''}
                        suffix="%"
                        valueStyle={{
                            color: isPositiveRoi ? '#00d26a' : '#ff4757',
                            fontSize: '24px',
                            fontWeight: 700,
                        }}
                    />
                </Col>
                <Col span={12}>
                    <Statistic
                        title="Active Users"
                        value={active_users || 0}
                        prefix={<UserOutlined />}
                        valueStyle={{ fontSize: '24px' }}
                    />
                </Col>
            </Row>

            {/* 전략 설명 */}
            {description && (
                <div className="strategy-description">
                    <h4><RocketOutlined /> Strategy</h4>
                    <p>{description}</p>
                </div>
            )}

            {/* 파라미터 */}
            <div className="parameters-section">
                <h4><SafetyOutlined /> Parameters</h4>
                <div className="param-grid">
                    <div className="param-item">
                        <span className="param-label">Stop Loss</span>
                        <span className="param-value loss">
                            -{stop_loss_percent || 5}%
                        </span>
                    </div>
                    <div className="param-item">
                        <span className="param-label">Take Profit</span>
                        <span className="param-value profit">
                            +{take_profit_percent || 10}%
                        </span>
                    </div>
                    <div className="param-item">
                        <span className="param-label">Min Investment</span>
                        <span className="param-value">
                            {minInvest} USDT
                        </span>
                    </div>
                    <div className="param-item">
                        <span className="param-label">Strategy Type</span>
                        <span className="param-value">
                            {strategy_type || 'AI Fusion'}
                        </span>
                    </div>
                </div>
            </div>

            <Divider className="modal-divider" />

            {/* 금액 입력 */}
            <div className="amount-section">
                <div className="amount-header">
                    <h4><DollarOutlined /> Investment Amount</h4>
                    <span className="available-balance">
                        Available: <strong>${availableBalance.toFixed(2)}</strong>
                    </span>
                </div>

                <InputNumber
                    className="amount-input"
                    value={amount}
                    onChange={setAmount}
                    min={minInvest}
                    max={Math.min(maxInvest, availableBalance)}
                    step={10}
                    precision={2}
                    addonAfter="USDT"
                    size="large"
                    status={!isAmountValid ? 'error' : ''}
                />

                {/* 퍼센트 버튼 */}
                <Space className="percent-buttons">
                    <Button
                        size="small"
                        onClick={() => handlePercentClick(0.25)}
                    >
                        25%
                    </Button>
                    <Button
                        size="small"
                        onClick={() => handlePercentClick(0.5)}
                    >
                        50%
                    </Button>
                    <Button
                        size="small"
                        onClick={() => handlePercentClick(0.75)}
                    >
                        75%
                    </Button>
                    <Button
                        size="small"
                        onClick={() => handlePercentClick(1)}
                    >
                        MAX
                    </Button>
                </Space>

                {/* 잔고 확인 결과 */}
                {balanceCheck && !balanceCheck.available && (
                    <Alert
                        type="error"
                        message={balanceCheck.message || '잔고가 부족합니다'}
                        showIcon
                        className="balance-alert"
                    />
                )}

                {amount < minInvest && (
                    <Alert
                        type="warning"
                        message={`최소 투자 금액은 ${minInvest} USDT입니다`}
                        showIcon
                        className="balance-alert"
                    />
                )}
            </div>

            {/* 시작 버튼 */}
            <Button
                className="start-button"
                type="primary"
                size="large"
                block
                loading={loading || checkingBalance}
                disabled={!canStart}
                onClick={handleStart}
            >
                {loading ? 'Starting...' : 'Start Bot'}
            </Button>
        </Modal>
    );
};

export default BotDetailModal;

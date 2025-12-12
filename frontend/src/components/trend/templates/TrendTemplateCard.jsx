/**
 * TrendTemplateCard - AI 추세 봇 템플릿 카드
 *
 * 표시 정보:
 * - 심볼, 방향, 레버리지 태그
 * - 30D ROI (%), 승률
 * - 손절/익절 설정
 * - 리스크 레벨
 * - 최소 투자금액
 * - 사용자 수
 * - Use 버튼
 */
import React from 'react';
import { Button, Tag, Tooltip } from 'antd';
import {
    UserOutlined,
    ThunderboltOutlined,
    ArrowUpOutlined,
    ArrowDownOutlined,
    SafetyOutlined
} from '@ant-design/icons';
import './TrendTemplateCard.css';

const TrendTemplateCard = ({
    template,
    onUse,
    loading = false,
}) => {
    const {
        name,
        symbol,
        direction,
        leverage,
        strategy_type,
        backtest_roi_30d,
        backtest_win_rate,
        backtest_max_drawdown,
        stop_loss_percent,
        take_profit_percent,
        min_investment,
        risk_level,
        active_users,
        is_featured,
    } = template;

    const isLong = direction === 'long';
    const isBoth = direction === 'both';
    const roiValue = backtest_roi_30d || 0;
    const isPositiveRoi = roiValue >= 0;
    const winRate = backtest_win_rate || 0;

    const getRiskColor = (level) => {
        switch (level) {
            case 'low': return '#34c759';
            case 'medium': return '#ff9500';
            case 'high': return '#ff3b30';
            default: return '#86868b';
        }
    };

    const getRiskLabel = (level) => {
        switch (level) {
            case 'low': return '저위험';
            case 'medium': return '중위험';
            case 'high': return '고위험';
            default: return level;
        }
    };

    const getStrategyLabel = (type) => {
        switch (type) {
            case 'ema_crossover': return 'EMA 크로스';
            case 'rsi_divergence': return 'RSI 다이버전스';
            case 'macd_trend': return 'MACD 추세';
            case 'bollinger_bands': return '볼린저밴드';
            default: return type;
        }
    };

    return (
        <div className={`trend-template-card ${is_featured ? 'featured' : ''}`}>
            {/* 상단 영역: 심볼 + Use 버튼 */}
            <div className="trend-card-header">
                <div className="trend-symbol-section">
                    <h3 className="trend-symbol">{symbol}</h3>
                    <div className="trend-tags">
                        <Tag className="tag-strategy">
                            <ThunderboltOutlined /> {getStrategyLabel(strategy_type)}
                        </Tag>
                        <Tag className={`tag-direction ${isLong ? 'long' : isBoth ? 'both' : 'short'}`}>
                            {isBoth ? <>양방향</> :
                                isLong ? <><ArrowUpOutlined /> Long</> :
                                    <><ArrowDownOutlined /> Short</>}
                        </Tag>
                        <Tag className="tag-leverage">{leverage}X</Tag>
                    </div>
                </div>

                <Button
                    type="primary"
                    className="use-button"
                    onClick={() => onUse(template)}
                    loading={loading}
                >
                    사용하기
                </Button>
            </div>

            {/* 중앙 영역: ROI + 승률 */}
            <div className="trend-card-body">
                <div className="stat-grid">
                    <div className="stat-item main">
                        <span className="stat-label">30일 백테스트 ROI</span>
                        <span className={`stat-value ${isPositiveRoi ? 'positive' : 'negative'}`}>
                            {isPositiveRoi ? '+' : ''}{roiValue.toFixed(2)}%
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
                        <span className="stat-value negative">
                            {(backtest_max_drawdown || 0).toFixed(2)}%
                        </span>
                    </div>
                </div>

                {/* 손절/익절 설정 */}
                <div className="risk-settings">
                    <Tooltip title="손절 설정">
                        <span className="risk-badge sl">
                            SL: {stop_loss_percent}%
                        </span>
                    </Tooltip>
                    <Tooltip title="익절 설정">
                        <span className="risk-badge tp">
                            TP: {take_profit_percent}%
                        </span>
                    </Tooltip>
                </div>
            </div>

            {/* 하단 영역: 추가 정보 */}
            <div className="trend-card-footer">
                <div className="footer-row">
                    <span className="footer-label">리스크 레벨</span>
                    <span
                        className="footer-value risk-level"
                        style={{ color: getRiskColor(risk_level) }}
                    >
                        <SafetyOutlined /> {getRiskLabel(risk_level)}
                    </span>
                </div>
                <div className="footer-row">
                    <span className="footer-label">최소 투자금</span>
                    <span className="footer-value">{parseFloat(min_investment || 0).toFixed(0)} USDT</span>

                    <span className="user-count">
                        <UserOutlined /> {active_users || 0}
                    </span>
                </div>
            </div>

            {/* Featured 배지 */}
            {is_featured && (
                <div className="featured-badge">
                    <ThunderboltOutlined /> HOT
                </div>
            )}
        </div>
    );
};

export default TrendTemplateCard;

/**
 * TrendTemplateCard - AI 추세 봇 템플릿 카드
 * 
 * 라이트 모드 + 코인 로고 + Long/Short 영어
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

// 코인 로고 URL 생성
const getCoinLogoUrl = (symbol) => {
    // BTCUSDT -> btc
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
            case 'low': return '안전';
            case 'medium': return '보통';
            case 'high': return '공격적';
            default: return level;
        }
    };

    const getStrategyLabel = (type) => {
        switch (type) {
            case 'ema_crossover': return 'EMA 교차';
            case 'rsi_divergence': return 'RSI 반전';
            case 'macd_trend': return 'MACD 추세';
            case 'bollinger_bands': return '볼린저밴드';
            default: return type;
        }
    };

    return (
        <div className={`trend-template-card ${is_featured ? 'featured' : ''}`}>
            {/* 상단: 심볼 + 사용 버튼 */}
            <div className="trend-card-header">
                <div className="trend-symbol-section">
                    <div className="symbol-with-logo">
                        <img
                            src={getCoinLogoUrl(symbol)}
                            alt={symbol}
                            className="coin-logo"
                            onError={(e) => { e.target.style.display = 'none'; }}
                        />
                        <h3 className="trend-symbol">{formatSymbol(symbol)}</h3>
                    </div>
                    <div className="trend-tags">
                        <Tag className="tag-strategy">
                            <ThunderboltOutlined /> {getStrategyLabel(strategy_type)}
                        </Tag>
                        <Tag className={`tag-direction ${isLong ? 'long' : isBoth ? 'both' : 'short'}`}>
                            {isBoth ? 'Long/Short' :
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

            {/* 중앙: 수익률 + 승률 */}
            <div className="trend-card-body">
                <div className="stat-grid">
                    <div className="stat-item main">
                        <span className="stat-label">30일 예상 수익률</span>
                        <span className={`stat-value ${isPositiveRoi ? 'positive' : 'negative'}`}>
                            {isPositiveRoi ? '+' : ''}{roiValue.toFixed(1)}%
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
                        <span className="stat-value negative">
                            -{(backtest_max_drawdown || 0).toFixed(1)}%
                        </span>
                    </div>
                </div>

                {/* 손절/익절 설정 */}
                <div className="risk-settings">
                    <Tooltip title="손실이 이 비율에 도달하면 자동으로 매도합니다">
                        <span className="risk-badge sl">
                            손절 {stop_loss_percent}%
                        </span>
                    </Tooltip>
                    <Tooltip title="이익이 이 비율에 도달하면 자동으로 매도합니다">
                        <span className="risk-badge tp">
                            익절 {take_profit_percent}%
                        </span>
                    </Tooltip>
                </div>
            </div>

            {/* 하단: 추가 정보 */}
            <div className="trend-card-footer">
                <div className="footer-row">
                    <span className="footer-label">위험도</span>
                    <span
                        className="footer-value risk-level"
                        style={{ color: getRiskColor(risk_level) }}
                    >
                        <SafetyOutlined /> {getRiskLabel(risk_level)}
                    </span>
                </div>
                <div className="footer-row">
                    <span className="footer-label">최소 금액</span>
                    <span className="footer-value">{parseFloat(min_investment || 0).toFixed(0)} USDT</span>
                    <span className="user-count">
                        <UserOutlined /> {active_users || 0}명 사용중
                    </span>
                </div>
            </div>

            {/* HOT 배지 */}
            {is_featured && (
                <div className="featured-badge">
                    <ThunderboltOutlined /> 추천
                </div>
            )}
        </div>
    );
};

export default TrendTemplateCard;

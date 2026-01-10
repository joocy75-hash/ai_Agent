/**
 * BotCard - Bitget 스타일 봇 템플릿 카드
 *
 * 다크 테마 + 미니 차트 + Use 버튼
 * 멀티봇 시스템에서 사용자가 봇 템플릿을 선택할 때 표시되는 카드
 */
import React, { useMemo } from 'react';
import { Button, Tag, Tooltip } from 'antd';
import {
    UserOutlined,
    ThunderboltOutlined,
    ArrowUpOutlined,
    ArrowDownOutlined,
    ClockCircleOutlined,
    DollarOutlined
} from '@ant-design/icons';
import './styles/BotCard.css';

// 코인 로고 URL 생성 (CoinCap API 사용)
const getCoinLogoUrl = (symbol) => {
    // BTCUSDT -> btc, ETHUSDT -> eth
    const coin = symbol
        .replace('USDT', '')
        .replace('BUSD', '')
        .replace('USDC', '')
        .toLowerCase();
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
    if (symbol.endsWith('USDC')) {
        return symbol.replace('USDC', '/USDC');
    }
    return symbol;
};

// 미니 라인 차트 SVG 생성
const MiniChart = ({ isPositive }) => {
    // 랜덤한 차트 데이터 생성 (상승/하락 트렌드)
    const points = useMemo(() => {
        const data = [];
        let value = 50;
        const trend = isPositive ? 0.8 : -0.8;

        for (let i = 0; i < 20; i++) {
            // 트렌드 + 약간의 랜덤 변동
            value += trend + (Math.random() - 0.5) * 3;
            // 범위 제한 (10-90)
            value = Math.max(10, Math.min(90, value));
            data.push(value);
        }
        return data;
    }, [isPositive]);

    // SVG path 생성
    const pathData = points
        .map((val, idx) => {
            const x = (idx / (points.length - 1)) * 100;
            const y = 100 - val;
            return `${idx === 0 ? 'M' : 'L'} ${x} ${y}`;
        })
        .join(' ');

    const strokeColor = isPositive ? '#00d26a' : '#ff4757';

    return (
        <svg
            className="mini-chart"
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
        >
            {/* 그라데이션 정의 */}
            <defs>
                <linearGradient
                    id={`gradient-${isPositive ? 'positive' : 'negative'}`}
                    x1="0%" y1="0%" x2="0%" y2="100%"
                >
                    <stop
                        offset="0%"
                        stopColor={strokeColor}
                        stopOpacity="0.3"
                    />
                    <stop
                        offset="100%"
                        stopColor={strokeColor}
                        stopOpacity="0"
                    />
                </linearGradient>
            </defs>

            {/* 영역 채우기 */}
            <path
                d={`${pathData} L 100 100 L 0 100 Z`}
                fill={`url(#gradient-${isPositive ? 'positive' : 'negative'})`}
            />

            {/* 라인 */}
            <path
                d={pathData}
                fill="none"
                stroke={strokeColor}
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
            />
        </svg>
    );
};

// 전략 타입 라벨 변환
const getStrategyLabel = (type) => {
    const labels = {
        'ema_crossover': 'EMA 교차',
        'rsi_divergence': 'RSI 반전',
        'macd_trend': 'MACD 추세',
        'bollinger_bands': '볼린저밴드',
        'ai_fusion': 'AI 퓨전',
        'momentum': '모멘텀',
        'scalping': '스캘핑',
        'grid': '그리드',
    };
    return labels[type] || type || 'AI 전략';
};

const BotCard = ({
    template,
    onUse,
    loading = false,
}) => {
    const {
        id,
        symbol,
        direction,
        leverage,
        backtest_roi_30d,
        min_investment,
        active_users,
        is_featured,
        strategy_type,
    } = template;

    // 방향 판별
    const isLong = direction === 'long';
    const isBoth = direction === 'both';

    // ROI 값 처리
    const roiValue = backtest_roi_30d || 0;
    const isPositiveRoi = roiValue >= 0;

    // Use 버튼 클릭 핸들러
    const handleUseClick = () => {
        if (onUse) {
            onUse(template);
        }
    };

    return (
        <div className={`bot-card ${is_featured ? 'featured' : ''}`}>
            {/* HOT 배지 (추천 템플릿) */}
            {is_featured && (
                <div className="hot-badge">
                    <ThunderboltOutlined /> HOT
                </div>
            )}

            {/* 상단: 코인 정보 + 태그 */}
            <div className="bot-card-header">
                <div className="coin-info">
                    <img
                        src={getCoinLogoUrl(symbol)}
                        alt={symbol}
                        className="coin-logo"
                        onError={(e) => {
                            e.target.style.display = 'none';
                        }}
                    />
                    <div className="symbol-section">
                        <h3 className="symbol-name">{formatSymbol(symbol)}</h3>
                        <div className="symbol-tags">
                            {/* Long/Short 태그 */}
                            <Tag className={`direction-tag ${isLong ? 'long' : isBoth ? 'both' : 'short'}`}>
                                {isBoth ? 'Long/Short' :
                                    isLong ? <><ArrowUpOutlined /> Long</> :
                                        <><ArrowDownOutlined /> Short</>}
                            </Tag>
                            {/* 레버리지 태그 */}
                            <Tag className="leverage-tag">
                                {leverage}x
                            </Tag>
                        </div>
                    </div>
                </div>
            </div>

            {/* 중앙: ROI + 미니 차트 */}
            <div className="bot-card-body">
                <div className="roi-section">
                    <span className="roi-label">30-day APY</span>
                    <span className={`roi-value ${isPositiveRoi ? 'positive' : 'negative'}`}>
                        {isPositiveRoi ? '+' : ''}{roiValue.toFixed(2)}%
                    </span>
                </div>

                {/* 미니 SVG 라인 차트 */}
                <div className="chart-container">
                    <MiniChart isPositive={isPositiveRoi} />
                </div>
            </div>

            {/* 하단: 상세 정보 */}
            <div className="bot-card-footer">
                <div className="info-grid">
                    {/* 최소 투자금 */}
                    <div className="info-item">
                        <DollarOutlined className="info-icon" />
                        <div className="info-content">
                            <span className="info-label">Min investment</span>
                            <span className="info-value">
                                {parseFloat(min_investment || 50).toFixed(0)} USDT
                            </span>
                        </div>
                    </div>

                    {/* 운용 기간 */}
                    <div className="info-item">
                        <ClockCircleOutlined className="info-icon" />
                        <div className="info-content">
                            <span className="info-label">Duration</span>
                            <span className="info-value">Flexible</span>
                        </div>
                    </div>

                    {/* 사용자 수 */}
                    <div className="info-item">
                        <UserOutlined className="info-icon" />
                        <div className="info-content">
                            <span className="info-label">Users</span>
                            <span className="info-value">
                                {active_users || 0}
                            </span>
                        </div>
                    </div>
                </div>

                {/* 전략 타입 */}
                <Tooltip title={`전략: ${getStrategyLabel(strategy_type)}`}>
                    <div className="strategy-badge">
                        <ThunderboltOutlined /> {getStrategyLabel(strategy_type)}
                    </div>
                </Tooltip>
            </div>

            {/* Use 버튼 */}
            <Button
                className="use-button"
                onClick={handleUseClick}
                loading={loading}
            >
                Use
            </Button>
        </div>
    );
};

export default BotCard;

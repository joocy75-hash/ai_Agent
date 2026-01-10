/**
 * BotCard - 프리미엄 봇 템플릿 카드
 *
 * 미니멀 & 고급스러운 디자인
 * 멀티봇 시스템에서 사용자가 봇 템플릿을 선택할 때 표시되는 카드
 */
import { useMemo } from 'react';
import { Button, Tooltip } from 'antd';
import {
    ThunderboltOutlined,
    RiseOutlined,
    FallOutlined,
    SwapOutlined,
} from '@ant-design/icons';
import './styles/BotCard.css';

// 코인 로고 URL 매핑 (안정적인 CDN 사용)
const COIN_LOGOS = {
    btc: 'https://cryptologos.cc/logos/bitcoin-btc-logo.svg',
    eth: 'https://cryptologos.cc/logos/ethereum-eth-logo.svg',
    sol: 'https://cryptologos.cc/logos/solana-sol-logo.svg',
    bnb: 'https://cryptologos.cc/logos/bnb-bnb-logo.svg',
    xrp: 'https://cryptologos.cc/logos/xrp-xrp-logo.svg',
    doge: 'https://cryptologos.cc/logos/dogecoin-doge-logo.svg',
    ada: 'https://cryptologos.cc/logos/cardano-ada-logo.svg',
    avax: 'https://cryptologos.cc/logos/avalanche-avax-logo.svg',
    dot: 'https://cryptologos.cc/logos/polkadot-new-dot-logo.svg',
    link: 'https://cryptologos.cc/logos/chainlink-link-logo.svg',
    matic: 'https://cryptologos.cc/logos/polygon-matic-logo.svg',
    uni: 'https://cryptologos.cc/logos/uniswap-uni-logo.svg',
    atom: 'https://cryptologos.cc/logos/cosmos-atom-logo.svg',
    ltc: 'https://cryptologos.cc/logos/litecoin-ltc-logo.svg',
    etc: 'https://cryptologos.cc/logos/ethereum-classic-etc-logo.svg',
    fil: 'https://cryptologos.cc/logos/filecoin-fil-logo.svg',
    apt: 'https://cryptologos.cc/logos/aptos-apt-logo.svg',
    arb: 'https://cryptologos.cc/logos/arbitrum-arb-logo.svg',
    op: 'https://cryptologos.cc/logos/optimism-ethereum-op-logo.svg',
    near: 'https://cryptologos.cc/logos/near-protocol-near-logo.svg',
};

// 코인별 그라데이션 색상 (프리미엄 느낌)
const COIN_COLORS = {
    btc: { primary: '#F7931A', secondary: '#FFB84D' },
    eth: { primary: '#627EEA', secondary: '#8FA8FF' },
    sol: { primary: '#9945FF', secondary: '#14F195' },
    bnb: { primary: '#F3BA2F', secondary: '#FFD966' },
    xrp: { primary: '#23292F', secondary: '#5A6A7E' },
    doge: { primary: '#C2A633', secondary: '#E8D174' },
    ada: { primary: '#0033AD', secondary: '#2B5CFF' },
    avax: { primary: '#E84142', secondary: '#FF6B6B' },
    dot: { primary: '#E6007A', secondary: '#FF4DA6' },
    link: { primary: '#2A5ADA', secondary: '#5B8AFF' },
    matic: { primary: '#8247E5', secondary: '#A77DFF' },
    uni: { primary: '#FF007A', secondary: '#FF4DA6' },
    default: { primary: '#6366f1', secondary: '#818cf8' },
};

// 코인 로고 URL 생성
const getCoinLogoUrl = (symbol) => {
    const coin = symbol
        .replace('USDT', '')
        .replace('BUSD', '')
        .replace('USDC', '')
        .toLowerCase();
    return COIN_LOGOS[coin] || `https://assets.coincap.io/assets/icons/${coin}@2x.png`;
};

// 코인 색상 가져오기
const getCoinColors = (symbol) => {
    const coin = symbol
        .replace('USDT', '')
        .replace('BUSD', '')
        .replace('USDC', '')
        .toLowerCase();
    return COIN_COLORS[coin] || COIN_COLORS.default;
};

// 코인 이름만 추출 (BTC, ETH 등)
const getCoinName = (symbol) => {
    return symbol
        .replace('USDT', '')
        .replace('BUSD', '')
        .replace('USDC', '');
};

// 미니 스파크라인 차트 (더 심플한 버전)
const SparklineChart = ({ isPositive, color }) => {
    const points = useMemo(() => {
        const data = [];
        let value = 50;
        const trend = isPositive ? 0.6 : -0.6;

        for (let i = 0; i < 12; i++) {
            value += trend + (Math.random() - 0.5) * 4;
            value = Math.max(20, Math.min(80, value));
            data.push(value);
        }
        return data;
    }, [isPositive]);

    const pathData = points
        .map((val, idx) => {
            const x = (idx / (points.length - 1)) * 100;
            const y = 100 - val;
            return `${idx === 0 ? 'M' : 'L'} ${x} ${y}`;
        })
        .join(' ');

    return (
        <svg className="sparkline" viewBox="0 0 100 100" preserveAspectRatio="none">
            <defs>
                <linearGradient id={`spark-grad-${isPositive}`} x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" stopColor={color} stopOpacity="0.2" />
                    <stop offset="100%" stopColor={color} stopOpacity="0" />
                </linearGradient>
            </defs>
            <path
                d={`${pathData} L 100 100 L 0 100 Z`}
                fill={`url(#spark-grad-${isPositive})`}
            />
            <path
                d={pathData}
                fill="none"
                stroke={color}
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
            />
        </svg>
    );
};

// 방향 아이콘 컴포넌트
const DirectionIcon = ({ direction }) => {
    if (direction === 'both') {
        return <SwapOutlined />;
    }
    return direction === 'long' ? <RiseOutlined /> : <FallOutlined />;
};

// 전략 타입 라벨
const getStrategyLabel = (type) => {
    const labels = {
        'ema_crossover': 'EMA',
        'rsi_divergence': 'RSI',
        'macd_trend': 'MACD',
        'bollinger_bands': 'BB',
        'ai_fusion': 'AI Fusion',
        'momentum': 'Momentum',
        'scalping': 'Scalp',
        'grid': 'Grid',
    };
    return labels[type] || type || 'AI';
};

const BotCard = ({
    template,
    onUse,
    loading = false,
}) => {
    const {
        symbol,
        direction,
        leverage,
        backtest_roi_30d,
        min_investment,
        active_users,
        is_featured,
        strategy_type,
    } = template;

    // 코인 정보
    const coinName = getCoinName(symbol);
    const coinColors = getCoinColors(symbol);

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
        <div className={`bot-card-premium ${is_featured ? 'featured' : ''}`}>
            {/* 배경 그라데이션 효과 */}
            <div
                className="card-glow"
                style={{
                    background: `radial-gradient(ellipse at top left, ${coinColors.primary}15 0%, transparent 50%)`
                }}
            />

            {/* HOT 배지 */}
            {is_featured && (
                <div className="featured-badge">
                    <ThunderboltOutlined />
                </div>
            )}

            {/* 메인 콘텐츠 */}
            <div className="card-content">
                {/* 상단: 코인 로고 + 심볼 */}
                <div className="card-header">
                    <div className="coin-wrapper">
                        <div
                            className="coin-logo-container"
                            style={{
                                background: `linear-gradient(135deg, ${coinColors.primary}20, ${coinColors.secondary}10)`
                            }}
                        >
                            <img
                                src={getCoinLogoUrl(symbol)}
                                alt={coinName}
                                className="coin-logo"
                                onError={(e) => {
                                    e.target.src = `https://ui-avatars.com/api/?name=${coinName}&background=${coinColors.primary.slice(1)}&color=fff&size=64`;
                                }}
                            />
                        </div>
                        <div className="coin-details">
                            <span className="coin-name">{coinName}</span>
                            <span className="coin-pair">/ USDT</span>
                        </div>
                    </div>

                    {/* 태그들 */}
                    <div className="card-badges">
                        <span className={`direction-badge ${direction}`}>
                            <DirectionIcon direction={direction} />
                            {direction === 'both' ? 'Both' : direction === 'long' ? 'Long' : 'Short'}
                        </span>
                        <span className="leverage-badge">{leverage}×</span>
                    </div>
                </div>

                {/* 중앙: ROI 표시 */}
                <div className="card-body">
                    <div className="roi-display">
                        <div className="roi-header">
                            <span className="roi-label">30일 예상 수익률</span>
                            <Tooltip title={getStrategyLabel(strategy_type)}>
                                <span className="strategy-chip">
                                    <ThunderboltOutlined /> {getStrategyLabel(strategy_type)}
                                </span>
                            </Tooltip>
                        </div>
                        <div className={`roi-value ${isPositiveRoi ? 'positive' : 'negative'}`}>
                            {isPositiveRoi ? '+' : ''}{roiValue.toFixed(1)}%
                        </div>
                    </div>

                    {/* 스파크라인 차트 */}
                    <div className="sparkline-container">
                        <SparklineChart
                            isPositive={isPositiveRoi}
                            color={isPositiveRoi ? '#10b981' : '#ef4444'}
                        />
                    </div>
                </div>

                {/* 하단: 간단한 정보 + 버튼 */}
                <div className="card-footer">
                    <div className="footer-stats">
                        <div className="stat-item">
                            <span className="stat-value">${parseFloat(min_investment || 50).toFixed(0)}</span>
                            <span className="stat-label">최소</span>
                        </div>
                        <div className="stat-divider" />
                        <div className="stat-item">
                            <span className="stat-value">{active_users || 0}</span>
                            <span className="stat-label">사용자</span>
                        </div>
                    </div>

                    <Button
                        className="start-button"
                        onClick={handleUseClick}
                        loading={loading}
                        style={{
                            background: `linear-gradient(135deg, ${coinColors.primary}, ${coinColors.secondary})`,
                        }}
                    >
                        시작하기
                    </Button>
                </div>
            </div>
        </div>
    );
};

export default BotCard;

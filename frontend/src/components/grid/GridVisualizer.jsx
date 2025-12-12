/**
 * GridVisualizer Component
 *
 * 그리드 봇의 가격 레인지와 그리드 라인을 시각화하는 인터랙티브 컴포넌트
 * 라이트/다크 모드 지원
 *
 * 특징:
 * - 세로 방향 가격 축 (위=고가, 아래=저가)
 * - 그리드 라인별 상태 표시 (pending/buy_filled/sell_filled)
 * - 현재가 마커 애니메이션
 * - 체결된 주문에 펄스 효과
 *
 * @example
 * <GridVisualizer
 *   lowerPrice={85000}
 *   upperPrice={100000}
 *   gridCount={10}
 *   currentPrice={92500}
 *   orders={[{ grid_index: 0, status: 'buy_filled', ... }]}
 *   lightMode={true}
 * />
 */

import { useMemo } from 'react';
import { Tooltip, Typography } from 'antd';

const { Text } = Typography;

// 그리드 상태별 색상 (라이트 모드)
const STATUS_COLORS_LIGHT = {
    pending: { bg: '#f5f5f7', border: '#d2d2d7', glow: 'none' },
    buy_placed: { bg: '#e8f4fd', border: '#0071e3', glow: '0 0 8px rgba(0, 113, 227, 0.2)' },
    buy_filled: { bg: '#e3f9ed', border: '#34c759', glow: '0 0 12px rgba(52, 199, 89, 0.3)' },
    sell_placed: { bg: '#fff5e6', border: '#ff9500', glow: '0 0 8px rgba(255, 149, 0, 0.2)' },
    sell_filled: { bg: '#e8f4fd', border: '#0071e3', glow: '0 0 12px rgba(0, 113, 227, 0.3)' },
};

// 그리드 상태별 색상 (다크 모드)
const STATUS_COLORS_DARK = {
    pending: { bg: '#2d2d44', border: '#3d3d5c', glow: 'none' },
    buy_placed: { bg: '#1a3a4a', border: '#00A8FF', glow: '0 0 8px rgba(0, 168, 255, 0.3)' },
    buy_filled: { bg: '#0d3320', border: '#00C076', glow: '0 0 12px rgba(0, 192, 118, 0.4)' },
    sell_placed: { bg: '#3a2a1a', border: '#F5C242', glow: '0 0 8px rgba(245, 194, 66, 0.3)' },
    sell_filled: { bg: '#1a2a3a', border: '#00E5FF', glow: '0 0 12px rgba(0, 229, 255, 0.5)' },
};

export default function GridVisualizer({
    lowerPrice,
    upperPrice,
    gridCount = 10,
    gridMode = 'arithmetic',
    currentPrice,
    orders = [],
    totalInvestment,
    height = 400,
    showLabels = true,
    compact = false,
    onGridClick,
    lightMode = false,
}) {
    // 테마에 따른 색상 선택
    const STATUS_COLORS = lightMode ? STATUS_COLORS_LIGHT : STATUS_COLORS_DARK;

    // 테마 색상
    const theme = lightMode ? {
        background: 'linear-gradient(180deg, #f8f9fa 0%, #f0f0f5 100%)',
        border: '1px solid #e5e5ea',
        textPrimary: '#1d1d1f',
        textSecondary: '#86868b',
        axisGradient: 'linear-gradient(180deg, #34c759 0%, #0071e3 50%, #ff3b30 100%)',
        meshGradient1: 'rgba(52, 199, 89, 0.05)',
        meshGradient2: 'rgba(0, 113, 227, 0.05)',
        upperColor: '#34c759',
        lowerColor: '#ff3b30',
        currentPriceGradient: 'linear-gradient(90deg, transparent 0%, #ff9500 20%, #ff9500 80%, transparent 100%)',
        currentPriceGlow: 'rgba(255, 149, 0, 0.3)',
        currentPriceBg: 'linear-gradient(135deg, #ff9500 0%, #ff6b00 100%)',
        currentPriceText: '#ffffff',
        legendText: '#86868b',
    } : {
        background: 'linear-gradient(180deg, #0f1923 0%, #0a1015 100%)',
        border: '1px solid rgba(0, 229, 255, 0.15)',
        textPrimary: '#ffffff',
        textSecondary: 'rgba(255,255,255,0.5)',
        axisGradient: 'linear-gradient(180deg, #00C076 0%, #00A8FF 50%, #FF4D6A 100%)',
        meshGradient1: 'rgba(0, 192, 118, 0.08)',
        meshGradient2: 'rgba(0, 168, 255, 0.08)',
        upperColor: '#00C076',
        lowerColor: '#FF4D6A',
        currentPriceGradient: 'linear-gradient(90deg, transparent 0%, #F5C242 20%, #F5C242 80%, transparent 100%)',
        currentPriceGlow: 'rgba(245, 194, 66, 0.4)',
        currentPriceBg: 'linear-gradient(135deg, #F5C242 0%, #E5A020 100%)',
        currentPriceText: '#000000',
        legendText: 'rgba(255,255,255,0.5)',
    };

    // 그리드 라인 계산
    const gridLines = useMemo(() => {
        const lines = [];
        const priceRange = upperPrice - lowerPrice;

        for (let i = 0; i < gridCount; i++) {
            let price;
            if (gridMode === 'geometric') {
                // 기하급수적 간격 (로그 스케일)
                const ratio = Math.pow(upperPrice / lowerPrice, i / (gridCount - 1));
                price = lowerPrice * ratio;
            } else {
                // 균등 간격 (산술)
                price = lowerPrice + (priceRange * i) / (gridCount - 1);
            }

            // 해당 그리드의 주문 상태 찾기
            const order = orders.find((o) => o.grid_index === i);

            lines.push({
                index: i,
                price,
                status: order?.status || 'pending',
                order,
                // Y 위치 계산 (상단이 고가)
                yPercent: 100 - ((price - lowerPrice) / priceRange) * 100,
            });
        }

        return lines;
    }, [lowerPrice, upperPrice, gridCount, gridMode, orders]);

    // 현재가 위치 계산
    const currentPriceY = useMemo(() => {
        if (!currentPrice || currentPrice < lowerPrice || currentPrice > upperPrice) {
            return null;
        }
        const priceRange = upperPrice - lowerPrice;
        return 100 - ((currentPrice - lowerPrice) / priceRange) * 100;
    }, [currentPrice, lowerPrice, upperPrice]);

    // 그리드당 투자금
    const perGridAmount = totalInvestment ? (totalInvestment / gridCount).toFixed(2) : null;

    // 가격 포맷
    const formatPrice = (price) => {
        if (price >= 1000) return `$${(price / 1000).toFixed(1)}K`;
        if (price >= 1) return `$${price.toFixed(2)}`;
        return `$${price.toFixed(6)}`;
    };

    return (
        <div
            style={{
                position: 'relative',
                height,
                background: theme.background,
                borderRadius: 16,
                border: theme.border,
                overflow: 'hidden',
                padding: compact ? 12 : 20,
            }}
        >
            {/* 배경 그라디언트 메시 */}
            <div
                style={{
                    position: 'absolute',
                    inset: 0,
                    background: `
                        radial-gradient(ellipse at 20% 20%, ${theme.meshGradient1} 0%, transparent 50%),
                        radial-gradient(ellipse at 80% 80%, ${theme.meshGradient2} 0%, transparent 50%)
                    `,
                    pointerEvents: 'none',
                }}
            />

            {/* 가격 범위 라벨 */}
            {showLabels && (
                <>
                    <div
                        style={{
                            position: 'absolute',
                            top: 8,
                            right: 12,
                            display: 'flex',
                            alignItems: 'center',
                            gap: 6,
                        }}
                    >
                        <Text style={{ color: theme.upperColor, fontSize: 12, fontWeight: 600 }}>
                            상한
                        </Text>
                        <Text
                            style={{
                                color: theme.textPrimary,
                                fontSize: 14,
                                fontWeight: 700,
                                fontFamily: 'SF Mono, Monaco, monospace',
                            }}
                        >
                            {formatPrice(upperPrice)}
                        </Text>
                    </div>
                    <div
                        style={{
                            position: 'absolute',
                            bottom: 8,
                            right: 12,
                            display: 'flex',
                            alignItems: 'center',
                            gap: 6,
                        }}
                    >
                        <Text style={{ color: theme.lowerColor, fontSize: 12, fontWeight: 600 }}>
                            하한
                        </Text>
                        <Text
                            style={{
                                color: theme.textPrimary,
                                fontSize: 14,
                                fontWeight: 700,
                                fontFamily: 'SF Mono, Monaco, monospace',
                            }}
                        >
                            {formatPrice(lowerPrice)}
                        </Text>
                    </div>
                </>
            )}

            {/* 그리드 라인 영역 */}
            <div
                style={{
                    position: 'relative',
                    height: '100%',
                    marginLeft: compact ? 0 : 60,
                    marginRight: compact ? 0 : 80,
                }}
            >
                {/* 세로 가격 축 */}
                <div
                    style={{
                        position: 'absolute',
                        left: compact ? 8 : -40,
                        top: 0,
                        bottom: 0,
                        width: 2,
                        background: theme.axisGradient,
                        borderRadius: 1,
                        opacity: 0.6,
                    }}
                />

                {/* 그리드 라인들 */}
                {gridLines.map((grid) => {
                    const statusColor = STATUS_COLORS[grid.status];
                    const isActive =
                        grid.status === 'buy_filled' || grid.status === 'sell_filled';

                    return (
                        <Tooltip
                            key={grid.index}
                            title={
                                <div style={{ fontSize: 12 }}>
                                    <div>
                                        <strong>그리드 #{grid.index + 1}</strong>
                                    </div>
                                    <div>가격: {formatPrice(grid.price)}</div>
                                    <div>상태: {grid.status}</div>
                                    {grid.order?.profit && (
                                        <div style={{ color: '#34c759' }}>
                                            수익: ${grid.order.profit.toFixed(4)}
                                        </div>
                                    )}
                                </div>
                            }
                            placement="right"
                        >
                            <div
                                onClick={() => onGridClick?.(grid)}
                                style={{
                                    position: 'absolute',
                                    top: `${grid.yPercent}%`,
                                    left: 0,
                                    right: 0,
                                    transform: 'translateY(-50%)',
                                    cursor: onGridClick ? 'pointer' : 'default',
                                }}
                            >
                                {/* 그리드 라인 */}
                                <div
                                    style={{
                                        height: 3,
                                        background: statusColor.border,
                                        borderRadius: 2,
                                        boxShadow: statusColor.glow,
                                        transition: 'all 0.3s ease',
                                        position: 'relative',
                                    }}
                                >
                                    {/* 활성 상태 펄스 애니메이션 */}
                                    {isActive && (
                                        <div
                                            style={{
                                                position: 'absolute',
                                                inset: -4,
                                                background: statusColor.border,
                                                borderRadius: 4,
                                                opacity: 0.3,
                                                animation: 'gridPulse 2s ease-in-out infinite',
                                            }}
                                        />
                                    )}
                                </div>

                                {/* 가격 라벨 (왼쪽) */}
                                {!compact && (
                                    <div
                                        style={{
                                            position: 'absolute',
                                            left: -55,
                                            top: '50%',
                                            transform: 'translateY(-50%)',
                                            fontSize: 10,
                                            color: theme.textSecondary,
                                            fontFamily: 'SF Mono, Monaco, monospace',
                                            whiteSpace: 'nowrap',
                                        }}
                                    >
                                        {formatPrice(grid.price)}
                                    </div>
                                )}

                                {/* 상태 인디케이터 (오른쪽) */}
                                <div
                                    style={{
                                        position: 'absolute',
                                        right: compact ? -8 : -24,
                                        top: '50%',
                                        transform: 'translateY(-50%)',
                                        width: compact ? 8 : 16,
                                        height: compact ? 8 : 16,
                                        borderRadius: '50%',
                                        background: statusColor.bg,
                                        border: `2px solid ${statusColor.border}`,
                                        boxShadow: statusColor.glow,
                                    }}
                                />
                            </div>
                        </Tooltip>
                    );
                })}

                {/* 현재가 마커 */}
                {currentPriceY !== null && (
                    <div
                        style={{
                            position: 'absolute',
                            top: `${currentPriceY}%`,
                            left: -20,
                            right: -20,
                            transform: 'translateY(-50%)',
                            zIndex: 10,
                        }}
                    >
                        {/* 현재가 라인 */}
                        <div
                            style={{
                                height: 2,
                                background: theme.currentPriceGradient,
                                position: 'relative',
                            }}
                        >
                            {/* 움직이는 글로우 */}
                            <div
                                style={{
                                    position: 'absolute',
                                    top: -4,
                                    left: 0,
                                    right: 0,
                                    height: 10,
                                    background:
                                        `linear-gradient(90deg, transparent 0%, ${theme.currentPriceGlow} 50%, transparent 100%)`,
                                    animation: 'currentPriceGlow 3s ease-in-out infinite',
                                }}
                            />
                        </div>

                        {/* 현재가 라벨 */}
                        <div
                            style={{
                                position: 'absolute',
                                right: compact ? -50 : -70,
                                top: '50%',
                                transform: 'translateY(-50%)',
                                background: theme.currentPriceBg,
                                padding: compact ? '2px 6px' : '4px 10px',
                                borderRadius: 6,
                                boxShadow: `0 2px 8px ${theme.currentPriceGlow}`,
                            }}
                        >
                            <Text
                                style={{
                                    color: theme.currentPriceText,
                                    fontSize: compact ? 10 : 12,
                                    fontWeight: 700,
                                    fontFamily: 'SF Mono, Monaco, monospace',
                                }}
                            >
                                {formatPrice(currentPrice)}
                            </Text>
                        </div>
                    </div>
                )}
            </div>

            {/* 범례 */}
            {!compact && (
                <div
                    style={{
                        position: 'absolute',
                        bottom: 12,
                        left: 12,
                        display: 'flex',
                        gap: 16,
                        fontSize: 10,
                    }}
                >
                    {[
                        { label: '대기', status: 'pending' },
                        { label: '매수 체결', status: 'buy_filled' },
                        { label: '매도 체결', status: 'sell_filled' },
                    ].map(({ label, status }) => (
                        <div
                            key={status}
                            style={{ display: 'flex', alignItems: 'center', gap: 4 }}
                        >
                            <div
                                style={{
                                    width: 8,
                                    height: 8,
                                    borderRadius: '50%',
                                    background: STATUS_COLORS[status].border,
                                }}
                            />
                            <Text style={{ color: theme.legendText }}>{label}</Text>
                        </div>
                    ))}
                </div>
            )}

            {/* 애니메이션 스타일 */}
            <style>{`
                @keyframes gridPulse {
                    0%, 100% {
                        transform: scaleX(1);
                        opacity: 0.3;
                    }
                    50% {
                        transform: scaleX(1.1);
                        opacity: 0.5;
                    }
                }

                @keyframes currentPriceGlow {
                    0%, 100% {
                        opacity: 0.4;
                        transform: translateX(-20%);
                    }
                    50% {
                        opacity: 0.8;
                        transform: translateX(20%);
                    }
                }
            `}</style>
        </div>
    );
}

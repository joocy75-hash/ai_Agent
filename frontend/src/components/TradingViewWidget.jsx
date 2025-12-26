import { useEffect, useRef, memo, useState, useCallback } from 'react';
import { Spin, Typography } from 'antd';
import { DownOutlined, ReloadOutlined } from '@ant-design/icons';
import { createChart } from 'lightweight-charts';
import { bitgetAPI } from '../api/bitget';

const { Text } = Typography;

// 코인 정보 (아이콘, 색상)
const COIN_DATA = {
    btc: { name: 'Bitcoin', symbol: '₿', color: '#F7931A', gradient: 'linear-gradient(135deg, #F7931A 0%, #FFAB40 100%)' },
    eth: { name: 'Ethereum', symbol: 'Ξ', color: '#627EEA', gradient: 'linear-gradient(135deg, #627EEA 0%, #8C9EFF 100%)' },
    bnb: { name: 'BNB', symbol: 'B', color: '#F3BA2F', gradient: 'linear-gradient(135deg, #F3BA2F 0%, #FFD54F 100%)' },
    sol: { name: 'Solana', symbol: 'S', color: '#9945FF', gradient: 'linear-gradient(135deg, #9945FF 0%, #14F195 100%)' },
    ada: { name: 'Cardano', symbol: 'A', color: '#0033AD', gradient: 'linear-gradient(135deg, #0033AD 0%, #3F51B5 100%)' },
};

// Custom hook for responsive detection
const useIsMobile = () => {
    const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

    useEffect(() => {
        const handleResize = () => setIsMobile(window.innerWidth < 768);
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    return isMobile;
};

function TradingViewWidget({
    symbol = 'BTCUSDT',
    height = 500,
    availableSymbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT'],
    onSymbolChange,
}) {
    const [loading, setLoading] = useState(true);
    const [coinModalOpen, setCoinModalOpen] = useState(false);
    const [error, setError] = useState(null);
    const [currentPrice, setCurrentPrice] = useState(null);
    const [priceChange, setPriceChange] = useState(null);
    const chartContainerRef = useRef(null);
    const chartRef = useRef(null);
    const candleSeriesRef = useRef(null);
    const isMobile = useIsMobile();

    // 코인 ID 추출
    const coinId = symbol.replace('USDT', '').toLowerCase();
    const coinInfo = COIN_DATA[coinId] || {
        name: coinId.toUpperCase(),
        symbol: coinId.charAt(0).toUpperCase(),
        color: '#1890ff',
        gradient: 'linear-gradient(135deg, #1890ff 0%, #40a9ff 100%)'
    };

    const handleSymbolChange = (newSymbol) => {
        if (onSymbolChange) {
            onSymbolChange(newSymbol);
        }
        setCoinModalOpen(false);
        setLoading(true);
        setError(null);
    };

    // 차트 데이터 로드
    const loadChartData = useCallback(async () => {
        if (!chartContainerRef.current) return;

        try {
            setLoading(true);
            setError(null);

            // Bitget API에서 캔들 데이터 가져오기
            const response = await bitgetAPI.getCandles(symbol, '15m', 200);

            if (!response || !response.candles || response.candles.length === 0) {
                throw new Error('캔들 데이터가 없습니다');
            }

            // 차트가 없으면 생성
            if (!chartRef.current) {
                const chart = createChart(chartContainerRef.current, {
                    width: chartContainerRef.current.clientWidth,
                    height: height,
                    layout: {
                        background: { color: '#ffffff' },
                        textColor: '#333',
                    },
                    grid: {
                        vertLines: { color: '#f0f0f0' },
                        horzLines: { color: '#f0f0f0' },
                    },
                    crosshair: {
                        mode: 1,
                    },
                    rightPriceScale: {
                        borderColor: '#e5e7eb',
                    },
                    timeScale: {
                        borderColor: '#e5e7eb',
                        timeVisible: true,
                        secondsVisible: false,
                    },
                });

                chartRef.current = chart;
                candleSeriesRef.current = chart.addCandlestickSeries({
                    upColor: '#26a69a',
                    downColor: '#ef5350',
                    borderVisible: false,
                    wickUpColor: '#26a69a',
                    wickDownColor: '#ef5350',
                });
            }

            // 캔들 데이터 포맷 변환 (lightweight-charts 형식)
            const formattedCandles = response.candles.map(candle => ({
                time: candle.time,
                open: parseFloat(candle.open),
                high: parseFloat(candle.high),
                low: parseFloat(candle.low),
                close: parseFloat(candle.close),
            }));

            // 현재가 및 변동률 계산
            if (formattedCandles.length > 0) {
                const lastCandle = formattedCandles[formattedCandles.length - 1];
                const firstCandle = formattedCandles[0];
                setCurrentPrice(lastCandle.close);
                const change = ((lastCandle.close - firstCandle.open) / firstCandle.open) * 100;
                setPriceChange(change);
            }

            // 차트에 데이터 설정
            if (candleSeriesRef.current) {
                candleSeriesRef.current.setData(formattedCandles);
                chartRef.current.timeScale().fitContent();
            }

            setLoading(false);

        } catch (err) {
            console.error('차트 데이터 로드 실패:', err);
            setError(err.message || '차트 데이터를 불러올 수 없습니다');
            setLoading(false);
        }
    }, [symbol, height]);

    // 심볼 변경 시 차트 재로드
    useEffect(() => {
        // 기존 차트 제거
        if (chartRef.current) {
            chartRef.current.remove();
            chartRef.current = null;
            candleSeriesRef.current = null;
        }

        loadChartData();
    }, [symbol, loadChartData]);

    // 차트 리사이즈 처리
    useEffect(() => {
        const handleResize = () => {
            if (chartRef.current && chartContainerRef.current) {
                chartRef.current.applyOptions({
                    width: chartContainerRef.current.clientWidth,
                });
            }
        };

        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    // 컴포넌트 언마운트 시 차트 정리
    useEffect(() => {
        return () => {
            if (chartRef.current) {
                chartRef.current.remove();
                chartRef.current = null;
                candleSeriesRef.current = null;
            }
        };
    }, []);

    return (
        <div style={{ position: 'relative', width: '100%' }}>
            {/* Header: Coin Selector */}
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: isMobile ? '8px' : '16px',
                padding: isMobile ? '10px 12px' : '14px 16px',
                border: '1px solid #e5e7eb',
                borderRadius: '12px 12px 0 0',
                background: '#ffffff',
            }}>
                {/* Coin Selector */}
                <div
                    onClick={() => setCoinModalOpen(!coinModalOpen)}
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: isMobile ? '8px' : '12px',
                        cursor: 'pointer',
                        padding: isMobile ? '4px 8px 4px 4px' : '6px 12px 6px 6px',
                        borderRadius: '10px',
                        transition: 'all 0.2s ease',
                        background: 'transparent',
                        position: 'relative',
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.background = '#f5f5f7'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                >
                    {/* Coin Icon */}
                    <div style={{
                        width: isMobile ? '32px' : '40px',
                        height: isMobile ? '32px' : '40px',
                        borderRadius: '50%',
                        background: coinInfo.gradient,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: isMobile ? '16px' : '20px',
                        fontWeight: '700',
                        color: '#fff',
                        boxShadow: `0 4px 12px ${coinInfo.color}40`,
                    }}>
                        {coinInfo.symbol}
                    </div>
                    <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: isMobile ? '4px' : '8px' }}>
                            <span style={{
                                fontSize: isMobile ? '14px' : '18px',
                                fontWeight: '700',
                                color: '#111827',
                                letterSpacing: '-0.02em',
                            }}>
                                {symbol.replace('USDT', '')}
                            </span>
                            {!isMobile && (
                                <span style={{
                                    fontSize: '12px',
                                    color: '#9ca3af',
                                    background: '#f3f4f6',
                                    padding: '2px 6px',
                                    borderRadius: '4px',
                                }}>Perpetual</span>
                            )}
                            <DownOutlined style={{ fontSize: isMobile ? '8px' : '10px', color: '#9ca3af' }} />
                        </div>
                        {!isMobile && (
                            <div style={{ fontSize: '11px', color: '#9ca3af' }}>
                                {coinInfo.name} · Bitget
                            </div>
                        )}
                    </div>
                </div>

                {/* Price Display */}
                {currentPrice && (
                    <div style={{ textAlign: 'right' }}>
                        <div style={{
                            fontSize: isMobile ? '14px' : '18px',
                            fontWeight: '700',
                            color: '#111827',
                        }}>
                            ${currentPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </div>
                        {priceChange !== null && (
                            <div style={{
                                fontSize: isMobile ? '11px' : '12px',
                                color: priceChange >= 0 ? '#26a69a' : '#ef5350',
                                fontWeight: '600',
                            }}>
                                {priceChange >= 0 ? '+' : ''}{priceChange.toFixed(2)}%
                            </div>
                        )}
                    </div>
                )}

                {/* Timeframe Badge + Refresh */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{
                        padding: isMobile ? '6px 12px' : '8px 16px',
                        borderRadius: isMobile ? '6px' : '8px',
                        background: '#111827',
                        color: '#ffffff',
                        fontWeight: 600,
                        fontSize: isMobile ? '11px' : '13px',
                    }}>
                        {isMobile ? '15m' : '15분'}
                    </div>
                    <div
                        onClick={() => !loading && loadChartData()}
                        style={{
                            padding: '8px',
                            borderRadius: '8px',
                            cursor: loading ? 'not-allowed' : 'pointer',
                            color: '#9ca3af',
                            transition: 'all 0.2s',
                        }}
                        onMouseEnter={(e) => !loading && (e.currentTarget.style.background = '#f5f5f7')}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                    >
                        <ReloadOutlined spin={loading} />
                    </div>
                </div>
            </div>

            {/* Dropdown Menu */}
            {coinModalOpen && (
                <div style={{
                    position: 'absolute',
                    top: isMobile ? '52px' : '64px',
                    left: '12px',
                    zIndex: 100,
                    background: '#ffffff',
                    border: '1px solid #e5e7eb',
                    borderRadius: '12px',
                    boxShadow: '0 10px 40px rgba(0,0,0,0.15)',
                    minWidth: '200px',
                    overflow: 'hidden',
                }}>
                    {availableSymbols.map(sym => {
                        const id = sym.replace('USDT', '').toLowerCase();
                        const info = COIN_DATA[id] || { name: id.toUpperCase(), symbol: id.charAt(0).toUpperCase(), gradient: '#1890ff' };
                        const isSelected = sym === symbol;

                        return (
                            <div
                                key={sym}
                                onClick={() => handleSymbolChange(sym)}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '12px',
                                    padding: '12px 16px',
                                    cursor: 'pointer',
                                    background: isSelected ? '#f0f5ff' : 'transparent',
                                    borderLeft: isSelected ? '3px solid #1890ff' : '3px solid transparent',
                                    transition: 'all 0.15s',
                                }}
                                onMouseEnter={(e) => !isSelected && (e.currentTarget.style.background = '#f9fafb')}
                                onMouseLeave={(e) => !isSelected && (e.currentTarget.style.background = 'transparent')}
                            >
                                <div style={{
                                    width: '28px',
                                    height: '28px',
                                    borderRadius: '50%',
                                    background: info.gradient,
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    fontSize: '12px',
                                    fontWeight: '700',
                                    color: '#fff',
                                }}>
                                    {info.symbol}
                                </div>
                                <div>
                                    <div style={{ fontWeight: '600', color: '#111827', fontSize: '14px' }}>
                                        {sym.replace('USDT', '')}
                                    </div>
                                    <div style={{ fontSize: '11px', color: '#9ca3af' }}>
                                        {info.name}
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {/* Backdrop for dropdown */}
            {coinModalOpen && (
                <div
                    style={{
                        position: 'fixed',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        zIndex: 99,
                    }}
                    onClick={() => setCoinModalOpen(false)}
                />
            )}

            {/* Lightweight Charts Container */}
            <div
                style={{
                    width: '100%',
                    height: `${height}px`,
                    minHeight: isMobile ? '300px' : '400px',
                    border: '1px solid #e5e7eb',
                    borderTop: 'none',
                    borderRadius: '0 0 12px 12px',
                    overflow: 'hidden',
                    position: 'relative',
                    background: '#fff',
                }}
            >
                {loading && (
                    <div style={{
                        position: 'absolute',
                        top: '50%',
                        left: '50%',
                        transform: 'translate(-50%, -50%)',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        gap: '12px',
                        zIndex: 10,
                    }}>
                        <Spin size="large" />
                        <Text type="secondary">차트 로딩 중...</Text>
                    </div>
                )}
                {error && (
                    <div style={{
                        position: 'absolute',
                        top: '50%',
                        left: '50%',
                        transform: 'translate(-50%, -50%)',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        gap: '12px',
                        zIndex: 10,
                        textAlign: 'center',
                        padding: '20px',
                    }}>
                        <Text type="danger">{error}</Text>
                        <div
                            onClick={loadChartData}
                            style={{
                                padding: '8px 16px',
                                background: '#1890ff',
                                color: '#fff',
                                borderRadius: '6px',
                                cursor: 'pointer',
                                fontSize: '14px',
                            }}
                        >
                            다시 시도
                        </div>
                    </div>
                )}
                <div
                    ref={chartContainerRef}
                    style={{
                        width: '100%',
                        height: '100%',
                        opacity: loading || error ? 0 : 1,
                        transition: 'opacity 0.3s ease',
                    }}
                />
            </div>
        </div>
    );
}

export default memo(TradingViewWidget);

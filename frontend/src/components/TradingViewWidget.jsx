import { useEffect, useRef, memo, useState } from 'react';
import { Spin, Typography } from 'antd';
import { DownOutlined } from '@ant-design/icons';

const { Text } = Typography;

// 코인 정보 (아이콘, 색상)
const COIN_DATA = {
    btc: { name: 'Bitcoin', symbol: '₿', color: '#F7931A', gradient: 'linear-gradient(135deg, #F7931A 0%, #FFAB40 100%)' },
    eth: { name: 'Ethereum', symbol: 'Ξ', color: '#627EEA', gradient: 'linear-gradient(135deg, #627EEA 0%, #8C9EFF 100%)' },
    bnb: { name: 'BNB', symbol: 'B', color: '#F3BA2F', gradient: 'linear-gradient(135deg, #F3BA2F 0%, #FFD54F 100%)' },
    sol: { name: 'Solana', symbol: 'S', color: '#9945FF', gradient: 'linear-gradient(135deg, #9945FF 0%, #14F195 100%)' },
    ada: { name: 'Cardano', symbol: 'A', color: '#0033AD', gradient: 'linear-gradient(135deg, #0033AD 0%, #3F51B5 100%)' },
};

// TradingView 심볼 매핑 (Bitget Perpetual)
const TRADINGVIEW_SYMBOLS = {
    BTCUSDT: 'BITGET:BTCUSDT.P',
    ETHUSDT: 'BITGET:ETHUSDT.P',
    BNBUSDT: 'BITGET:BNBUSDT.P',
    SOLUSDT: 'BITGET:SOLUSDT.P',
    ADAUSDT: 'BITGET:ADAUSDT.P',
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
    const iframeRef = useRef(null);
    const isMobile = useIsMobile();

    // 코인 ID 추출
    const coinId = symbol.replace('USDT', '').toLowerCase();
    const coinInfo = COIN_DATA[coinId] || {
        name: coinId.toUpperCase(),
        symbol: coinId.charAt(0).toUpperCase(),
        color: '#1890ff',
        gradient: 'linear-gradient(135deg, #1890ff 0%, #40a9ff 100%)'
    };

    const tradingViewSymbol = TRADINGVIEW_SYMBOLS[symbol] || `BITGET:${symbol}.P`;

    const handleSymbolChange = (newSymbol) => {
        if (onSymbolChange) {
            onSymbolChange(newSymbol);
        }
        setCoinModalOpen(false);
        setLoading(true);
    };

    const handleIframeLoad = () => {
        setLoading(false);
    };

    // TradingView Widget URL (iframe 방식)
    const widgetUrl = `https://s.tradingview.com/widgetembed/?frameElementId=tradingview_widget&symbol=${encodeURIComponent(tradingViewSymbol)}&interval=15&hidesidetoolbar=${isMobile ? 1 : 0}&symboledit=0&saveimage=0&toolbarbg=f1f3f6&studies=[]&theme=light&style=1&timezone=Asia%2FSeoul&studies_overrides={}&overrides={}&enabled_features=[]&disabled_features=[]&locale=kr&utm_source=&utm_medium=widget&utm_campaign=chart`;

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

                {/* Timeframe Badge */}
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

            {/* TradingView Chart Container - iframe 기반 */}
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
                <iframe
                    ref={iframeRef}
                    key={symbol} // 심볼 변경 시 iframe 재생성
                    src={widgetUrl}
                    style={{
                        width: '100%',
                        height: '100%',
                        border: 'none',
                        display: loading ? 'none' : 'block',
                    }}
                    onLoad={handleIframeLoad}
                    title={`TradingView Chart - ${symbol}`}
                    allowFullScreen
                />
            </div>
        </div>
    );
}

export default memo(TradingViewWidget);

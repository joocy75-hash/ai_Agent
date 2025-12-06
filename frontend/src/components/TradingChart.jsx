import { useEffect, useRef, useState } from 'react';
import { createChart } from 'lightweight-charts';
import { Modal, Input, Switch, Space, Typography } from 'antd';
import { SearchOutlined, DownOutlined } from '@ant-design/icons';

const { Text } = Typography;

// 환율 설정 (1 USD = 1,460 KRW)
const USD_KRW_RATE = 1460;

// 코인 정보 (아이콘, 색상)
const COIN_DATA = {
  btc: { name: 'Bitcoin', symbol: '₿', color: '#F7931A', gradient: 'linear-gradient(135deg, #F7931A 0%, #FFAB40 100%)' },
  eth: { name: 'Ethereum', symbol: 'Ξ', color: '#627EEA', gradient: 'linear-gradient(135deg, #627EEA 0%, #8C9EFF 100%)' },
  bnb: { name: 'BNB', symbol: 'B', color: '#F3BA2F', gradient: 'linear-gradient(135deg, #F3BA2F 0%, #FFD54F 100%)' },
  sol: { name: 'Solana', symbol: 'S', color: '#9945FF', gradient: 'linear-gradient(135deg, #9945FF 0%, #14F195 100%)' },
  ada: { name: 'Cardano', symbol: 'A', color: '#0033AD', gradient: 'linear-gradient(135deg, #0033AD 0%, #3F51B5 100%)' },
  xrp: { name: 'XRP', symbol: 'X', color: '#23292F', gradient: 'linear-gradient(135deg, #23292F 0%, #607D8B 100%)' },
  doge: { name: 'Dogecoin', symbol: 'Ð', color: '#C2A633', gradient: 'linear-gradient(135deg, #C2A633 0%, #FFE082 100%)' },
};

const formatPrice = (value) => {
  if (value === undefined || value === null) return '-';
  return Math.round(Number(value)).toLocaleString('en-US');
};

const formatPriceShort = (value) => {
  if (value === undefined || value === null) return '-';
  const num = Number(value);
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K';
  }
  return num.toLocaleString('en-US');
};

const formatKRW = (value) => {
  if (value === undefined || value === null) return '₩0';
  const krwPrice = Number(value) * USD_KRW_RATE;
  if (krwPrice >= 1000000) {
    return '₩' + (krwPrice / 10000).toFixed(0) + '만';
  }
  return '₩' + Math.round(krwPrice).toLocaleString('ko-KR');
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

export default function TradingChart({
  data = [],
  symbol = 'BTC/USDT',
  height = 500,
  timeframe,
  availableTimeframes = [],
  onTimeframeChange,
  availableSymbols = [],
  onSymbolChange,
  positions = [],
  tradeMarkers = [],
}) {
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const candlestickSeriesRef = useRef(null);
  const [coinModalOpen, setCoinModalOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [showMarkers, setShowMarkers] = useState(true);
  const isMobile = useIsMobile();

  // Initialize chart once
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const container = chartContainerRef.current;
    const chartWidth = container.clientWidth;

    console.log('[TradingChart] Initializing with width:', chartWidth);

    if (chartWidth === 0) {
      console.warn('[TradingChart] Container width is 0, waiting...');
      return;
    }

    // Create chart
    const chart = createChart(container, {
      width: chartWidth,
      height: height || 600,
      layout: {
        background: { type: 'solid', color: '#ffffff' },
        textColor: '#4b5563',
        fontSize: isMobile ? 10 : 12,
      },
      grid: {
        vertLines: { color: '#eceff3' },
        horzLines: { color: '#eceff3' },
      },
      rightPriceScale: {
        borderColor: '#e5e7eb',
        autoScale: true,
        scaleMargins: {
          top: 0.1,
          bottom: 0.1,
        },
      },
      timeScale: {
        borderColor: '#e5e7eb',
        timeVisible: true,
        rightOffset: isMobile ? 5 : 12,
        barSpacing: isMobile ? 6 : 8,
      },
    });

    // Add candlestick series
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#0ecb81',
      downColor: '#f6465d',
      borderVisible: false,
      wickUpColor: '#0ecb81',
      wickDownColor: '#f6465d',
    });

    chartRef.current = chart;
    candlestickSeriesRef.current = candlestickSeries;

    console.log('[TradingChart] Chart initialized successfully');

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
      if (chartRef.current) {
        chart.remove();
      }
      chartRef.current = null;
      candlestickSeriesRef.current = null;
    };
  }, [height, isMobile]);

  // Update data and markers when they change
  useEffect(() => {
    if (!candlestickSeriesRef.current || !data || data.length === 0) {
      console.log('[TradingChart] No data or series not ready');
      return;
    }

    console.log('[TradingChart] Updating with', data.length, 'candles');

    const candleData = data
      .filter(c => c.time && c.open && c.high && c.low && c.close)
      .map(c => ({
        time: c.time,
        open: parseFloat(c.open),
        high: parseFloat(c.high),
        low: parseFloat(c.low),
        close: parseFloat(c.close),
      }))
      .sort((a, b) => a.time - b.time);

    if (candleData.length === 0) {
      console.warn('[TradingChart] No valid candles');
      return;
    }

    candlestickSeriesRef.current.setData(candleData);

    // Update markers if enabled
    if (showMarkers && tradeMarkers && tradeMarkers.length > 0) {
      const chartMarkers = createChartMarkers(tradeMarkers, candleData);
      if (chartMarkers.length > 0) {
        candlestickSeriesRef.current.setMarkers(chartMarkers);
        console.log('[TradingChart] Added', chartMarkers.length, 'markers');
      }
    } else {
      candlestickSeriesRef.current.setMarkers([]);
    }

    if (chartRef.current) {
      setTimeout(() => {
        chartRef.current?.timeScale().fitContent();
      }, 100);
    }

    console.log('[TradingChart] Data updated successfully');
  }, [data, tradeMarkers, showMarkers]);

  // Create chart markers from trade data
  const createChartMarkers = (markers, candleData) => {
    if (!markers || markers.length === 0 || !candleData || candleData.length === 0) {
      return [];
    }

    // Get time range of candle data
    const minTime = candleData[0].time;
    const maxTime = candleData[candleData.length - 1].time;

    // Convert trade markers to lightweight-charts format
    const chartMarkers = markers
      .filter(m => m.timestamp >= minTime && m.timestamp <= maxTime)
      .map(marker => {
        // Find the closest candle time
        const closestCandle = candleData.reduce((prev, curr) => {
          return Math.abs(curr.time - marker.timestamp) < Math.abs(prev.time - marker.timestamp) ? curr : prev;
        });

        if (marker.type === 'entry') {
          // Entry markers
          if (marker.side === 'long') {
            return {
              time: closestCandle.time,
              position: 'belowBar',
              color: '#0ecb81',
              shape: 'arrowUp',
              text: isMobile ? 'L' : `L ${formatPriceShort(marker.price)}`,
              size: isMobile ? 1 : 2,
            };
          } else {
            return {
              time: closestCandle.time,
              position: 'aboveBar',
              color: '#f6465d',
              shape: 'arrowDown',
              text: isMobile ? 'S' : `S ${formatPriceShort(marker.price)}`,
              size: isMobile ? 1 : 2,
            };
          }
        } else if (marker.type === 'exit') {
          // Exit markers with P&L indicator
          const pnlText = marker.pnl >= 0
            ? `+${marker.pnl.toFixed(isMobile ? 0 : 2)}`
            : marker.pnl.toFixed(isMobile ? 0 : 2);
          const color = marker.pnl >= 0 ? '#0ecb81' : '#f6465d';

          return {
            time: closestCandle.time,
            position: marker.side === 'long' ? 'aboveBar' : 'belowBar',
            color: color,
            shape: 'square',
            text: isMobile ? '✕' : `✕ ${pnlText}`,
            size: isMobile ? 1 : 2,
          };
        }
        return null;
      })
      .filter(m => m !== null)
      .sort((a, b) => a.time - b.time);

    return chartMarkers;
  };

  // Add position lines on chart
  useEffect(() => {
    if (!chartRef.current || !candlestickSeriesRef.current || !positions || positions.length === 0) {
      return;
    }

    // Create price lines for open positions
    positions.forEach(pos => {
      try {
        candlestickSeriesRef.current.createPriceLine({
          price: pos.entry_price,
          color: pos.side === 'long' ? '#0ecb81' : '#f6465d',
          lineWidth: 2,
          lineStyle: 2, // Dashed
          axisLabelVisible: true,
          title: isMobile
            ? `${pos.side === 'long' ? 'L' : 'S'}`
            : `${pos.side.toUpperCase()} @ ${formatPrice(pos.entry_price)}`,
        });
      } catch (e) {
        console.warn('[TradingChart] Failed to create price line:', e);
      }
    });

    // Cleanup
    return () => {
      // Price lines are automatically removed when series is cleared
    };
  }, [positions, data, isMobile]);

  const latestCandle = data && data.length > 0 ? data[data.length - 1] : null;
  const firstCandle = data && data.length > 0 ? data[0] : null;
  const changePercent = latestCandle && firstCandle
    ? (((latestCandle.close - firstCandle.open) / firstCandle.open) * 100).toFixed(2)
    : 0;

  // 코인 ID 추출
  const coinId = symbol.replace('/USDT', '').replace('USDT', '').toLowerCase();
  const coinInfo = COIN_DATA[coinId] || { name: coinId.toUpperCase(), symbol: coinId.charAt(0).toUpperCase(), color: '#1890ff', gradient: 'linear-gradient(135deg, #1890ff 0%, #40a9ff 100%)' };

  // 필터링된 심볼 목록
  const filteredSymbols = availableSymbols.filter(sym =>
    sym.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleCoinSelect = (newSymbol) => {
    if (onSymbolChange) {
      onSymbolChange(newSymbol);
    }
    setCoinModalOpen(false);
    setSearchTerm('');
  };

  const timeframesDefault = [
    { value: '1m', label: '1분' },
    { value: '5m', label: '5분' },
    { value: '15m', label: '15분' },
    { value: '1h', label: '1시간' },
    { value: '4h', label: '4시간' },
    { value: '1d', label: '1일' },
  ];

  // Mobile-optimized timeframes (shorter labels)
  const timeframesMobile = [
    { value: '1m', label: '1m' },
    { value: '5m', label: '5m' },
    { value: '15m', label: '15m' },
    { value: '1h', label: '1H' },
    { value: '4h', label: '4H' },
    { value: '1d', label: '1D' },
  ];

  const tfList = isMobile
    ? timeframesMobile
    : (availableTimeframes.length ? availableTimeframes : timeframesDefault);

  return (
    <div style={{ position: 'relative', width: '100%' }}>
      {/* Combined Header: Coin Info + Timeframe + Price */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: isMobile ? '8px' : '16px',
        padding: isMobile ? '10px 12px' : '14px 16px',
        border: '1px solid #e5e7eb',
        borderRadius: '12px 12px 0 0',
        background: '#ffffff',
        flexWrap: 'wrap',
      }}>
        {/* Left: Coin Selector */}
        <div
          onClick={() => setCoinModalOpen(true)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: isMobile ? '8px' : '12px',
            cursor: 'pointer',
            padding: isMobile ? '4px 8px 4px 4px' : '6px 12px 6px 6px',
            borderRadius: '10px',
            transition: 'all 0.2s ease',
            background: 'transparent',
            flex: isMobile ? '0 0 auto' : 'none',
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
                {symbol.replace('/USDT', '').replace('USDT', '')}
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

        {/* Price Info - Simplified for Mobile */}
        {latestCandle && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: isMobile ? '8px' : '12px',
            flex: isMobile ? '1' : 'none',
            justifyContent: isMobile ? 'flex-end' : 'flex-start',
          }}>
            <div style={{ textAlign: 'right' }}>
              <div style={{
                fontWeight: '800',
                color: parseFloat(changePercent) >= 0 ? '#059669' : '#dc2626',
                fontSize: isMobile ? '16px' : '22px',
                lineHeight: 1.1,
                letterSpacing: '-0.02em',
              }}>
                ${formatPrice(latestCandle.close)}
              </div>
              {!isMobile && (
                <div style={{
                  fontSize: '12px',
                  color: '#9ca3af',
                  marginTop: '2px',
                }}>
                  {formatKRW(latestCandle.close)}
                </div>
              )}
            </div>
            <div style={{
              padding: isMobile ? '4px 8px' : '6px 12px',
              borderRadius: '8px',
              background: parseFloat(changePercent) >= 0 ? '#dcfce7' : '#fee2e2',
              color: parseFloat(changePercent) >= 0 ? '#059669' : '#dc2626',
              fontWeight: '700',
              fontSize: isMobile ? '12px' : '14px',
            }}>
              {parseFloat(changePercent) >= 0 ? '+' : ''}{changePercent}%
            </div>
          </div>
        )}

        {/* OHLC - Hidden on Mobile */}
        {!isMobile && latestCandle && (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '4px',
            fontSize: '12px',
            color: '#6b7280',
            borderLeft: '1px solid #e5e7eb',
            paddingLeft: '16px',
          }}>
            <span>O <b style={{ color: '#111827' }}>{formatPrice(latestCandle.open)}</b></span>
            <span>H <b style={{ color: '#059669' }}>{formatPrice(latestCandle.high)}</b></span>
            <span>L <b style={{ color: '#dc2626' }}>{formatPrice(latestCandle.low)}</b></span>
            <span>C <b style={{ color: '#111827' }}>{formatPrice(latestCandle.close)}</b></span>
          </div>
        )}
      </div>

      {/* Second Row: Timeframe + Marker Toggle (Mobile Optimized) */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '8px',
        padding: isMobile ? '8px 12px' : '10px 16px',
        borderLeft: '1px solid #e5e7eb',
        borderRight: '1px solid #e5e7eb',
        background: '#fafafa',
      }}>
        {/* Timeframe Selector */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: isMobile ? '2px' : '4px',
          background: '#f0f0f0',
          padding: isMobile ? '2px' : '4px',
          borderRadius: isMobile ? '8px' : '10px',
          overflowX: 'auto',
          WebkitOverflowScrolling: 'touch',
          flex: 1,
        }}>
          {tfList.map((tf) => (
            <button
              key={tf.value}
              onClick={() => onTimeframeChange && onTimeframeChange(tf.value)}
              style={{
                padding: isMobile ? '6px 10px' : '8px 14px',
                borderRadius: isMobile ? '6px' : '8px',
                border: 'none',
                background: timeframe === tf.value ? '#111827' : 'transparent',
                color: timeframe === tf.value ? '#ffffff' : '#6b7280',
                fontWeight: timeframe === tf.value ? 600 : 500,
                fontSize: isMobile ? '11px' : '13px',
                cursor: onTimeframeChange ? 'pointer' : 'default',
                transition: 'all 0.15s ease',
                whiteSpace: 'nowrap',
                flexShrink: 0,
              }}
            >
              {tf.label}
            </button>
          ))}
        </div>

        {/* Marker Toggle */}
        <Space size={4} style={{ flexShrink: 0 }}>
          <Switch
            size="small"
            checked={showMarkers}
            onChange={setShowMarkers}
            style={{ background: showMarkers ? '#0ecb81' : undefined }}
          />
          {!isMobile && (
            <Text style={{ fontSize: '11px', color: '#6b7280' }}>
              마커 {tradeMarkers?.length || 0}
            </Text>
          )}
        </Space>
      </div>

      {/* Chart Container */}
      <div
        ref={chartContainerRef}
        style={{
          width: '100%',
          height: `${height}px`,
          minHeight: isMobile ? '280px' : '400px',
          border: '1px solid #e5e7eb',
          borderTop: 'none',
          borderRadius: '0 0 12px 12px',
        }}
      />

      {/* Marker Legend - Compact for Mobile */}
      {showMarkers && tradeMarkers && tradeMarkers.length > 0 && (
        <div style={{
          position: 'absolute',
          bottom: isMobile ? '8px' : '16px',
          left: isMobile ? '8px' : '16px',
          background: 'rgba(255,255,255,0.95)',
          padding: isMobile ? '4px 8px' : '8px 12px',
          borderRadius: isMobile ? '6px' : '8px',
          border: '1px solid #e5e7eb',
          display: 'flex',
          gap: isMobile ? '8px' : '16px',
          fontSize: isMobile ? '9px' : '11px',
          color: '#6b7280',
          boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
        }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
            <span style={{ color: '#0ecb81', fontSize: isMobile ? '10px' : '14px' }}>▲</span>
            {isMobile ? 'L' : '롱 진입'}
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
            <span style={{ color: '#f6465d', fontSize: isMobile ? '10px' : '14px' }}>▼</span>
            {isMobile ? 'S' : '숏 진입'}
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
            <span style={{ fontSize: isMobile ? '10px' : '12px' }}>✕</span>
            {isMobile ? '청산' : '청산'}
          </span>
        </div>
      )}

      {/* Coin Selection Modal */}
      <Modal
        title={
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: isMobile ? '16px' : '18px',
            fontWeight: '700',
          }}>
            코인 선택
          </div>
        }
        open={coinModalOpen}
        onCancel={() => {
          setCoinModalOpen(false);
          setSearchTerm('');
        }}
        footer={null}
        width={isMobile ? '100%' : 420}
        centered
        styles={{
          body: { padding: '16px 0' },
        }}
      >
        {/* Search Input */}
        <div style={{ padding: '0 16px 16px' }}>
          <Input
            prefix={<SearchOutlined style={{ color: '#9ca3af' }} />}
            placeholder="코인 검색..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              borderRadius: '10px',
              padding: isMobile ? '8px 12px' : '10px 14px',
              fontSize: '14px',
            }}
            autoFocus
          />
        </div>

        {/* Coin List */}
        <div style={{
          maxHeight: isMobile ? '60vh' : '400px',
          overflowY: 'auto',
          padding: '0 8px',
        }}>
          {filteredSymbols.map((sym) => {
            const symCoinId = sym.replace('USDT', '').toLowerCase();
            const symCoinInfo = COIN_DATA[symCoinId] || {
              name: symCoinId.toUpperCase(),
              symbol: symCoinId.charAt(0).toUpperCase(),
              color: '#1890ff',
              gradient: 'linear-gradient(135deg, #1890ff 0%, #40a9ff 100%)'
            };
            const isSelected = sym === symbol.replace('/USDT', '').replace('USDT', '') + 'USDT' ||
              sym === symbol.replace('/USDT', '');

            return (
              <div
                key={sym}
                onClick={() => handleCoinSelect(sym)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: isMobile ? '10px' : '14px',
                  padding: isMobile ? '12px' : '14px 16px',
                  borderRadius: '12px',
                  cursor: 'pointer',
                  background: isSelected ? '#f0f9ff' : 'transparent',
                  border: isSelected ? '1px solid #bae6fd' : '1px solid transparent',
                  transition: 'all 0.15s ease',
                  marginBottom: '4px',
                }}
                onMouseEnter={(e) => {
                  if (!isSelected) {
                    e.currentTarget.style.background = '#f5f5f7';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isSelected) {
                    e.currentTarget.style.background = 'transparent';
                  }
                }}
              >
                {/* Coin Icon */}
                <div style={{
                  width: isMobile ? '36px' : '44px',
                  height: isMobile ? '36px' : '44px',
                  borderRadius: '50%',
                  background: symCoinInfo.gradient,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: isMobile ? '14px' : '18px',
                  fontWeight: '700',
                  color: '#fff',
                  boxShadow: `0 4px 12px ${symCoinInfo.color}30`,
                }}>
                  {symCoinInfo.symbol}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{
                    fontWeight: '600',
                    fontSize: isMobile ? '14px' : '15px',
                    color: '#111827',
                  }}>
                    {sym.replace('USDT', '')}
                  </div>
                  <div style={{ fontSize: isMobile ? '11px' : '12px', color: '#9ca3af' }}>
                    {symCoinInfo.name}
                  </div>
                </div>
                {isSelected && (
                  <div style={{
                    width: isMobile ? '20px' : '24px',
                    height: isMobile ? '20px' : '24px',
                    borderRadius: '50%',
                    background: '#0ea5e9',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#fff',
                    fontSize: isMobile ? '12px' : '14px',
                  }}>
                    ✓
                  </div>
                )}
              </div>
            );
          })}

          {filteredSymbols.length === 0 && (
            <div style={{
              textAlign: 'center',
              color: '#9ca3af',
              padding: '40px 20px',
              fontSize: '14px',
            }}>
              검색 결과가 없습니다
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
}

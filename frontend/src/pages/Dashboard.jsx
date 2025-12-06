import { useState, useEffect } from 'react';
import { Row, Col, Card, Tag, Table, Empty } from 'antd';
import {
  LineChartOutlined,
  BarChartOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  DollarOutlined,
  WalletOutlined,
  TrophyOutlined,
  ThunderboltOutlined,
  SwapOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { useWebSocket } from '../context/WebSocketContext';
import ErrorBoundary from '../components/ErrorBoundary';
import PositionList from '../components/PositionList';
import RiskGauge from '../components/RiskGauge';
import { bitgetAPI } from '../api/bitget';
import { botAPI } from '../api/bot';
import { analyticsAPI } from '../api/analytics';
import { orderAPI } from '../api/order';

// Apple 스타일 통계 카드 컴포넌트 (모바일 최적화)
const StatCard = ({ title, value, suffix, trend, trendValue, icon, delay = 0, isMobile = false }) => {
  const isPositive = trend === 'up';
  const isNegative = trend === 'down';

  return (
    <div
      style={{
        background: '#ffffff',
        borderRadius: isMobile ? 12 : 16,
        padding: isMobile ? '14px 16px' : '24px',
        border: '1px solid #f5f5f7',
        transition: 'all 0.25s ease',
        animation: `fadeInUp 0.5s ease ${delay}s both`,
        cursor: 'default',
        minHeight: isMobile ? 'auto' : undefined,
      }}
      className="stat-card-hover"
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{
            fontSize: isMobile ? 11 : 13,
            color: '#86868b',
            fontWeight: 500,
            marginBottom: isMobile ? 4 : 8,
            letterSpacing: '0.01em',
          }}>
            {title}
          </div>
          <div style={{
            fontSize: isMobile ? 20 : 28,
            fontWeight: 600,
            color: '#1d1d1f',
            letterSpacing: '-0.02em',
            lineHeight: 1.2,
          }}>
            {value}
            {suffix && <span style={{ fontSize: isMobile ? 12 : 16, marginLeft: 2, color: '#86868b' }}>{suffix}</span>}
          </div>
          {trendValue !== undefined && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              marginTop: isMobile ? 4 : 8,
            }}>
              {isPositive && <ArrowUpOutlined style={{ fontSize: isMobile ? 10 : 12, color: '#34c759' }} />}
              {isNegative && <ArrowDownOutlined style={{ fontSize: isMobile ? 10 : 12, color: '#ff3b30' }} />}
              <span style={{
                fontSize: isMobile ? 11 : 13,
                fontWeight: 500,
                color: isPositive ? '#34c759' : isNegative ? '#ff3b30' : '#86868b',
              }}>
                {trendValue}
              </span>
            </div>
          )}
        </div>
        <div style={{
          width: isMobile ? 32 : 48,
          height: isMobile ? 32 : 48,
          borderRadius: isMobile ? 8 : 12,
          background: '#f5f5f7',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#86868b',
          fontSize: isMobile ? 14 : 20,
        }}>
          {icon}
        </div>
      </div>
    </div>
  );
};

// 포지션 카드 (Long/Short 표시) - 모바일 최적화
const PositionCard = ({ longCount, shortCount, delay = 0, isMobile = false }) => {
  return (
    <div
      style={{
        background: '#ffffff',
        borderRadius: isMobile ? 12 : 16,
        padding: isMobile ? '14px 16px' : '24px',
        border: '1px solid #f5f5f7',
        transition: 'all 0.25s ease',
        animation: `fadeInUp 0.5s ease ${delay}s both`,
        cursor: 'default',
      }}
      className="stat-card-hover"
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{
            fontSize: isMobile ? 11 : 13,
            color: '#86868b',
            fontWeight: 500,
            marginBottom: isMobile ? 4 : 8,
            letterSpacing: '0.01em',
          }}>
            포지션
          </div>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: isMobile ? 6 : 12,
            marginTop: isMobile ? 2 : 4,
          }}>
            {/* Long */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: isMobile ? 2 : 4,
            }}>
              <ArrowUpOutlined style={{ fontSize: isMobile ? 12 : 16, color: '#34c759' }} />
              <span style={{
                fontSize: isMobile ? 11 : 14,
                fontWeight: 600,
                color: '#34c759',
              }}>Long</span>
              <span style={{
                fontSize: isMobile ? 16 : 22,
                fontWeight: 700,
                color: '#1d1d1f',
                marginLeft: isMobile ? 1 : 2,
              }}>{longCount}</span>
            </div>

            {/* Divider */}
            <span style={{ color: '#d2d2d7', fontSize: isMobile ? 16 : 20 }}>/</span>

            {/* Short */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: isMobile ? 2 : 4,
            }}>
              <ArrowDownOutlined style={{ fontSize: isMobile ? 12 : 16, color: '#ff3b30' }} />
              <span style={{
                fontSize: isMobile ? 11 : 14,
                fontWeight: 600,
                color: '#ff3b30',
              }}>Short</span>
              <span style={{
                fontSize: isMobile ? 16 : 22,
                fontWeight: 700,
                color: '#1d1d1f',
                marginLeft: isMobile ? 1 : 2,
              }}>{shortCount}</span>
            </div>
          </div>
        </div>
        <div style={{
          width: isMobile ? 32 : 48,
          height: isMobile ? 32 : 48,
          borderRadius: isMobile ? 8 : 12,
          background: '#f5f5f7',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#86868b',
          fontSize: isMobile ? 14 : 20,
        }}>
          <SwapOutlined />
        </div>
      </div>
    </div>
  );
};

// 최대 이익/손실 카드 - 모바일 최적화
const ProfitLossCard = ({ bestTrade, worstTrade, delay = 0, isMobile = false }) => {
  return (
    <div
      style={{
        background: '#ffffff',
        borderRadius: isMobile ? 12 : 16,
        padding: isMobile ? '14px 16px' : '24px',
        border: '1px solid #f5f5f7',
        transition: 'all 0.25s ease',
        animation: `fadeInUp 0.5s ease ${delay}s both`,
        cursor: 'default',
      }}
      className="stat-card-hover"
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{
            fontSize: isMobile ? 11 : 13,
            color: '#86868b',
            fontWeight: 500,
            marginBottom: isMobile ? 4 : 8,
            letterSpacing: '0.01em',
          }}>
            최대 이익 / 손실
          </div>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: isMobile ? 6 : 12,
            marginTop: isMobile ? 2 : 4,
          }}>
            {/* Best Trade */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: isMobile ? 1 : 2,
            }}>
              <ArrowUpOutlined style={{ fontSize: isMobile ? 12 : 16, color: '#34c759' }} />
              <span style={{
                fontSize: isMobile ? 16 : 22,
                fontWeight: 700,
                color: '#34c759',
                fontFamily: 'SF Mono, Monaco, monospace',
              }}>+{Math.round(bestTrade)}</span>
              <span style={{ fontSize: isMobile ? 11 : 14, color: '#34c759', fontWeight: 600 }}>%</span>
            </div>

            {/* Divider */}
            <span style={{ color: '#d2d2d7', fontSize: isMobile ? 16 : 20 }}>/</span>

            {/* Worst Trade */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: isMobile ? 1 : 2,
            }}>
              <ArrowDownOutlined style={{ fontSize: isMobile ? 12 : 16, color: '#ff3b30' }} />
              <span style={{
                fontSize: isMobile ? 16 : 22,
                fontWeight: 700,
                color: '#ff3b30',
                fontFamily: 'SF Mono, Monaco, monospace',
              }}>{Math.round(worstTrade)}</span>
              <span style={{ fontSize: isMobile ? 11 : 14, color: '#ff3b30', fontWeight: 600 }}>%</span>
            </div>
          </div>
        </div>
        <div style={{
          width: isMobile ? 32 : 48,
          height: isMobile ? 32 : 48,
          borderRadius: isMobile ? 8 : 12,
          background: '#f5f5f7',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#86868b',
          fontSize: isMobile ? 14 : 20,
        }}>
          <TrophyOutlined />
        </div>
      </div>
    </div>
  );
};

// 기간별 수익 카드 (미니멀 버전)
// 기간별 수익 카드 (미니멀 버전)
const PeriodProfitCard = ({ title, returnValue, pnl, delay = 0 }) => {
  const isPositive = returnValue >= 0;

  return (
    <div
      style={{
        background: '#ffffff',
        borderRadius: 12,
        padding: '20px',
        border: '1px solid #f5f5f7',
        transition: 'all 0.25s ease',
        animation: `fadeInUp 0.5s ease ${delay}s both`,
      }}
      className="stat-card-hover"
    >
      <div style={{
        fontSize: 12,
        color: '#86868b',
        fontWeight: 700, // Bold title as per request "각패널 메인 글씨 진한글씨로 전체 변경" - applying here too just in case
        marginBottom: 12,
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
      }}>
        {title}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
        {isPositive ? (
          <ArrowUpOutlined style={{ fontSize: 14, color: '#0071e3' }} />
        ) : (
          <ArrowDownOutlined style={{ fontSize: 14, color: '#ff3b30' }} />
        )}
        <span style={{
          fontSize: 24,
          fontWeight: 600,
          color: isPositive ? '#0071e3' : '#ff3b30',
          letterSpacing: '-0.02em',
        }}>
          {Math.round(Math.abs(returnValue))}
        </span>
        <span style={{ fontSize: 14, color: '#86868b' }}>%</span>
      </div>
      <div style={{
        fontSize: 12,
        color: '#86868b',
        marginTop: 6,
        fontFamily: 'SF Mono, Monaco, Menlo, monospace',
      }}>
        {pnl >= 0 ? '+' : ''}{Math.round(pnl)} USDT
      </div>
    </div>
  );
};

// 최근 거래내역 컴포넌트
const RecentTrades = ({ trades, loading }) => {
  const columns = [
    {
      title: '시간',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 100,
      render: (value) => {
        if (!value) return '-';
        const date = new Date(value);
        return (
          <span style={{ fontSize: 12, color: '#86868b' }}>
            {date.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}
          </span>
        );
      },
    },
    {
      title: '심볼',
      dataIndex: 'symbol',
      key: 'symbol',
      width: 100,
      render: (value) => (
        <span style={{ fontWeight: 600, color: '#1d1d1f', fontSize: 13 }}>
          {value?.replace('USDT', '') || '-'}
        </span>
      ),
    },
    {
      title: '방향',
      dataIndex: 'side',
      key: 'side',
      width: 70,
      render: (value) => {
        const isBuy = value?.toLowerCase() === 'buy';
        return (
          <Tag
            color={isBuy ? 'green' : 'red'}
            style={{
              borderRadius: 12,
              fontSize: 11,
              border: 'none',
              padding: '2px 8px',
            }}
          >
            {isBuy ? 'Long' : 'Short'}
          </Tag>
        );
      },
    },
    {
      title: '가격',
      dataIndex: 'price',
      key: 'price',
      width: 100,
      align: 'right',
      render: (value) => (
        <span style={{ fontFamily: 'SF Mono, monospace', fontSize: 12 }}>
          ${parseFloat(value || 0).toLocaleString()}
        </span>
      ),
    },
    {
      title: '수익',
      dataIndex: 'pnl',
      key: 'pnl',
      width: 90,
      align: 'right',
      render: (value) => {
        const pnl = parseFloat(value || 0);
        const isPositive = pnl >= 0;
        return (
          <span style={{
            fontFamily: 'SF Mono, monospace',
            fontSize: 12,
            fontWeight: 600,
            color: isPositive ? '#34c759' : '#ff3b30',
          }}>
            {isPositive ? '+' : ''}{pnl.toFixed(2)}
          </span>
        );
      },
    },
  ];

  return (
    <Card
      title={
        <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <SwapOutlined style={{ color: '#0071e3' }} />
          최근 거래내역
        </span>
      }
      style={{ marginBottom: 20 }}
      styles={{ body: { padding: 0 } }}
    >
      {trades.length > 0 ? (
        <Table
          dataSource={trades.slice(0, 5)}
          columns={columns}
          pagination={false}
          loading={loading}
          size="small"
          rowKey={(record, index) => record.order_id || index}
          style={{
            background: '#ffffff',
            borderRadius: '0 0 12px 12px',
          }}
        />
      ) : (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={<span style={{ color: '#86868b' }}>거래 내역이 없습니다</span>}
          style={{ padding: '40px 0' }}
        />
      )}
    </Card>
  );
};

export default function Dashboard() {
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const [currentPrices, setCurrentPrices] = useState({});
  const [botStatus, setBotStatus] = useState(null);
  const [tradeStats, setTradeStats] = useState(null);
  const [periodProfits, setPeriodProfits] = useState(null);
  const [recentTrades, setRecentTrades] = useState([]);
  const [tradesLoading, setTradesLoading] = useState(false);
  const { subscribe, isConnected } = useWebSocket();

  const loadBotStatus = async () => {
    try {
      const status = await botAPI.getStatus();
      setBotStatus(status);
    } catch (error) {
      console.error('[Dashboard] Error loading bot status:', error);
    }
  };

  const loadPrices = async () => {
    try {
      const symbols = ['BTCUSDT'];
      const prices = {};

      for (const symbol of symbols) {
        try {
          const ticker = await bitgetAPI.getTicker(symbol);
          if (ticker && ticker.last) {
            prices[symbol] = parseFloat(ticker.last);
          }
        } catch (err) {
          console.log(`[Dashboard] Failed to load price for ${symbol}`);
        }
      }
      setCurrentPrices(prices);
    } catch (error) {
      console.error('[Dashboard] Error loading prices:', error);
      setCurrentPrices({});
    }
  };

  const loadTradeStats = async () => {
    try {
      const [performance, riskMetrics] = await Promise.all([
        analyticsAPI.getPerformanceMetrics('all'),
        analyticsAPI.getRiskMetrics()
      ]);

      setTradeStats({
        totalTrades: riskMetrics.total_trades || 0,
        winRate: riskMetrics.win_rate || 0,
        winningTrades: performance.winning_trades || 0,
        losingTrades: performance.losing_trades || 0,
        avgPnl: performance.total_pnl && performance.total_trades
          ? (performance.total_pnl / performance.total_trades).toFixed(2)
          : 0,
        totalReturn: performance.total_return || 0,
        bestTrade: performance.best_trade?.pnl_percent || 0,
        worstTrade: performance.worst_trade?.pnl_percent || 0,
        longCount: performance.total_trades || 0,
        shortCount: 0,
      });
    } catch (error) {
      console.error('[Dashboard] Error loading trade stats:', error);
      setTradeStats(null);
    }
  };

  const loadPeriodProfits = async () => {
    try {
      const [daily, weekly, monthly, allTime] = await Promise.all([
        analyticsAPI.getPerformanceMetrics('1d'),
        analyticsAPI.getPerformanceMetrics('1w'),
        analyticsAPI.getPerformanceMetrics('1m'),
        analyticsAPI.getPerformanceMetrics('all')
      ]);

      setPeriodProfits({
        daily: { return: daily.total_return || 0, pnl: daily.total_pnl || 0 },
        weekly: { return: weekly.total_return || 0, pnl: weekly.total_pnl || 0 },
        monthly: { return: monthly.total_return || 0, pnl: monthly.total_pnl || 0 },
        allTime: { return: allTime.total_return || 0, pnl: allTime.total_pnl || 0 },
      });
    } catch (error) {
      console.error('[Dashboard] Error loading period profits:', error);
      setPeriodProfits(null);
    }
  };

  const loadRecentTrades = async () => {
    try {
      setTradesLoading(true);
      const response = await orderAPI.getOrderHistory(10);
      const trades = Array.isArray(response) ? response : (response?.orders || []);
      setRecentTrades(trades.slice(0, 10));
    } catch (error) {
      console.error('[Dashboard] Error loading recent trades:', error);
      setRecentTrades([]);
    } finally {
      setTradesLoading(false);
    }
  };

  useEffect(() => {
    loadBotStatus();
    loadPrices();
    loadTradeStats();
    loadPeriodProfits();
    loadRecentTrades();

    const interval = setInterval(() => {
      loadBotStatus();
      loadPrices();
      loadTradeStats();
      loadPeriodProfits();
      loadRecentTrades();
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!isConnected) return;

    const unsubscribe = subscribe('price_update', (data) => {
      if (data.symbol && data.price) {
        setCurrentPrices(prev => ({
          ...prev,
          [data.symbol]: parseFloat(data.price)
        }));
      }
    });

    return unsubscribe;
  }, [isConnected, subscribe]);

  return (
    <div style={{ maxWidth: 1400, margin: '0 auto', padding: isMobile ? 0 : undefined }}>

      {/* Stats Grid - Apple Style */}
      <Row gutter={isMobile ? [8, 8] : [16, 16]} style={{ marginBottom: isMobile ? 16 : 24 }}>
        <Col xs={12} sm={12} md={6}>
          <StatCard
            title="총 거래"
            value={tradeStats?.totalTrades || 0}
            suffix="회"
            icon={<BarChartOutlined />}
            delay={0}
            isMobile={isMobile}
          />
        </Col>
        <Col xs={12} sm={12} md={6}>
          <PositionCard
            longCount={tradeStats?.longCount || 0}
            shortCount={tradeStats?.shortCount || 0}
            delay={0.1}
            isMobile={isMobile}
          />
        </Col>
        <Col xs={12} sm={12} md={6}>
          <ProfitLossCard
            bestTrade={tradeStats?.bestTrade || 0}
            worstTrade={tradeStats?.worstTrade || 0}
            delay={0.2}
            isMobile={isMobile}
          />
        </Col>
        <Col xs={12} sm={12} md={6}>
          <StatCard
            title="평균 수익"
            value={parseFloat(tradeStats?.avgPnl || 0).toFixed(2)}
            suffix="%"
            trend={parseFloat(tradeStats?.avgPnl || 0) >= 0 ? 'up' : 'down'}
            icon={<ThunderboltOutlined />}
            delay={0.3}
            isMobile={isMobile}
          />
        </Col>
      </Row>

      {/* Main Content */}
      <Row gutter={[20, 20]}>
        {/* Left Column */}
        <Col xs={24} lg={16}>
          {/* Period Profits - Clean White Cards */}
          <Card
            title={
              <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <DollarOutlined style={{ color: '#34c759' }} />
                기간별 수익
              </span>
            }
            style={{ marginBottom: 20 }}
            styles={{ body: { padding: 20 } }}
          >
            <Row gutter={[12, 12]}>
              <Col xs={12} sm={6}>
                <PeriodProfitCard
                  title="24시간"
                  returnValue={periodProfits?.daily?.return || 0}
                  pnl={periodProfits?.daily?.pnl || 0}
                  delay={0}
                />
              </Col>
              <Col xs={12} sm={6}>
                <PeriodProfitCard
                  title="7일"
                  returnValue={periodProfits?.weekly?.return || 0}
                  pnl={periodProfits?.weekly?.pnl || 0}
                  delay={0.1}
                />
              </Col>
              <Col xs={12} sm={6}>
                <PeriodProfitCard
                  title="30일"
                  returnValue={periodProfits?.monthly?.return || 0}
                  pnl={periodProfits?.monthly?.pnl || 0}
                  delay={0.2}
                />
              </Col>
              <Col xs={12} sm={6}>
                <PeriodProfitCard
                  title="전체"
                  returnValue={periodProfits?.allTime?.return || 0}
                  pnl={periodProfits?.allTime?.pnl || 0}
                  delay={0.3}
                />
              </Col>
            </Row>
          </Card>

          {/* Position List */}
          <ErrorBoundary>
            <PositionList
              currentPrices={currentPrices}
              onPositionClosed={loadBotStatus}
            />
          </ErrorBoundary>

          {/* Recent Trades */}
          <RecentTrades trades={recentTrades} loading={tradesLoading} />
        </Col>

        {/* Right Column */}
        <Col xs={24} lg={8}>
          {/* Risk Gauge with Chart */}
          <div style={{ marginBottom: 20 }}>
            <ErrorBoundary>
              <RiskGauge />
            </ErrorBoundary>
          </div>

          {/* Bot Status Card */}
          <Card
            title={
              <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <ThunderboltOutlined style={{ color: '#0071e3' }} />
                봇 상태
              </span>
            }
            style={{ marginBottom: 20 }}
            styles={{ body: { padding: 20 } }}
          >
            <div style={{ marginBottom: 16 }}>
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: 12,
              }}>
                <span style={{ color: '#1d1d1f', fontWeight: 500 }}>엔진 상태</span>
                <Tag
                  color={botStatus?.is_running ? 'green' : 'default'}
                  style={{ borderRadius: 20, padding: '2px 12px' }}
                >
                  {botStatus?.is_running ? '실행 중' : '정지'}
                </Tag>
              </div>
              {botStatus?.strategy && (
                <div style={{
                  background: '#f5f5f7',
                  borderRadius: 8,
                  padding: '12px',
                  marginTop: 12,
                }}>
                  <div style={{ fontSize: 12, color: '#86868b', marginBottom: 4 }}>현재 전략</div>
                  <div style={{ fontSize: 14, fontWeight: 500, color: '#1d1d1f' }}>
                    {typeof botStatus.strategy === 'object'
                      ? (botStatus.strategy?.name || botStatus.strategy?.strategy_name || JSON.stringify(botStatus.strategy))
                      : botStatus.strategy}
                  </div>
                </div>
              )}
            </div>
          </Card>

          {/* Connection Status */}
          <Card
            title={
              <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <LineChartOutlined style={{ color: '#0071e3' }} />
                연결 상태
              </span>
            }
            styles={{ body: { padding: 20 } }}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}>
                <span style={{ color: '#1d1d1f', fontSize: 14 }}>WebSocket</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    background: isConnected ? '#34c759' : '#ff3b30',
                    animation: isConnected ? 'pulse 2s infinite' : 'none',
                  }} />
                  <span style={{
                    fontSize: 13,
                    color: isConnected ? '#34c759' : '#ff3b30',
                    fontWeight: 500,
                  }}>
                    {isConnected ? '연결됨' : '끊김'}
                  </span>
                </div>
              </div>

              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}>
                <span style={{ color: '#1d1d1f', fontSize: 14 }}>Bitget API</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    background: Object.keys(currentPrices).length > 0 ? '#34c759' : '#ff9500',
                  }} />
                  <span style={{
                    fontSize: 13,
                    color: Object.keys(currentPrices).length > 0 ? '#34c759' : '#ff9500',
                    fontWeight: 500,
                  }}>
                    {Object.keys(currentPrices).length > 0 ? '정상' : '확인 필요'}
                  </span>
                </div>
              </div>

              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}>
                <span style={{ color: '#1d1d1f', fontSize: 14 }}>봇 엔진</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    background: botStatus ? '#34c759' : '#86868b',
                  }} />
                  <span style={{
                    fontSize: 13,
                    color: botStatus ? '#34c759' : '#86868b',
                    fontWeight: 500,
                  }}>
                    {botStatus ? '활성화' : '로딩 중'}
                  </span>
                </div>
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* Animations */}
      <style>
        {`
          @keyframes fadeInUp {
            from {
              opacity: 0;
              transform: translateY(20px);
            }
            to {
              opacity: 1;
              transform: translateY(0);
            }
          }

          @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
          }

          .stat-card-hover:hover {
            /* Hover animation disabled for main panels */
          }
        `}
      </style>
    </div>
  );
}

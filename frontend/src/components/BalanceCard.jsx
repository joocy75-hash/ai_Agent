import { useState, useEffect, memo } from 'react';
import { accountAPI } from '../api/account';
import { bitgetAPI } from '../api/bitget';
import { useWebSocket } from '../context/WebSocketContext';
import { ReloadOutlined, WalletOutlined, CheckCircleOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { Button, Spin, Tooltip, Row, Col } from 'antd';

function BalanceCard({ onRefresh }) {
  // 모바일 감지
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // 초기값을 0으로 설정하여 로딩 중에도 레이아웃이 유지되도록 함 (깜빡임 방지)
  const [balance, setBalance] = useState({
    exchange: 'bitget',
    mock: false,
    futures: {
      total: 0,
      free: 0,
      used: 0,
      unrealized_pnl: 0
    }
  });
  const [loading, setLoading] = useState(false);
  const [useBitget, setUseBitget] = useState(true);
  const { subscribe, isConnected } = useWebSocket();

  const USD_KRW_RATE = 1460; // 고정 환율

  const loadBalance = async () => {
    setLoading(true);
    try {
      // Bitget API 먼저 시도
      if (useBitget) {
        try {
          const data = await bitgetAPI.getAccount();

          const formattedBalance = {
            exchange: 'bitget',
            mock: false,
            futures: {
              total: parseFloat(data.available || 0) + parseFloat(data.frozen || 0),
              free: parseFloat(data.available || 0),
              used: parseFloat(data.frozen || 0),
              unrealized_pnl: parseFloat(data.unrealizedPL || 0)
            }
          };

          setBalance(formattedBalance);
          return;
        } catch (bitgetError) {
          console.log('[BalanceCard] Bitget API failed, using legacy API');
          setUseBitget(false);
        }
      }

      // Legacy API fallback
      const data = await accountAPI.getBalance();
      setBalance(data);

    } catch (err) {
      console.error('[BalanceCard] Error loading balance:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBalance();
    const interval = setInterval(loadBalance, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!isConnected) return;
    const unsubscribe = subscribe('balance_update', (data) => {
      if (balance && data.data) {
        setBalance(prev => ({
          ...prev,
          futures: {
            ...prev.futures,
            total: parseFloat(data.data.total || prev.futures.total),
            free: parseFloat(data.data.free || prev.futures.free),
            used: parseFloat(data.data.used || prev.futures.used),
          }
        }));
      }
    });
    return unsubscribe;
  }, [isConnected, subscribe, balance]);

  useEffect(() => {
    if (onRefresh) {
      onRefresh(loadBalance);
    }
  }, [onRefresh]);

  const futures = balance?.futures || { total: 0, free: 0, used: 0, unrealized_pnl: 0 };
  const total = parseFloat(futures.total || 0);
  const used = parseFloat(futures.used || 0);
  const unrealizedPnl = parseFloat(futures.unrealized_pnl || 0);

  // Helper to render a stat item (Dashboard StatCard 스타일)
  const StatItem = ({ label, value, subValue, color = '#1d1d1f', isPnl = false }) => (
    <div style={{
      background: '#ffffff',
      borderRadius: isMobile ? 12 : 16,
      padding: isMobile ? '14px 16px' : '24px',
      border: '1px solid #f5f5f7',
      transition: 'all 0.25s ease',
      cursor: 'default',
      minHeight: isMobile ? 'auto' : undefined,
    }}>
      <div style={{
        fontSize: isMobile ? 11 : 13,
        color: '#86868b',
        fontWeight: 500,
        marginBottom: isMobile ? 4 : 8,
        letterSpacing: '0.01em'
      }}>
        {label}
      </div>
      <div style={{
        fontSize: isMobile ? 20 : 28,
        fontWeight: 600,
        color: isPnl ? (value >= 0 ? '#34c759' : '#ff3b30') : color,
        letterSpacing: '-0.02em',
        lineHeight: 1.2,
      }}>
        {isPnl ? (value >= 0 ? '+' : '') : ''}
        {typeof value === 'number' ? value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : value}
        <span style={{ fontSize: isMobile ? 12 : 16, marginLeft: 2, fontWeight: 400, color: '#86868b' }}>
          {isPnl ? 'USDT' : (label.includes('KRW') ? 'KRW' : 'USDT')}
        </span>
      </div>
      {subValue && (
        <div style={{
          fontSize: isMobile ? 11 : 13,
          color: '#86868b',
          marginTop: isMobile ? 4 : 8,
          fontFamily: 'SF Mono, Monaco, monospace',
        }}>
          {subValue}
        </div>
      )}
    </div>
  );

  return (
    <div style={{ marginBottom: isMobile ? 12 : 20 }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: isMobile ? 12 : 16
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: isMobile ? 16 : 18, fontWeight: 600, color: '#1d1d1f' }}>
            <WalletOutlined style={{ marginRight: 8 }} />
            계정 잔고
          </span>
          {balance.mock && (
            <Tooltip title="Mock Data">
              <span style={{ fontSize: 10, background: '#fff7e6', color: '#fa8c16', padding: '2px 6px', borderRadius: 4, border: '1px solid #ffd591' }}>MOCK</span>
            </Tooltip>
          )}
        </div>
        <Button
          type="text"
          icon={<ReloadOutlined spin={loading} />}
          onClick={loadBalance}
          style={{ color: '#86868b' }}
        />
      </div>

      {/* Row/Col Grid - Dashboard 스타일 */}
      <Row gutter={isMobile ? [8, 8] : [16, 16]}>
        {/* 1. USDT Total */}
        <Col xs={12} sm={12} md={6}>
          <StatItem
            label="총 자산"
            value={total}
          />
        </Col>

        {/* 2. Used USDT */}
        <Col xs={12} sm={12} md={6}>
          <StatItem
            label="사용중"
            value={used}
            color="#f5a623"
          />
        </Col>

        {/* 3. Unrealized PnL */}
        <Col xs={12} sm={12} md={6}>
          <StatItem
            label="미실현 손익"
            value={unrealizedPnl}
            isPnl={true}
          />
        </Col>

        {/* 4. KRW Total */}
        <Col xs={12} sm={12} md={6}>
          <StatItem
            label="총 자산 (KRW)"
            value={Math.round(total * USD_KRW_RATE).toLocaleString()}
          />
        </Col>
      </Row>
    </div>
  );
}

export default memo(BalanceCard);

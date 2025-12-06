import { useState, useEffect, memo } from 'react';
import { accountAPI } from '../api/account';
import { bitgetAPI } from '../api/bitget';
import { useWebSocket } from '../context/WebSocketContext';
import { ReloadOutlined, WalletOutlined, CheckCircleOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { Button, Spin, Tooltip } from 'antd';

function BalanceCard({ onRefresh }) {
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

  // Helper to render a stat item
  const StatItem = ({ label, value, subValue, color = '#1d1d1f', isPnl = false }) => (
    <div style={{
      background: '#f5f5f7',
      borderRadius: 12,
      padding: '16px',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      minWidth: 140,
      flex: 1
    }}>
      <div style={{
        fontSize: 12,
        color: '#86868b',
        fontWeight: 700, // Bold label
        marginBottom: 4,
        letterSpacing: '0.01em'
      }}>
        {label}
      </div>
      <div style={{
        fontSize: 18,
        fontWeight: 600,
        color: isPnl ? (value >= 0 ? '#0071e3' : '#ff3b30') : color, // Blue for positive PnL
        fontFamily: 'SF Mono, Monaco, monospace',
      }}>
        {isPnl ? (value >= 0 ? '+' : '') : ''}
        {typeof value === 'number' ? value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : value}
        <span style={{ fontSize: 12, marginLeft: 2, fontWeight: 500, color: '#86868b' }}>
          {isPnl ? 'USDT' : (label.includes('KRW') ? 'KRW' : 'USDT')}
        </span>
      </div>
      {subValue && (
        <div style={{
          fontSize: 12,
          color: '#86868b',
          marginTop: 2,
          fontFamily: 'SF Mono, Monaco, monospace',
        }}>
          {subValue}
        </div>
      )}
    </div>
  );

  return (
    <div style={{
      background: '#ffffff',
      borderRadius: 16,
      padding: '24px',
      border: '1px solid #f5f5f7',
      boxShadow: '0 4px 20px rgba(0, 0, 0, 0.02)',
      marginBottom: 20
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 20
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{
            width: 32,
            height: 32,
            borderRadius: 8,
            background: '#0071e3',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white'
          }}>
            <WalletOutlined />
          </div>
          <span style={{ fontSize: 16, fontWeight: 600, color: '#1d1d1f' }}>계정 잔고</span>
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

      {/* Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
        gap: 12
      }}>
        {/* 1. USDT Total */}
        <StatItem
          label="총 자산 (USDT)"
          value={total}
        />

        {/* 2. KRW Total */}
        <StatItem
          label="총 자산 (KRW)"
          value={Math.round(total * USD_KRW_RATE).toLocaleString()}
        />

        {/* 3. Used USDT */}
        <StatItem
          label="사용중인 USDT"
          value={used}
          color="#f5a623"
        />

        {/* 4. Used KRW */}
        <StatItem
          label="사용중인 KRW"
          value={Math.round(used * USD_KRW_RATE).toLocaleString()}
          color="#f5a623"
        />

        {/* 5. Unrealized PnL */}
        <StatItem
          label="미실현 손익"
          value={unrealizedPnl}
          isPnl={true}
        />
      </div>
    </div>
  );
}

export default memo(BalanceCard);

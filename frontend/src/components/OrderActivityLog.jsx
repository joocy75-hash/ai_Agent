import { useState, useEffect, useRef, memo } from 'react';
import { orderAPI } from '../api/order';
import { alertsAPI } from '../api/alerts';
import { useWebSocket } from '../context/WebSocketContext';

function OrderActivityLog() {
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // all, orders, alerts
  const [autoScroll, setAutoScroll] = useState(true);
  const logEndRef = useRef(null);
  const { subscribe, isConnected } = useWebSocket();

  // 활동 로그 로드
  const loadActivities = async () => {
    try {
      setLoading(true);

      // 주문 이력과 알림을 병렬로 가져오기
      const [orderHistory, alerts] = await Promise.all([
        orderAPI.getOrderHistory(25, 0).catch(() => ({ orders: [] })),
        alertsAPI.getAll(25, 0).catch(() => ({ alerts: [] }))
      ]);

      // 주문을 활동 형식으로 변환
      const orderActivities = (orderHistory.orders || []).map(order => ({
        id: `order-${order.id}`,
        timestamp: order.timestamp || order.created_at,
        type: 'ORDER',
        severity: order.status === 'filled' ? 'SUCCESS' : order.status === 'rejected' ? 'ERROR' : 'INFO',
        symbol: order.symbol,
        message: `${order.side} ${order.qty} ${order.symbol} @ ${order.price_type === 'market' ? 'Market' : order.limit_price}`,
        details: order
      }));

      // 알림을 활동 형식으로 변환
      const alertActivities = (alerts.alerts || []).map(alert => ({
        id: `alert-${alert.id}`,
        timestamp: alert.timestamp,
        type: alert.level === 'ERROR' ? 'ERROR' : alert.level === 'WARNING' ? 'WARNING' : 'INFO',
        severity: alert.level,
        symbol: alert.symbol || '-',
        message: alert.message,
        details: alert
      }));

      // 모든 활동을 시간순으로 정렬
      const allActivities = [...orderActivities, ...alertActivities]
        .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
        .slice(0, 50);

      setActivities(allActivities);
      setLoading(false);
    } catch (error) {
      console.error('[OrderActivityLog] Error loading activities:', error);
      setLoading(false);
    }
  };

  useEffect(() => {
    loadActivities();

    // 30초마다 자동 새로고침
    const interval = setInterval(loadActivities, 30000);

    return () => clearInterval(interval);
  }, []);

  // WebSocket 실시간 업데이트
  useEffect(() => {
    if (!isConnected) return;

    const unsubscribeOrder = subscribe('order_update', (data) => {
      console.log('[OrderActivityLog] Order update:', data);

      if (data.data) {
        const newActivity = {
          id: `order-${data.data.id || Date.now()}`,
          timestamp: data.timestamp || new Date().toISOString(),
          type: 'ORDER',
          severity: 'INFO',
          symbol: data.data.symbol || '-',
          message: `${data.data.side} ${data.data.qty} ${data.data.symbol}`,
          details: data.data
        };

        setActivities(prev => [newActivity, ...prev].slice(0, 50));
      }
    });

    const unsubscribeAlert = subscribe('alert', (data) => {
      console.log('[OrderActivityLog] Alert update:', data);

      const newActivity = {
        id: `alert-${Date.now()}`,
        timestamp: data.timestamp || new Date().toISOString(),
        type: data.level || 'INFO',
        severity: data.level || 'INFO',
        symbol: data.symbol || '-',
        message: data.message,
        details: data
      };

      setActivities(prev => [newActivity, ...prev].slice(0, 50));
    });

    return () => {
      unsubscribeOrder();
      unsubscribeAlert();
    };
  }, [isConnected, subscribe]);

  // 자동 스크롤
  useEffect(() => {
    if (autoScroll && logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [activities, autoScroll]);

  // 필터링된 활동
  const filteredActivities = activities.filter(activity => {
    if (filter === 'all') return true;
    if (filter === 'orders') return activity.type === 'ORDER';
    if (filter === 'alerts') return activity.type === 'ERROR' || activity.type === 'WARNING' || activity.type === 'INFO';
    return true;
  });

  // 타입별 아이콘 및 색상
  const getActivityStyle = (type, severity) => {
    const styles = {
      ORDER: { icon: '📦', color: '#1565c0', bg: '#e3f2fd', border: '#90caf9' },
      ERROR: { icon: '❌', color: '#c62828', bg: '#ffebee', border: '#ef5350' },
      WARNING: { icon: '⚠️', color: '#f57c00', bg: '#fff3e0', border: '#ffb74d' },
      INFO: { icon: 'ℹ️', color: '#0288d1', bg: '#e1f5fe', border: '#4fc3f7' },
      SUCCESS: { icon: '✅', color: '#2e7d32', bg: '#e8f5e9', border: '#66bb6a' }
    };

    return styles[severity] || styles[type] || styles.INFO;
  };

  // 시간 포맷
  const formatTime = (timestamp) => {
    if (!timestamp) return '-';
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;

    // 1분 이내
    if (diff < 60000) {
      return '방금 전';
    }
    // 1시간 이내
    if (diff < 3600000) {
      return `${Math.floor(diff / 60000)}분 전`;
    }
    // 오늘
    if (date.toDateString() === now.toDateString()) {
      return date.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
    }
    // 그 외
    return date.toLocaleString('ko-KR', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div style={{
      background: 'white',
      padding: '1.5rem',
      borderRadius: '8px',
      boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
      border: '1px solid #e5e7eb'
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '1.5rem',
        paddingBottom: '1rem',
        borderBottom: '2px solid #f5f5f5',
        flexWrap: 'wrap',
        gap: '1rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span style={{ fontSize: '1.5rem' }}>📋</span>
          <div>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold', margin: 0, marginBottom: '0.25rem' }}>
              활동 로그
            </h3>
            <div style={{ fontSize: '0.75rem', color: '#666' }}>
              최근 {filteredActivities.length}개 활동
              {isConnected && (
                <span style={{
                  marginLeft: '0.5rem',
                  padding: '0.1rem 0.4rem',
                  background: '#e8f5e9',
                  color: '#2e7d32',
                  borderRadius: '4px',
                  fontSize: '0.7rem',
                  fontWeight: 'bold'
                }}>
                  실시간
                </span>
              )}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
          {/* Filter Buttons */}
          <div style={{ display: 'flex', gap: '0.25rem', background: '#f5f5f5', borderRadius: '6px', padding: '0.25rem' }}>
            {[
              { value: 'all', label: '전체' },
              { value: 'orders', label: '주문' },
              { value: 'alerts', label: '알림' }
            ].map(({ value, label }) => (
              <button
                key={value}
                onClick={() => setFilter(value)}
                style={{
                  padding: '0.4rem 0.8rem',
                  background: filter === value ? 'white' : 'transparent',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '0.75rem',
                  fontWeight: filter === value ? 'bold' : 'normal',
                  color: filter === value ? '#1565c0' : '#666',
                  boxShadow: filter === value ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
                  transition: 'all 0.2s'
                }}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Auto Scroll Toggle */}
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            style={{
              padding: '0.4rem 0.8rem',
              background: autoScroll ? '#e3f2fd' : '#f5f5f5',
              border: `1px solid ${autoScroll ? '#90caf9' : '#e0e0e0'}`,
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.75rem',
              fontWeight: 'bold',
              color: autoScroll ? '#1565c0' : '#666',
              transition: 'all 0.2s'
            }}
          >
            {autoScroll ? '📌 고정' : '📌 해제'}
          </button>

          {/* Refresh Button */}
          <button
            onClick={loadActivities}
            disabled={loading}
            style={{
              background: loading ? '#f5f5f5' : '#e3f2fd',
              border: '1px solid #90caf9',
              borderRadius: '6px',
              padding: '0.4rem 0.8rem',
              cursor: loading ? 'not-allowed' : 'pointer',
              fontSize: '0.75rem',
              fontWeight: 'bold',
              color: '#1565c0',
              opacity: loading ? 0.5 : 1,
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              transition: 'all 0.2s'
            }}
          >
            <span style={{ fontSize: '0.9rem' }}>🔄</span>
            새로고침
          </button>
        </div>
      </div>

      {/* Activity List */}
      <div style={{
        maxHeight: '400px',
        overflowY: 'auto',
        border: '1px solid #e5e7eb',
        borderRadius: '6px',
        background: '#fafafa'
      }}>
        {loading && filteredActivities.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#666' }}>
            로딩 중...
          </div>
        ) : filteredActivities.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#666' }}>
            활동 내역이 없습니다.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', padding: '0.5rem' }}>
            {filteredActivities.map((activity, index) => {
              const style = getActivityStyle(activity.type, activity.severity);

              return (
                <div
                  key={`${activity.id}-${index}`}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '0.75rem',
                    padding: '0.75rem',
                    background: 'white',
                    borderRadius: '6px',
                    border: `1px solid ${style.border}`,
                    borderLeft: `4px solid ${style.color}`,
                    transition: 'all 0.2s'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
                    e.currentTarget.style.transform = 'translateX(4px)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.boxShadow = 'none';
                    e.currentTarget.style.transform = 'translateX(0)';
                  }}
                >
                  {/* Icon */}
                  <div style={{
                    fontSize: '1.25rem',
                    flexShrink: 0,
                    width: '2rem',
                    height: '2rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: style.bg,
                    borderRadius: '50%'
                  }}>
                    {style.icon}
                  </div>

                  {/* Content */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.25rem' }}>
                      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                        <span style={{
                          fontSize: '0.7rem',
                          padding: '0.15rem 0.4rem',
                          background: style.bg,
                          color: style.color,
                          borderRadius: '4px',
                          fontWeight: 'bold',
                          textTransform: 'uppercase'
                        }}>
                          {activity.type}
                        </span>
                        {activity.symbol && activity.symbol !== '-' && (
                          <span style={{
                            fontSize: '0.7rem',
                            padding: '0.15rem 0.4rem',
                            background: '#f5f5f5',
                            color: '#333',
                            borderRadius: '4px',
                            fontWeight: 'bold'
                          }}>
                            {activity.symbol}
                          </span>
                        )}
                      </div>
                      <span style={{
                        fontSize: '0.7rem',
                        color: '#999',
                        whiteSpace: 'nowrap',
                        marginLeft: '0.5rem'
                      }}>
                        {formatTime(activity.timestamp)}
                      </span>
                    </div>
                    <div style={{
                      fontSize: '0.875rem',
                      color: '#333',
                      wordBreak: 'break-word'
                    }}>
                      {activity.message}
                    </div>
                  </div>
                </div>
              );
            })}
            <div ref={logEndRef} />
          </div>
        )}
      </div>

      {/* Footer Stats */}
      <div style={{
        marginTop: '1rem',
        padding: '0.75rem',
        background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
        borderRadius: '6px',
        display: 'flex',
        justifyContent: 'space-around',
        gap: '1rem',
        flexWrap: 'wrap'
      }}>
        {[
          { label: '총 활동', count: filteredActivities.length, icon: '📊' },
          { label: '주문', count: filteredActivities.filter(a => a.type === 'ORDER').length, icon: '📦' },
          { label: '에러', count: filteredActivities.filter(a => a.type === 'ERROR').length, icon: '❌' },
          { label: '경고', count: filteredActivities.filter(a => a.type === 'WARNING').length, icon: '⚠️' }
        ].map(({ label, count, icon }) => (
          <div key={label} style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '0.7rem', color: '#666', marginBottom: '0.25rem' }}>
              {icon} {label}
            </div>
            <div style={{ fontSize: '1.25rem', fontWeight: 'bold', color: '#333' }}>
              {count}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default memo(OrderActivityLog);

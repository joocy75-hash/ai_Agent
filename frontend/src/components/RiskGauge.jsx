import { useState, useEffect, memo } from 'react';
import { Card } from 'antd';
import { SafetyCertificateOutlined, ReloadOutlined, WarningOutlined } from '@ant-design/icons';
import { PieChart, Pie, Cell, ResponsiveContainer, RadialBarChart, RadialBar } from 'recharts';
import { analyticsAPI } from '../api/analytics';

/**
 * RiskGauge Component - Apple Style with Charts
 * 리스크 지표를 시각화하는 게이지 컴포넌트
 */
function RiskGauge() {
  const [riskMetrics, setRiskMetrics] = useState({
    mdd: 0,
    sharpe_ratio: 0,
    win_rate: 0,
    max_mdd_limit: -25.0,
    max_leverage: 10,
    total_trades: 0
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadRiskMetrics = async () => {
    try {
      setLoading(true);
      const data = await analyticsAPI.getRiskMetrics();
      console.log('[RiskGauge] Risk metrics loaded:', data);

      const metrics = {
        mdd: data.mdd ?? 0,
        sharpe_ratio: data.sharpe_ratio ?? 0,
        win_rate: data.win_rate ?? 0,
        max_mdd_limit: data.max_mdd_limit ?? -25.0,
        max_leverage: data.max_leverage ?? 10,
        total_trades: data.total_trades ?? 0
      };

      setRiskMetrics(metrics);

      if (metrics.total_trades < 10) {
        setError(`충분한 거래 데이터가 없습니다 (${metrics.total_trades}/10 거래)`);
      } else {
        setError('');
      }
    } catch (err) {
      console.log('[RiskGauge] ℹ️ Using default data');
      if (err.response?.status === 404) {
        setError('거래 데이터가 없습니다');
      } else {
        setError('거래 데이터 부족 - 10건 이상의 거래가 필요합니다');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRiskMetrics();
    const interval = setInterval(loadRiskMetrics, 60000);
    return () => clearInterval(interval);
  }, []);

  // 상태 계산 함수들
  const getMDDStatus = (mdd, limit = -25) => {
    const ratio = Math.abs(mdd) / Math.abs(limit);
    if (ratio < 0.5) return { status: '양호', color: '#34c759' };
    if (ratio < 0.8) return { status: '주의', color: '#ff9500' };
    return { status: '경고', color: '#ff3b30' };
  };

  const getSharpeStatus = (sharpe) => {
    if (sharpe >= 2.0) return { status: '우수', color: '#34c759' };
    if (sharpe >= 1.0) return { status: '양호', color: '#0071e3' };
    if (sharpe >= 0.5) return { status: '보통', color: '#ff9500' };
    return { status: '미흡', color: '#ff3b30' };
  };

  const getWinRateStatus = (winRate) => {
    if (winRate >= 60) return { status: '우수', color: '#34c759' };
    if (winRate >= 50) return { status: '양호', color: '#0071e3' };
    if (winRate >= 40) return { status: '보통', color: '#ff9500' };
    return { status: '미흡', color: '#ff3b30' };
  };

  const mddStatus = getMDDStatus(riskMetrics.mdd, riskMetrics.max_mdd_limit);
  const sharpeStatus = getSharpeStatus(riskMetrics.sharpe_ratio);
  const winRateStatus = getWinRateStatus(riskMetrics.win_rate);

  // 원형 게이지 컴포넌트
  const CircularGauge = ({ value, maxValue, color, label, unit = '%' }) => {
    const percentage = Math.min((Math.abs(value) / Math.abs(maxValue)) * 100, 100);
    const data = [
      { value: percentage, fill: color },
      { value: 100 - percentage, fill: '#f5f5f7' }
    ];

    return (
      <div style={{ textAlign: 'center' }}>
        <div style={{ position: 'relative', width: 100, height: 100, margin: '0 auto' }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                innerRadius={32}
                outerRadius={45}
                startAngle={90}
                endAngle={-270}
                dataKey="value"
                stroke="none"
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            textAlign: 'center',
          }}>
            <div style={{
              fontSize: 16,
              fontWeight: 700,
              color: '#1d1d1f',
              fontFamily: 'SF Mono, Monaco, monospace',
            }}>
              {typeof value === 'number' ? Math.round(value) : value}
            </div>
            <div style={{ fontSize: 10, color: '#86868b' }}>{unit}</div>
          </div>
        </div>
        <div style={{
          marginTop: 8,
          fontSize: 11,
          color: '#86868b',
          fontWeight: 500,
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
        }}>
          {label}
        </div>
      </div>
    );
  };

  // 상태 배지
  const StatusBadge = ({ status, color }) => (
    <span style={{
      display: 'inline-block',
      padding: '4px 10px',
      background: `${color}15`,
      color: color,
      borderRadius: 12,
      fontSize: 11,
      fontWeight: 600,
    }}>
      {status}
    </span>
  );

  return (
    <Card
      title={
        <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <SafetyCertificateOutlined style={{ color: '#0071e3' }} />
          리스크 관리 지표
        </span>
      }
      extra={
        <button
          onClick={loadRiskMetrics}
          disabled={loading}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '6px 12px',
            background: loading ? '#f5f5f7' : '#ffffff',
            border: '1px solid #d2d2d7',
            borderRadius: 8,
            cursor: loading ? 'not-allowed' : 'pointer',
            fontSize: 13,
            fontWeight: 500,
            color: '#1d1d1f',
            transition: 'all 0.2s ease',
            opacity: loading ? 0.6 : 1,
          }}
        >
          <ReloadOutlined spin={loading} style={{ fontSize: 12 }} />
          새로고침
        </button>
      }
      styles={{ body: { padding: 20 } }}
    >
      {/* 3개 원형 차트 */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: 16,
        marginBottom: 20,
      }}>
        <CircularGauge
          value={Math.abs(riskMetrics.mdd)}
          maxValue={Math.abs(riskMetrics.max_mdd_limit || 25)}
          color={mddStatus.color}
          label="MDD"
          unit="%"
        />
        <CircularGauge
          value={riskMetrics.sharpe_ratio}
          maxValue={3}
          color={sharpeStatus.color}
          label="Sharpe"
          unit=""
        />
        <CircularGauge
          value={riskMetrics.win_rate}
          maxValue={100}
          color={winRateStatus.color}
          label="승률"
          unit="%"
        />
      </div>

      {/* 상세 지표 카드 */}
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
      }}>
        {/* MDD */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '12px 16px',
          background: '#f5f5f7',
          borderRadius: 10,
        }}>
          <div>
            <div style={{ fontSize: 12, color: '#86868b', marginBottom: 2 }}>최대 낙폭 (MDD)</div>
            <div style={{
              fontSize: 18,
              fontWeight: 600,
              color: '#1d1d1f',
              fontFamily: 'SF Mono, Monaco, monospace',
            }}>
              {Math.round(riskMetrics.mdd)}%
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <StatusBadge status={mddStatus.status} color={mddStatus.color} />
            <div style={{ fontSize: 11, color: '#86868b', marginTop: 4 }}>
              한도: {Math.round(Math.abs(riskMetrics.max_mdd_limit || 25))}%
            </div>
          </div>
        </div>

        {/* Sharpe Ratio */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '12px 16px',
          background: '#f5f5f7',
          borderRadius: 10,
        }}>
          <div>
            <div style={{ fontSize: 12, color: '#86868b', marginBottom: 2 }}>샤프 비율</div>
            <div style={{
              fontSize: 18,
              fontWeight: 600,
              color: '#1d1d1f',
              fontFamily: 'SF Mono, Monaco, monospace',
            }}>
              {riskMetrics.sharpe_ratio.toFixed(1)}
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <StatusBadge status={sharpeStatus.status} color={sharpeStatus.color} />
            <div style={{ fontSize: 11, color: '#86868b', marginTop: 4 }}>
              목표: &gt; 2.0
            </div>
          </div>
        </div>

        {/* Win Rate */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '12px 16px',
          background: '#f5f5f7',
          borderRadius: 10,
        }}>
          <div>
            <div style={{ fontSize: 12, color: '#86868b', marginBottom: 2 }}>승률</div>
            <div style={{
              fontSize: 18,
              fontWeight: 600,
              color: '#1d1d1f',
              fontFamily: 'SF Mono, Monaco, monospace',
            }}>
              {Math.round(riskMetrics.win_rate)}%
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <StatusBadge status={winRateStatus.status} color={winRateStatus.color} />
            <div style={{ fontSize: 11, color: '#86868b', marginTop: 4 }}>
              목표: &gt; 60%
            </div>
          </div>
        </div>
      </div>

      {/* 경고 메시지 */}
      {error && (
        <div style={{
          marginTop: 16,
          padding: '12px 16px',
          background: '#fff8e6',
          border: '1px solid #ffe58f',
          borderRadius: 8,
          fontSize: 13,
          color: '#d48806',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}>
          <WarningOutlined />
          <span>{error}</span>
        </div>
      )}
    </Card>
  );
}

export default memo(RiskGauge);

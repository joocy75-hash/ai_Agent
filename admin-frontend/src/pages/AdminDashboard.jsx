import React, { useState, useEffect } from 'react';
import {
  Users,
  Bot,
  TrendingUp,
  DollarSign,
  Activity,
  AlertTriangle,
  UserX,
  PlayCircle,
  PauseCircle,
  RefreshCw,
  Shield,
  FileText,
  UserPlus,
  X,
  Database,
  HardDrive,
  Download,
  CheckCircle
} from 'lucide-react';
import api from '../api/client';
import UserDetailModal from '../components/UserDetailModal';
import './AdminDashboard.css';

const AdminDashboard = () => {
  const [loading, setLoading] = useState(true);
  const [globalStats, setGlobalStats] = useState(null);
  const [activeBots, setActiveBots] = useState([]);
  const [riskUsers, setRiskUsers] = useState(null);
  const [tradingVolume, setTradingVolume] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');

  // Users Tab state
  const [users, setUsers] = useState([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState('all'); // all, active, suspended
  const [filterRole, setFilterRole] = useState('all'); // all, admin, user

  // Logs Tab state
  const [logs, setLogs] = useState([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [logType, setLogType] = useState('system'); // system, bot, trading
  const [logLevel, setLogLevel] = useState(''); // '', CRITICAL, ERROR, WARNING, INFO
  const [logUserId, setLogUserId] = useState('');
  const [logLimit, setLogLimit] = useState(100);

  // User Detail Modal state
  const [selectedUserId, setSelectedUserId] = useState(null);
  const [showUserDetailModal, setShowUserDetailModal] = useState(false);

  // Create User Modal state
  const [showCreateUserModal, setShowCreateUserModal] = useState(false);
  const [newUserEmail, setNewUserEmail] = useState('');
  const [newUserPassword, setNewUserPassword] = useState('');
  const [newUserRole, setNewUserRole] = useState('user');
  const [createUserLoading, setCreateUserLoading] = useState(false);

  // Cache Management state
  const [cacheInfo, setCacheInfo] = useState(null);
  const [cacheLoading, setCacheLoading] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    fetchAdminData();
    const interval = setInterval(fetchAdminData, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (activeTab === 'users') {
      fetchUsers();
    } else if (activeTab === 'logs') {
      fetchLogs();
    } else if (activeTab === 'cache') {
      fetchCacheInfo();
    }
  }, [activeTab]);

  useEffect(() => {
    if (activeTab === 'logs') {
      fetchLogs();
    }
  }, [logType, logLevel, logUserId, logLimit]);

  const fetchAdminData = async () => {
    try {
      setLoading(true);
      const [statsRes, botsRes, riskRes, volumeRes] = await Promise.all([
        api.get('/admin/analytics/global-summary'),
        api.get('/admin/bots/active'),
        api.get('/admin/analytics/risk-users?limit=5'),
        api.get('/admin/analytics/trading-volume?days=7')
      ]);

      setGlobalStats(statsRes.data);
      setActiveBots(botsRes.data.active_bots || []);
      setRiskUsers(riskRes.data);
      setTradingVolume(volumeRes.data);
    } catch (error) {
      console.error('Failed to fetch admin data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePauseBot = async (userId) => {
    if (!window.confirm(`사용자 ${userId}번의 봇을 정지하시겠습니까?`)) return;

    try {
      await api.post(`/admin/bots/${userId}/pause`);
      alert('봇이 정지되었습니다.');
      fetchAdminData();
    } catch (error) {
      alert('봇 정지 실패: ' + error.message);
    }
  };

  const handleRestartBot = async (userId) => {
    if (!window.confirm(`사용자 ${userId}번의 봇을 재시작하시겠습니까?`)) return;

    try {
      await api.post(`/admin/bots/${userId}/restart`);
      alert('봇이 재시작되었습니다.');
      fetchAdminData();
    } catch (error) {
      alert('봇 재시작 실패: ' + error.message);
    }
  };

  const handlePauseAllBots = async () => {
    if (!window.confirm('⚠️ 전체 봇을 긴급 정지하시겠습니까? 이 작업은 모든 사용자의 봇을 정지시킵니다.')) return;

    try {
      await api.post('/admin/bots/pause-all');
      alert('전체 봇이 긴급 정지되었습니다.');
      fetchAdminData();
    } catch (error) {
      alert('전체 봇 정지 실패: ' + error.message);
    }
  };

  // Users Management functions
  const fetchUsers = async () => {
    try {
      setUsersLoading(true);
      const response = await api.get('/admin/users');
      setUsers(response.data.users || []);
    } catch (error) {
      console.error('Failed to fetch users:', error);
      alert('사용자 목록 조회 실패');
    } finally {
      setUsersLoading(false);
    }
  };

  const handleCreateUser = async () => {
    if (!newUserEmail || !newUserPassword) {
      alert('이메일과 비밀번호를 입력하세요');
      return;
    }
    if (newUserPassword.length < 8) {
      alert('비밀번호는 최소 8자 이상이어야 합니다');
      return;
    }

    try {
      setCreateUserLoading(true);
      await api.post('/admin/users', {
        email: newUserEmail,
        password: newUserPassword,
        role: newUserRole
      });
      alert('사용자가 생성되었습니다');
      setShowCreateUserModal(false);
      setNewUserEmail('');
      setNewUserPassword('');
      setNewUserRole('user');
      fetchUsers();
    } catch (error) {
      const errorMsg = error.response?.data?.detail || error.message;
      alert('사용자 생성 실패: ' + errorMsg);
    } finally {
      setCreateUserLoading(false);
    }
  };

  const handleSuspendUser = async (userId, email) => {
    if (!window.confirm(`사용자 ${email}의 계정을 정지하시겠습니까?\n정지된 사용자는 로그인할 수 없으며, 모든 봇이 정지됩니다.`)) return;

    try {
      await api.post(`/admin/users/${userId}/suspend`);
      alert('계정이 정지되었습니다.');
      fetchUsers();
    } catch (error) {
      alert('계정 정지 실패: ' + error.message);
    }
  };

  const handleActivateUser = async (userId, email) => {
    if (!window.confirm(`사용자 ${email}의 계정을 활성화하시겠습니까?`)) return;

    try {
      await api.post(`/admin/users/${userId}/activate`);
      alert('계정이 활성화되었습니다.');
      fetchUsers();
    } catch (error) {
      alert('계정 활성화 실패: ' + error.message);
    }
  };

  const handleForceLogout = async (userId, email) => {
    if (!window.confirm(`사용자 ${email}을 강제 로그아웃하시겠습니까?\n모든 봇이 정지되며 즉시 로그아웃됩니다.`)) return;

    try {
      await api.post(`/admin/users/${userId}/force-logout`);
      alert('사용자가 강제 로그아웃되었습니다.');
      fetchUsers();
    } catch (error) {
      alert('강제 로그아웃 실패: ' + error.message);
    }
  };

  // Logs Management functions
  const fetchLogs = async () => {
    try {
      setLogsLoading(true);
      let endpoint = '';
      const params = new URLSearchParams();

      if (logLimit) params.append('limit', logLimit);

      if (logType === 'system') {
        endpoint = '/admin/logs/system';
        if (logLevel) params.append('level', logLevel);
      } else if (logType === 'bot') {
        endpoint = '/admin/logs/bot';
        if (logUserId) params.append('user_id', logUserId);
      } else if (logType === 'trading') {
        endpoint = '/admin/logs/trading';
        if (logUserId) params.append('user_id', logUserId);
      }

      const queryString = params.toString();
      const url = queryString ? `${endpoint}?${queryString}` : endpoint;

      const response = await api.get(url);
      setLogs(response.data.logs || []);
    } catch (error) {
      console.error('Failed to fetch logs:', error);
      setLogs([]);
    } finally {
      setLogsLoading(false);
    }
  };

  // Fetch cache info
  const fetchCacheInfo = async () => {
    setCacheLoading(true);
    try {
      const response = await api.get('/backtest/cache/info');
      setCacheInfo(response.data);
    } catch (error) {
      console.error('Failed to fetch cache info:', error);
      setCacheInfo(null);
    } finally {
      setCacheLoading(false);
    }
  };

  // Show message helper
  const showMessage = (text, type = 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 3000);
  };

  // Filter users
  const filteredUsers = users.filter(user => {
    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      if (!user.email.toLowerCase().includes(query) && !user.id.toString().includes(query)) {
        return false;
      }
    }

    // Status filter
    if (filterStatus !== 'all') {
      if (filterStatus === 'active' && !user.is_active) return false;
      if (filterStatus === 'suspended' && user.is_active) return false;
    }

    // Role filter
    if (filterRole !== 'all') {
      if (user.role !== filterRole) return false;
    }

    return true;
  });

  if (loading && !globalStats) {
    return (
      <div className="loading-container">
        <div className="loading-content">
          <RefreshCw className="loading-spinner" />
          <p style={{ color: '#6b7280' }}>관리자 데이터 로딩 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-dashboard">
      {/* Header */}
      <div className="admin-header">
        <div className="admin-header-content">
          <div className="admin-title-section">
            <h1>
              <Shield style={{ width: '2rem', height: '2rem', color: '#2563eb' }} />
              관리자 대시보드
            </h1>
            <p>시스템 전체 모니터링 및 제어</p>
          </div>
          <button onClick={fetchAdminData} className="admin-refresh-btn">
            <RefreshCw style={{ width: '1rem', height: '1rem' }} />
            새로고침
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="admin-tabs">
        <div className="admin-tabs-list">
          {['overview', 'bots', 'users', 'logs', 'cache'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`admin-tab-btn ${activeTab === tab ? 'active' : ''}`}
            >
              {tab === 'overview' && '전체 개요'}
              {tab === 'bots' && '봇 관리'}
              {tab === 'users' && '사용자 관리'}
              {tab === 'logs' && '로그 조회'}
              {tab === 'cache' && '📊 캐시 관리'}
            </button>
          ))}
        </div>
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && globalStats && (
        <div>
          {/* Stats Grid */}
          <div className="stats-grid">
            {/* Total Users */}
            <div className="stat-card">
              <div className="stat-card-header">
                <Users style={{ width: '1.5rem', height: '1.5rem', color: '#2563eb' }} />
                <h3 className="stat-card-title">전체 사용자</h3>
              </div>
              <p className="stat-card-value">{globalStats.users.total}</p>
              <p className="stat-card-subtitle">
                활성: {globalStats.users.active} | 비활성: {globalStats.users.inactive}
              </p>
            </div>

            {/* Running Bots */}
            <div className="stat-card">
              <div className="stat-card-header">
                <Bot style={{ width: '1.5rem', height: '1.5rem', color: '#22c55e' }} />
                <h3 className="stat-card-title">실행 중인 봇</h3>
              </div>
              <p className="stat-card-value">{globalStats.bots.running}</p>
              <p className="stat-card-subtitle">전체: {globalStats.bots.total}</p>
            </div>

            {/* Total AUM */}
            <div className="stat-card">
              <div className="stat-card-header">
                <DollarSign style={{ width: '1.5rem', height: '1.5rem', color: '#eab308' }} />
                <h3 className="stat-card-title">총 AUM</h3>
              </div>
              <p className="stat-card-value">${globalStats.financials.total_aum.toLocaleString()}</p>
              <p className="stat-card-subtitle">미결제: {globalStats.financials.open_positions}건</p>
            </div>

            {/* Total P&L */}
            <div className="stat-card">
              <div className="stat-card-header">
                <TrendingUp style={{ width: '1.5rem', height: '1.5rem', color: '#a855f7' }} />
                <h3 className="stat-card-title">총 P&L</h3>
              </div>
              <p className="stat-card-value" style={{ color: globalStats.financials.total_pnl >= 0 ? '#16a34a' : '#dc2626' }}>
                ${globalStats.financials.total_pnl.toLocaleString()}
              </p>
              <p className="stat-card-subtitle">거래: {globalStats.financials.total_trades}건</p>
            </div>
          </div>

          {/* Risk Users & Trading Volume */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginTop: '1.5rem' }}>
            {/* Risk Users */}
            {riskUsers && (
              <div className="risk-users-section">
                <div className="risk-users-header">
                  <AlertTriangle style={{ width: '1.25rem', height: '1.25rem', color: '#f97316' }} />
                  <h2>위험 사용자</h2>
                </div>
                <div>
                  {riskUsers.top_loss_users.length > 0 ? (
                    <div>
                      <h4 style={{ fontSize: '0.875rem', fontWeight: '500', marginBottom: '0.75rem' }}>손실 사용자 Top 5</h4>
                      <table className="risk-users-table">
                        <thead>
                          <tr>
                            <th>사용자</th>
                            <th>거래</th>
                            <th>손실률</th>
                            <th>P&L</th>
                          </tr>
                        </thead>
                        <tbody>
                          {riskUsers.top_loss_users.map((user) => (
                            <tr key={user.user_id}>
                              <td>{user.email}</td>
                              <td>{user.trade_count}건</td>
                              <td>{user.loss_rate}%</td>
                              <td className="text-red">${user.total_pnl.toFixed(2)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="empty-state">손실 사용자가 없습니다</p>
                  )}

                  {riskUsers.high_frequency_traders.length > 0 && (
                    <div style={{ marginTop: '1.5rem' }}>
                      <h4 style={{ fontSize: '0.875rem', fontWeight: '500', marginBottom: '0.75rem' }}>고빈도 거래자</h4>
                      <table className="risk-users-table">
                        <thead>
                          <tr>
                            <th>사용자</th>
                            <th>거래 수</th>
                            <th>평균 P&L</th>
                          </tr>
                        </thead>
                        <tbody>
                          {riskUsers.high_frequency_traders.slice(0, 3).map((user) => (
                            <tr key={user.user_id}>
                              <td>{user.email}</td>
                              <td>{user.trade_count}건</td>
                              <td style={{ color: user.total_pnl >= 0 ? '#16a34a' : '#dc2626' }}>
                                ${user.avg_pnl_per_trade.toFixed(2)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Trading Volume */}
            {tradingVolume && (
              <div className="risk-users-section">
                <div className="risk-users-header">
                  <Activity style={{ width: '1.25rem', height: '1.25rem', color: '#22c55e' }} />
                  <h2>거래량 통계 (최근 7일)</h2>
                </div>
                <div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
                    <div style={{ textAlign: 'center' }}>
                      <p style={{ fontSize: '0.875rem', color: '#6b7280' }}>총 거래량</p>
                      <p style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#111827' }}>
                        ${tradingVolume.summary.total_volume.toFixed(2)}
                      </p>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                      <p style={{ fontSize: '0.875rem', color: '#6b7280' }}>총 거래 수</p>
                      <p style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#111827' }}>
                        {tradingVolume.summary.total_trades}
                      </p>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                      <p style={{ fontSize: '0.875rem', color: '#6b7280' }}>평균 거래</p>
                      <p style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#111827' }}>
                        ${tradingVolume.summary.avg_trade_size.toFixed(2)}
                      </p>
                    </div>
                  </div>

                  <div>
                    <h4 style={{ fontSize: '0.875rem', fontWeight: '500', marginBottom: '0.75rem' }}>인기 심볼 Top 5</h4>
                    <table className="risk-users-table">
                      <thead>
                        <tr>
                          <th>심볼</th>
                          <th>거래량</th>
                          <th>거래 수</th>
                        </tr>
                      </thead>
                      <tbody>
                        {tradingVolume.top_symbols.map((symbol, idx) => (
                          <tr key={idx}>
                            <td>{symbol.symbol}</td>
                            <td>${symbol.volume.toFixed(2)}</td>
                            <td>{symbol.trade_count}건</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* User Statistics */}
          {users.length > 0 && (
            <div className="risk-users-section" style={{ marginTop: '1.5rem' }}>
              <div className="risk-users-header">
                <Users style={{ width: '1.25rem', height: '1.25rem', color: '#2563eb' }} />
                <h2>사용자 통계</h2>
              </div>
              <div>
                {/* Top Performers */}
                <div>
                  <h4 style={{ fontSize: '0.875rem', fontWeight: '500', marginBottom: '0.75rem' }}>수익 상위 사용자 Top 5</h4>
                  <table className="risk-users-table">
                    <thead>
                      <tr>
                        <th>사용자</th>
                        <th>역할</th>
                        <th>총 거래</th>
                        <th>총 P&L</th>
                        <th>활성 봇</th>
                      </tr>
                    </thead>
                    <tbody>
                      {users
                        .filter(u => u.total_trades > 0)
                        .sort((a, b) => (b.total_pnl || 0) - (a.total_pnl || 0))
                        .slice(0, 5)
                        .map((user) => (
                          <tr key={user.id}>
                            <td>{user.email}</td>
                            <td>
                              <span style={{
                                padding: '0.25rem 0.5rem',
                                borderRadius: '9999px',
                                fontSize: '0.75rem',
                                background: user.role === 'admin' ? '#dbeafe' : '#f3f4f6',
                                color: user.role === 'admin' ? '#1e40af' : '#374151'
                              }}>
                                {user.role === 'admin' ? '관리자' : '일반'}
                              </span>
                            </td>
                            <td>{user.total_trades}건</td>
                            <td className="text-green">${user.total_pnl.toFixed(2)}</td>
                            <td>{user.active_bots_count}개</td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>

                {/* Most Active Traders */}
                <div style={{ marginTop: '1.5rem' }}>
                  <h4 style={{ fontSize: '0.875rem', fontWeight: '500', marginBottom: '0.75rem' }}>거래 활성도 Top 5</h4>
                  <table className="risk-users-table">
                    <thead>
                      <tr>
                        <th>사용자</th>
                        <th>총 거래</th>
                        <th>활성 봇</th>
                        <th>총 P&L</th>
                        <th>상태</th>
                      </tr>
                    </thead>
                    <tbody>
                      {users
                        .sort((a, b) => (b.total_trades || 0) - (a.total_trades || 0))
                        .slice(0, 5)
                        .map((user) => (
                          <tr key={user.id}>
                            <td>{user.email}</td>
                            <td>{user.total_trades}건</td>
                            <td>{user.active_bots_count}개</td>
                            <td style={{ color: user.total_pnl >= 0 ? '#16a34a' : '#dc2626' }}>
                              {user.total_pnl >= 0 ? '+' : ''}${user.total_pnl.toFixed(2)}
                            </td>
                            <td>
                              <span style={{
                                padding: '0.25rem 0.5rem',
                                borderRadius: '9999px',
                                fontSize: '0.75rem',
                                background: user.is_active ? '#dcfce7' : '#fee2e2',
                                color: user.is_active ? '#166534' : '#991b1b'
                              }}>
                                {user.is_active ? '활성' : '정지됨'}
                              </span>
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Bots Tab */}
      {activeTab === 'bots' && (
        <div>
          {/* Emergency Stop */}
          <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '0.5rem', padding: '1rem', marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <h3 style={{ fontSize: '1.125rem', fontWeight: '600', color: '#7f1d1d', display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
                  <AlertTriangle style={{ width: '1.25rem', height: '1.25rem' }} />
                  긴급 정지
                </h3>
                <p style={{ fontSize: '0.875rem', color: '#991b1b', marginTop: '0.25rem' }}>
                  모든 봇을 즉시 정지합니다. 긴급 상황에만 사용하세요.
                </p>
              </div>
              <button onClick={handlePauseAllBots} className="emergency-stop-btn">
                전체 봇 긴급 정지
              </button>
            </div>
          </div>

          {/* Active Bots */}
          <div className="bots-section">
            <div className="bots-header">
              <h2>
                <Bot style={{ width: '1.25rem', height: '1.25rem', color: '#22c55e', marginRight: '0.5rem' }} />
                활성 봇 목록 ({activeBots.length}개)
              </h2>
            </div>
            <div>
              {activeBots.length > 0 ? (
                <div className="bots-list">
                  {activeBots.map((bot) => (
                    <div key={bot.user_id} className="bot-card">
                      <div className="bot-info">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                          <div style={{
                            width: '0.75rem',
                            height: '0.75rem',
                            borderRadius: '9999px',
                            background: bot.is_running ? '#22c55e' : '#9ca3af'
                          }} />
                          <div>
                            <p className="bot-user">User #{bot.user_id} - {bot.user_email}</p>
                            <div className="bot-details">
                              <span>전략: {bot.strategy_name || 'N/A'}</span>
                              <span>상태: {bot.is_running ? '실행 중' : '정지'}</span>
                              <span>업데이트: {new Date(bot.updated_at).toLocaleString('ko-KR')}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                      <div className="bot-actions">
                        {bot.is_running ? (
                          <button onClick={() => handlePauseBot(bot.user_id)} className="bot-action-btn pause">
                            <PauseCircle style={{ width: '1rem', height: '1rem' }} />
                            정지
                          </button>
                        ) : (
                          <button onClick={() => handleRestartBot(bot.user_id)} className="bot-action-btn restart">
                            <PlayCircle style={{ width: '1rem', height: '1rem' }} />
                            재시작
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="empty-state">실행 중인 봇이 없습니다</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Users Tab */}
      {activeTab === 'users' && (
        <div>
          <div className="bots-section">
            <div className="bots-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2>
                <Users style={{ width: '1.25rem', height: '1.25rem', color: '#2563eb', marginRight: '0.5rem' }} />
                사용자 관리 ({filteredUsers.length}명)
              </h2>
              <button
                onClick={() => setShowCreateUserModal(true)}
                style={{
                  padding: '0.5rem 1rem',
                  background: '#2563eb',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.5rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  fontWeight: '500',
                  fontSize: '0.875rem'
                }}
              >
                <UserPlus style={{ width: '1rem', height: '1rem' }} />
                사용자 추가
              </button>
            </div>

            {/* Filters */}
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
              <input
                type="text"
                placeholder="이메일 또는 ID로 검색..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  padding: '0.5rem 1rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '0.5rem',
                  fontSize: '0.875rem'
                }}
              />
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                style={{
                  padding: '0.5rem 1rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '0.5rem',
                  fontSize: '0.875rem'
                }}
              >
                <option value="all">모든 상태</option>
                <option value="active">활성</option>
                <option value="suspended">정지됨</option>
              </select>
              <select
                value={filterRole}
                onChange={(e) => setFilterRole(e.target.value)}
                style={{
                  padding: '0.5rem 1rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '0.5rem',
                  fontSize: '0.875rem'
                }}
              >
                <option value="all">모든 역할</option>
                <option value="admin">관리자</option>
                <option value="user">일반 사용자</option>
              </select>
            </div>

            {/* Users Table */}
            {usersLoading ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
                <RefreshCw className="loading-spinner" style={{ display: 'inline-block' }} />
                <p>사용자 목록 로딩 중...</p>
              </div>
            ) : filteredUsers.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
                <p>검색 결과가 없습니다.</p>
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table className="risk-users-table" style={{ width: '100%' }}>
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>이메일</th>
                      <th>역할</th>
                      <th>상태</th>
                      <th>총 거래</th>
                      <th>총 손익</th>
                      <th>활성 봇</th>
                      <th>가입일</th>
                      <th>정지일</th>
                      <th>작업</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredUsers.map((user) => (
                      <tr key={user.id}>
                        <td>#{user.id}</td>
                        <td>{user.email}</td>
                        <td>
                          <span style={{
                            padding: '0.25rem 0.75rem',
                            borderRadius: '9999px',
                            fontSize: '0.75rem',
                            fontWeight: '500',
                            background: user.role === 'admin' ? '#dbeafe' : '#f3f4f6',
                            color: user.role === 'admin' ? '#1e40af' : '#374151'
                          }}>
                            {user.role === 'admin' ? '관리자' : '일반'}
                          </span>
                        </td>
                        <td>
                          <span style={{
                            padding: '0.25rem 0.75rem',
                            borderRadius: '9999px',
                            fontSize: '0.75rem',
                            fontWeight: '500',
                            background: user.is_active ? '#dcfce7' : '#fee2e2',
                            color: user.is_active ? '#166534' : '#991b1b'
                          }}>
                            {user.is_active ? '활성' : '정지됨'}
                          </span>
                        </td>
                        <td style={{ textAlign: 'right', fontWeight: '500' }}>
                          {user.total_trades || 0}건
                        </td>
                        <td style={{
                          textAlign: 'right',
                          fontWeight: '600',
                          color: user.total_pnl >= 0 ? '#16a34a' : '#dc2626'
                        }}>
                          {user.total_pnl >= 0 ? '+' : ''}${(user.total_pnl || 0).toFixed(2)}
                        </td>
                        <td style={{ textAlign: 'center', fontWeight: '500' }}>
                          <span style={{
                            padding: '0.25rem 0.5rem',
                            borderRadius: '0.375rem',
                            fontSize: '0.75rem',
                            background: user.active_bots_count > 0 ? '#dcfce7' : '#f3f4f6',
                            color: user.active_bots_count > 0 ? '#166534' : '#6b7280'
                          }}>
                            {user.active_bots_count || 0}개
                          </span>
                        </td>
                        <td>{user.created_at ? new Date(user.created_at).toLocaleDateString('ko-KR') : 'N/A'}</td>
                        <td>{user.suspended_at ? new Date(user.suspended_at).toLocaleDateString('ko-KR') : '-'}</td>
                        <td>
                          <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <button
                              onClick={() => {
                                setSelectedUserId(user.id);
                                setShowUserDetailModal(true);
                              }}
                              style={{
                                padding: '0.25rem 0.75rem',
                                fontSize: '0.75rem',
                                background: '#dbeafe',
                                color: '#1e40af',
                                border: '1px solid #bfdbfe',
                                borderRadius: '0.375rem',
                                cursor: 'pointer',
                                fontWeight: '500'
                              }}
                            >
                              상세보기
                            </button>
                            {user.is_active ? (
                              <button
                                onClick={() => handleSuspendUser(user.id, user.email)}
                                style={{
                                  padding: '0.25rem 0.75rem',
                                  fontSize: '0.75rem',
                                  background: '#fee2e2',
                                  color: '#991b1b',
                                  border: '1px solid #fecaca',
                                  borderRadius: '0.375rem',
                                  cursor: 'pointer',
                                  fontWeight: '500'
                                }}
                                disabled={user.role === 'admin'}
                              >
                                정지
                              </button>
                            ) : (
                              <button
                                onClick={() => handleActivateUser(user.id, user.email)}
                                style={{
                                  padding: '0.25rem 0.75rem',
                                  fontSize: '0.75rem',
                                  background: '#dcfce7',
                                  color: '#166534',
                                  border: '1px solid #bbf7d0',
                                  borderRadius: '0.375rem',
                                  cursor: 'pointer',
                                  fontWeight: '500'
                                }}
                              >
                                활성화
                              </button>
                            )}
                            <button
                              onClick={() => handleForceLogout(user.id, user.email)}
                              style={{
                                padding: '0.25rem 0.75rem',
                                fontSize: '0.75rem',
                                background: '#fef3c7',
                                color: '#92400e',
                                border: '1px solid #fde68a',
                                borderRadius: '0.375rem',
                                cursor: 'pointer',
                                fontWeight: '500'
                              }}
                              disabled={user.role === 'admin'}
                            >
                              강제 로그아웃
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Logs Tab */}
      {activeTab === 'logs' && (
        <div>
          <div className="bots-section">
            <div className="bots-header">
              <h2>
                <FileText style={{ width: '1.25rem', height: '1.25rem', color: '#a855f7', marginRight: '0.5rem' }} />
                로그 조회 ({logs.length}건)
              </h2>
            </div>

            {/* Log Type Tabs */}
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', borderBottom: '1px solid #e5e7eb' }}>
              <button
                onClick={() => setLogType('system')}
                style={{
                  padding: '0.75rem 1.5rem',
                  border: 'none',
                  background: 'transparent',
                  cursor: 'pointer',
                  fontWeight: logType === 'system' ? '600' : '400',
                  color: logType === 'system' ? '#2563eb' : '#6b7280',
                  borderBottom: logType === 'system' ? '2px solid #2563eb' : 'none'
                }}
              >
                시스템 로그
              </button>
              <button
                onClick={() => setLogType('bot')}
                style={{
                  padding: '0.75rem 1.5rem',
                  border: 'none',
                  background: 'transparent',
                  cursor: 'pointer',
                  fontWeight: logType === 'bot' ? '600' : '400',
                  color: logType === 'bot' ? '#2563eb' : '#6b7280',
                  borderBottom: logType === 'bot' ? '2px solid #2563eb' : 'none'
                }}
              >
                봇 로그
              </button>
              <button
                onClick={() => setLogType('trading')}
                style={{
                  padding: '0.75rem 1.5rem',
                  border: 'none',
                  background: 'transparent',
                  cursor: 'pointer',
                  fontWeight: logType === 'trading' ? '600' : '400',
                  color: logType === 'trading' ? '#2563eb' : '#6b7280',
                  borderBottom: logType === 'trading' ? '2px solid #2563eb' : 'none'
                }}
              >
                거래 로그
              </button>
            </div>

            {/* Filters */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
              {logType === 'system' && (
                <select
                  value={logLevel}
                  onChange={(e) => setLogLevel(e.target.value)}
                  style={{
                    padding: '0.5rem 1rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.5rem',
                    fontSize: '0.875rem'
                  }}
                >
                  <option value="">모든 레벨</option>
                  <option value="CRITICAL">CRITICAL</option>
                  <option value="ERROR">ERROR</option>
                  <option value="WARNING">WARNING</option>
                  <option value="INFO">INFO</option>
                </select>
              )}
              {(logType === 'bot' || logType === 'trading') && (
                <input
                  type="number"
                  placeholder="사용자 ID (선택)"
                  value={logUserId}
                  onChange={(e) => setLogUserId(e.target.value)}
                  style={{
                    padding: '0.5rem 1rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.5rem',
                    fontSize: '0.875rem'
                  }}
                />
              )}
              <select
                value={logLimit}
                onChange={(e) => setLogLimit(Number(e.target.value))}
                style={{
                  padding: '0.5rem 1rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '0.5rem',
                  fontSize: '0.875rem'
                }}
              >
                <option value="50">최근 50건</option>
                <option value="100">최근 100건</option>
                <option value="200">최근 200건</option>
                <option value="500">최근 500건</option>
              </select>
              <button
                onClick={fetchLogs}
                style={{
                  padding: '0.5rem 1rem',
                  background: '#2563eb',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.5rem',
                  fontSize: '0.875rem',
                  cursor: 'pointer',
                  fontWeight: '500',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem'
                }}
              >
                <RefreshCw style={{ width: '1rem', height: '1rem' }} />
                새로고침
              </button>
            </div>

            {/* Logs Table */}
            {logsLoading ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
                <RefreshCw className="loading-spinner" style={{ display: 'inline-block' }} />
                <p>로그 로딩 중...</p>
              </div>
            ) : logs.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
                <p>로그가 없습니다.</p>
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table className="risk-users-table" style={{ width: '100%' }}>
                  <thead>
                    <tr>
                      <th style={{ width: '80px' }}>ID</th>
                      {logType !== 'system' && <th style={{ width: '100px' }}>사용자 ID</th>}
                      {logType !== 'system' && <th style={{ width: '200px' }}>이메일</th>}
                      <th style={{ width: '150px' }}>이벤트 타입</th>
                      <th>메시지</th>
                      <th style={{ width: '180px' }}>시간</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.map((log) => (
                      <tr key={log.id}>
                        <td>#{log.id}</td>
                        {logType !== 'system' && <td>#{log.user_id}</td>}
                        {logType !== 'system' && <td>{log.user_email || 'N/A'}</td>}
                        <td>
                          <span style={{
                            padding: '0.25rem 0.75rem',
                            borderRadius: '9999px',
                            fontSize: '0.75rem',
                            fontWeight: '500',
                            background: log.event_type?.includes('error') || log.event_type?.includes('critical') ? '#fee2e2' :
                              log.event_type?.includes('warning') ? '#fef3c7' : '#f3f4f6',
                            color: log.event_type?.includes('error') || log.event_type?.includes('critical') ? '#991b1b' :
                              log.event_type?.includes('warning') ? '#92400e' : '#374151'
                          }}>
                            {log.event_type || log.trade_type || 'N/A'}
                          </span>
                        </td>
                        <td style={{
                          maxWidth: '400px',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap'
                        }}>
                          {log.message || log.symbol || 'N/A'}
                        </td>
                        <td>{log.created_at ? new Date(log.created_at).toLocaleString('ko-KR') : 'N/A'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Cache Management Tab */}
      {activeTab === 'cache' && (
        <div>
          {/* Message */}
          {message && (
            <div style={{
              padding: '1rem',
              marginBottom: '1rem',
              borderRadius: '0.5rem',
              background: message.type === 'success' ? '#dcfce7' : message.type === 'error' ? '#fee2e2' : '#dbeafe',
              color: message.type === 'success' ? '#166534' : message.type === 'error' ? '#991b1b' : '#1e40af',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}>
              {message.type === 'success' && <CheckCircle style={{ width: '1rem', height: '1rem' }} />}
              {message.type === 'error' && <AlertTriangle style={{ width: '1rem', height: '1rem' }} />}
              {message.text}
            </div>
          )}

          <div className="bots-section">
            <div className="bots-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2>
                <Database style={{ width: '1.25rem', height: '1.25rem', color: '#2563eb', marginRight: '0.5rem' }} />
                백테스트 데이터 캐시 현황
              </h2>
              <button onClick={fetchCacheInfo} className="admin-refresh-btn" disabled={cacheLoading}>
                <RefreshCw style={{ width: '1rem', height: '1rem' }} />
                새로고침
              </button>
            </div>

            {cacheLoading ? (
              <div style={{ textAlign: 'center', padding: '2rem' }}>
                <RefreshCw className="loading-spinner" style={{ width: '2rem', height: '2rem' }} />
                <p style={{ marginTop: '1rem', color: '#6b7280' }}>캐시 정보 로딩 중...</p>
              </div>
            ) : cacheInfo ? (
              <div>
                {/* Cache Stats */}
                <div className="stats-grid" style={{ marginBottom: '1.5rem' }}>
                  <div className="stat-card">
                    <div className="stat-card-header">
                      <HardDrive style={{ width: '1.5rem', height: '1.5rem', color: '#2563eb' }} />
                      <h3 className="stat-card-title">데이터 모드</h3>
                    </div>
                    <p className="stat-card-value" style={{
                      color: cacheInfo.cache_only ? '#22c55e' : '#f59e0b',
                      fontSize: '1.5rem'
                    }}>
                      {cacheInfo.cache_only ? '오프라인' : '온라인'}
                    </p>
                    <p className="stat-card-subtitle">
                      {cacheInfo.cache_only ? 'API 호출 없이 캐시만 사용' : 'API 호출 허용'}
                    </p>
                  </div>

                  <div className="stat-card">
                    <div className="stat-card-header">
                      <FileText style={{ width: '1.5rem', height: '1.5rem', color: '#22c55e' }} />
                      <h3 className="stat-card-title">캐시 파일</h3>
                    </div>
                    <p className="stat-card-value">{cacheInfo.total_files || 0}</p>
                    <p className="stat-card-subtitle">개의 데이터 파일</p>
                  </div>

                  <div className="stat-card">
                    <div className="stat-card-header">
                      <TrendingUp style={{ width: '1.5rem', height: '1.5rem', color: '#8b5cf6' }} />
                      <h3 className="stat-card-title">사용 가능 심볼</h3>
                    </div>
                    <p className="stat-card-value">
                      {[...new Set((cacheInfo.available_data || []).map(d => d.symbol))].length}
                    </p>
                    <p className="stat-card-subtitle">개의 거래쌍</p>
                  </div>
                </div>

                {/* Cache Data Table */}
                <div style={{
                  background: 'white',
                  borderRadius: '0.5rem',
                  padding: '1rem',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
                }}>
                  <h3 style={{ marginBottom: '1rem', fontSize: '1rem', fontWeight: '600' }}>
                    📊 캐시된 데이터 상세
                  </h3>

                  {(cacheInfo.available_data && cacheInfo.available_data.length > 0) ? (
                    <div style={{ overflowX: 'auto' }}>
                      <table className="logs-table">
                        <thead>
                          <tr>
                            <th>심볼</th>
                            <th>타임프레임</th>
                            <th>캔들 수</th>
                            <th>시작일</th>
                            <th>종료일</th>
                            <th>파일 크기</th>
                            <th>최종 업데이트</th>
                          </tr>
                        </thead>
                        <tbody>
                          {cacheInfo.available_data.map((data, idx) => (
                            <tr key={idx}>
                              <td>
                                <span style={{
                                  padding: '0.25rem 0.75rem',
                                  borderRadius: '9999px',
                                  fontSize: '0.875rem',
                                  fontWeight: '500',
                                  background: '#dbeafe',
                                  color: '#1e40af'
                                }}>
                                  {data.symbol}
                                </span>
                              </td>
                              <td>
                                <span style={{
                                  padding: '0.25rem 0.5rem',
                                  borderRadius: '0.25rem',
                                  fontSize: '0.75rem',
                                  background: '#f3f4f6',
                                  color: '#374151'
                                }}>
                                  {data.timeframe}
                                </span>
                              </td>
                              <td style={{ fontWeight: '500' }}>
                                {data.candle_count?.toLocaleString() || 0}
                              </td>
                              <td>{data.start_date || '-'}</td>
                              <td>{data.end_date || '-'}</td>
                              <td>{data.size_mb ? `${data.size_mb} MB` : '-'}</td>
                              <td>
                                {data.updated_at
                                  ? new Date(data.updated_at).toLocaleDateString('ko-KR')
                                  : '-'
                                }
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
                      <Database style={{ width: '3rem', height: '3rem', marginBottom: '1rem', opacity: 0.5 }} />
                      <p>캐시된 데이터가 없습니다</p>
                      <p style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>
                        데이터를 다운로드하려면 터미널에서 실행하세요:
                      </p>
                      <code style={{
                        display: 'block',
                        background: '#1f2937',
                        color: '#10b981',
                        padding: '1rem',
                        borderRadius: '0.5rem',
                        marginTop: '1rem',
                        fontSize: '0.875rem'
                      }}>
                        cd backend && python scripts/download_candle_data.py --all
                      </code>
                    </div>
                  )}
                </div>

                {/* Download Instructions */}
                <div style={{
                  marginTop: '1.5rem',
                  padding: '1rem',
                  background: '#fef3c7',
                  borderRadius: '0.5rem',
                  border: '1px solid #f59e0b'
                }}>
                  <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                    <Download style={{ width: '1rem', height: '1rem' }} />
                    데이터 다운로드 방법
                  </h4>
                  <p style={{ fontSize: '0.875rem', color: '#92400e', marginBottom: '0.5rem' }}>
                    새로운 캔들 데이터를 다운로드하려면 터미널에서 다음 명령어를 실행하세요:
                  </p>
                  <code style={{
                    display: 'block',
                    background: '#1f2937',
                    color: '#10b981',
                    padding: '0.75rem',
                    borderRadius: '0.375rem',
                    fontSize: '0.875rem'
                  }}>
                    cd backend && python scripts/download_candle_data.py --all --years 3
                  </code>
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
                <AlertTriangle style={{ width: '2rem', height: '2rem', marginBottom: '1rem', color: '#f59e0b' }} />
                <p>캐시 정보를 불러오지 못했습니다</p>
                <button
                  onClick={fetchCacheInfo}
                  style={{
                    marginTop: '1rem',
                    padding: '0.5rem 1rem',
                    background: '#2563eb',
                    color: 'white',
                    border: 'none',
                    borderRadius: '0.375rem',
                    cursor: 'pointer'
                  }}
                >
                  다시 시도
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* User Detail Modal */}
      {showUserDetailModal && selectedUserId && (
        <UserDetailModal
          userId={selectedUserId}
          onClose={() => {
            setShowUserDetailModal(false);
            setSelectedUserId(null);
          }}
        />
      )}
    </div>
  );
};

export default AdminDashboard;

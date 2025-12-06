import React, { useState, useEffect } from 'react';
import {
  X, User, Mail, Shield, Calendar, Activity, DollarSign, TrendingUp, Bot,
  Key, Lock, Trash2, AlertTriangle, RefreshCw, UserX, UserCheck, Crown
} from 'lucide-react';
import api from '../api/client';
import './UserDetailModal.css';

const UserDetailModal = ({ userId, onClose, onUserUpdated }) => {
  const [loading, setLoading] = useState(true);
  const [userDetail, setUserDetail] = useState(null);
  const [profitStats, setProfitStats] = useState(null);
  const [activeSubTab, setActiveSubTab] = useState('overview');
  const [actionLoading, setActionLoading] = useState(false);
  const [newPassword, setNewPassword] = useState(null);

  useEffect(() => {
    if (userId) {
      fetchUserDetail();
      fetchProfitStats();
    }
  }, [userId]);

  const fetchUserDetail = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/admin/users/${userId}/detail`);
      setUserDetail(response.data);
    } catch (error) {
      console.error('Failed to fetch user detail:', error);
      alert('사용자 상세 정보 조회 실패');
    } finally {
      setLoading(false);
    }
  };

  const fetchProfitStats = async () => {
    try {
      const response = await api.get(`/admin/users/${userId}/profit-stats`);
      setProfitStats(response.data);
    } catch (error) {
      console.error('Failed to fetch profit stats:', error);
    }
  };

  // 비밀번호 재설정
  const handleResetPassword = async () => {
    if (!window.confirm(`${userDetail.email} 사용자의 비밀번호를 초기화하시겠습니까?`)) return;

    try {
      setActionLoading(true);
      const response = await api.post(`/admin/users/${userId}/reset-password`);
      setNewPassword(response.data.new_password);
      alert('비밀번호가 초기화되었습니다. 새 비밀번호를 확인하세요.');
    } catch (error) {
      alert(error.response?.data?.detail || '비밀번호 초기화 실패');
    } finally {
      setActionLoading(false);
    }
  };

  // 계정 정지/활성화
  const handleToggleSuspend = async () => {
    const action = userDetail.is_active ? 'suspend' : 'activate';
    const actionText = userDetail.is_active ? '정지' : '활성화';

    if (!window.confirm(`${userDetail.email} 사용자를 ${actionText}하시겠습니까?`)) return;

    try {
      setActionLoading(true);
      await api.post(`/admin/users/${userId}/${action}`);
      alert(`계정이 ${actionText}되었습니다.`);
      fetchUserDetail();
      if (onUserUpdated) onUserUpdated();
    } catch (error) {
      alert(error.response?.data?.detail || `${actionText} 실패`);
    } finally {
      setActionLoading(false);
    }
  };

  // 역할 변경
  const handleChangeRole = async (newRole) => {
    if (!window.confirm(`${userDetail.email} 사용자를 ${newRole === 'admin' ? '관리자' : '일반 사용자'}로 변경하시겠습니까?`)) return;

    try {
      setActionLoading(true);
      await api.put(`/admin/users/${userId}/role?role=${newRole}`);
      alert('역할이 변경되었습니다.');
      fetchUserDetail();
      if (onUserUpdated) onUserUpdated();
    } catch (error) {
      alert(error.response?.data?.detail || '역할 변경 실패');
    } finally {
      setActionLoading(false);
    }
  };

  // API 키 삭제
  const handleDeleteApiKeys = async () => {
    if (!window.confirm(`${userDetail.email} 사용자의 모든 API 키를 삭제하시겠습니까?\n\n⚠️ 이 작업은 되돌릴 수 없으며, 봇도 정지됩니다.`)) return;

    try {
      setActionLoading(true);
      await api.delete(`/admin/users/${userId}/api-keys/all`);
      alert('API 키가 삭제되었습니다.');
      fetchUserDetail();
    } catch (error) {
      alert(error.response?.data?.detail || 'API 키 삭제 실패');
    } finally {
      setActionLoading(false);
    }
  };

  // 강제 로그아웃
  const handleForceLogout = async () => {
    if (!window.confirm(`${userDetail.email} 사용자를 강제 로그아웃 하시겠습니까?`)) return;

    try {
      setActionLoading(true);
      await api.post(`/admin/users/${userId}/force-logout`);
      alert('강제 로그아웃 처리되었습니다.');
      fetchUserDetail();
    } catch (error) {
      alert(error.response?.data?.detail || '강제 로그아웃 실패');
    } finally {
      setActionLoading(false);
    }
  };

  if (!userId) return null;

  const renderStats = (stats, label) => (
    <div className="profit-period-card">
      <h5>{label}</h5>
      <div className="profit-stats-grid">
        <div className="profit-stat">
          <span className="label">총 손익</span>
          <span className={`value ${stats.total_pnl >= 0 ? 'text-green' : 'text-red'}`}>
            {stats.total_pnl >= 0 ? '+' : ''}${stats.total_pnl}
          </span>
        </div>
        <div className="profit-stat">
          <span className="label">거래 수</span>
          <span className="value">{stats.total_trades}건</span>
        </div>
        <div className="profit-stat">
          <span className="label">승률</span>
          <span className="value">{stats.win_rate}%</span>
        </div>
        <div className="profit-stat">
          <span className="label">프로핏 팩터</span>
          <span className="value">{stats.profit_factor}</span>
        </div>
        <div className="profit-stat">
          <span className="label">최대 수익</span>
          <span className="value text-green">${stats.max_profit}</span>
        </div>
        <div className="profit-stat">
          <span className="label">최대 손실</span>
          <span className="value text-red">${stats.max_loss}</span>
        </div>
      </div>
    </div>
  );

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content user-detail-modal large" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <h2>
            <User style={{ width: '1.5rem', height: '1.5rem', marginRight: '0.5rem' }} />
            사용자 상세 정보
          </h2>
          <button className="close-button" onClick={onClose}>
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        {loading ? (
          <div className="loading-container">
            <p>로딩 중...</p>
          </div>
        ) : !userDetail ? (
          <div className="error-container">
            <p>사용자 정보를 불러올 수 없습니다.</p>
          </div>
        ) : (
          <div className="modal-body">
            {/* User Basic Info */}
            <div className="user-basic-info">
              <div className="user-avatar">
                <User size={48} />
              </div>
              <div className="user-info">
                <h3>{userDetail.email}</h3>
                <div className="user-badges">
                  <span className={`badge ${userDetail.role === 'admin' ? 'badge-admin' : 'badge-user'}`}>
                    {userDetail.role === 'admin' ? <Crown size={14} /> : <Shield size={14} />}
                    {userDetail.role === 'admin' ? '관리자' : '일반 사용자'}
                  </span>
                  <span className={`badge ${userDetail.is_active ? 'badge-active' : 'badge-inactive'}`}>
                    <Activity size={14} />
                    {userDetail.is_active ? '활성' : '정지됨'}
                  </span>
                </div>
                <div className="user-meta">
                  <span>
                    <Calendar size={14} />
                    가입일: {new Date(userDetail.created_at).toLocaleDateString('ko-KR')}
                  </span>
                  {userDetail.suspended_at && (
                    <span className="text-red">
                      <Calendar size={14} />
                      정지일: {new Date(userDetail.suspended_at).toLocaleDateString('ko-KR')}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="quick-actions">
              <button
                className={`action-btn ${userDetail.is_active ? 'btn-danger' : 'btn-success'}`}
                onClick={handleToggleSuspend}
                disabled={actionLoading}
              >
                {userDetail.is_active ? <UserX size={16} /> : <UserCheck size={16} />}
                {userDetail.is_active ? '계정 정지' : '계정 활성화'}
              </button>
              <button
                className="action-btn btn-warning"
                onClick={handleResetPassword}
                disabled={actionLoading}
              >
                <Lock size={16} />
                비밀번호 초기화
              </button>
              <button
                className="action-btn btn-secondary"
                onClick={handleForceLogout}
                disabled={actionLoading}
              >
                <RefreshCw size={16} />
                강제 로그아웃
              </button>
              <button
                className="action-btn btn-danger"
                onClick={handleDeleteApiKeys}
                disabled={actionLoading || !userDetail.has_api_keys}
              >
                <Trash2 size={16} />
                API 키 삭제
              </button>
            </div>

            {/* New Password Display */}
            {newPassword && (
              <div className="new-password-alert">
                <AlertTriangle size={20} />
                <div>
                  <strong>새 비밀번호:</strong>
                  <code>{newPassword}</code>
                  <p>이 비밀번호를 사용자에게 안전하게 전달하세요. 다시 조회할 수 없습니다.</p>
                </div>
                <button onClick={() => {
                  navigator.clipboard.writeText(newPassword);
                  alert('클립보드에 복사되었습니다.');
                }}>복사</button>
              </div>
            )}

            {/* Sub Tabs */}
            <div className="sub-tabs">
              <button
                className={activeSubTab === 'overview' ? 'active' : ''}
                onClick={() => setActiveSubTab('overview')}
              >
                개요
              </button>
              <button
                className={activeSubTab === 'profit' ? 'active' : ''}
                onClick={() => setActiveSubTab('profit')}
              >
                수익 분석
              </button>
              <button
                className={activeSubTab === 'trades' ? 'active' : ''}
                onClick={() => setActiveSubTab('trades')}
              >
                거래 내역 ({userDetail.total_trades || 0})
              </button>
              <button
                className={activeSubTab === 'settings' ? 'active' : ''}
                onClick={() => setActiveSubTab('settings')}
              >
                관리 설정
              </button>
            </div>

            {/* Overview Tab */}
            {activeSubTab === 'overview' && (
              <div className="overview-section">
                <div className="stats-grid">
                  <div className="stat-card">
                    <div className="stat-icon" style={{ background: '#dbeafe', color: '#1e40af' }}>
                      <DollarSign size={24} />
                    </div>
                    <div className="stat-content">
                      <p className="stat-label">총 자산</p>
                      <p className="stat-value">${userDetail.total_balance?.toFixed(2) || '0.00'}</p>
                    </div>
                  </div>

                  <div className="stat-card">
                    <div className="stat-icon" style={{ background: userDetail.total_pnl >= 0 ? '#dcfce7' : '#fee2e2', color: userDetail.total_pnl >= 0 ? '#166534' : '#991b1b' }}>
                      <TrendingUp size={24} />
                    </div>
                    <div className="stat-content">
                      <p className="stat-label">총 손익</p>
                      <p className={`stat-value ${userDetail.total_pnl >= 0 ? 'text-green' : 'text-red'}`}>
                        {userDetail.total_pnl >= 0 ? '+' : ''}${userDetail.total_pnl?.toFixed(2) || '0.00'}
                      </p>
                    </div>
                  </div>

                  <div className="stat-card">
                    <div className="stat-icon" style={{ background: '#fef3c7', color: '#92400e' }}>
                      <Bot size={24} />
                    </div>
                    <div className="stat-content">
                      <p className="stat-label">실행 중인 봇</p>
                      <p className="stat-value">{userDetail.active_bots_count || 0}개</p>
                    </div>
                  </div>

                  <div className="stat-card">
                    <div className="stat-icon" style={{ background: '#e9d5ff', color: '#6b21a8' }}>
                      <Activity size={24} />
                    </div>
                    <div className="stat-content">
                      <p className="stat-label">총 거래 수</p>
                      <p className="stat-value">{userDetail.total_trades || 0}건</p>
                    </div>
                  </div>
                </div>

                {/* Trading Stats */}
                <div className="detail-section">
                  <h4>거래 통계</h4>
                  <div className="detail-grid">
                    <div className="detail-item">
                      <span className="detail-label">승률:</span>
                      <span className="detail-value">{userDetail.win_rate?.toFixed(1) || '0.0'}%</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">승리 거래:</span>
                      <span className="detail-value text-green">{userDetail.winning_trades || 0}건</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">패배 거래:</span>
                      <span className="detail-value text-red">{userDetail.losing_trades || 0}건</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">평균 손익:</span>
                      <span className={`detail-value ${userDetail.avg_pnl >= 0 ? 'text-green' : 'text-red'}`}>
                        ${userDetail.avg_pnl?.toFixed(2) || '0.00'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* API Key Info */}
                <div className="detail-section">
                  <h4>API 키 정보</h4>
                  <div className="detail-grid">
                    <div className="detail-item">
                      <span className="detail-label">API 키 상태:</span>
                      <span className={`detail-value ${userDetail.has_api_keys ? 'text-green' : 'text-red'}`}>
                        {userDetail.has_api_keys ? '✓ 등록됨' : '✗ 미등록'}
                      </span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">거래소:</span>
                      <span className="detail-value">Bitget</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Profit Analysis Tab */}
            {activeSubTab === 'profit' && (
              <div className="profit-section">
                {profitStats ? (
                  <>
                    <div className="profit-periods">
                      {renderStats(profitStats.today, '오늘')}
                      {renderStats(profitStats.week, '최근 7일')}
                      {renderStats(profitStats.month, '최근 30일')}
                      {renderStats(profitStats.all_time, '전체 기간')}
                    </div>

                    {/* Daily PnL Table */}
                    <div className="detail-section">
                      <h4>일별 손익 (최근 7일)</h4>
                      <div className="table-container">
                        <table className="detail-table">
                          <thead>
                            <tr>
                              <th>날짜</th>
                              <th>거래 수</th>
                              <th>손익</th>
                            </tr>
                          </thead>
                          <tbody>
                            {profitStats.daily_pnl?.map((day, idx) => (
                              <tr key={idx}>
                                <td>{day.date}</td>
                                <td>{day.trades}건</td>
                                <td className={day.pnl >= 0 ? 'text-green' : 'text-red'}>
                                  {day.pnl >= 0 ? '+' : ''}${day.pnl}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </>
                ) : (
                  <p className="empty-state">수익 통계를 불러오는 중...</p>
                )}
              </div>
            )}

            {/* Trades Tab */}
            {activeSubTab === 'trades' && (
              <div className="trades-section">
                {!userDetail.recent_trades || userDetail.recent_trades.length === 0 ? (
                  <p className="empty-state">최근 거래 내역이 없습니다.</p>
                ) : (
                  <div className="table-container">
                    <table className="detail-table">
                      <thead>
                        <tr>
                          <th>시간</th>
                          <th>심볼</th>
                          <th>방향</th>
                          <th>진입가</th>
                          <th>청산가</th>
                          <th>수량</th>
                          <th>P&L</th>
                        </tr>
                      </thead>
                      <tbody>
                        {userDetail.recent_trades.map((trade, idx) => (
                          <tr key={idx}>
                            <td>{new Date(trade.created_at).toLocaleString('ko-KR')}</td>
                            <td>{trade.symbol}</td>
                            <td>
                              <span className={`badge ${trade.side === 'buy' ? 'badge-buy' : 'badge-sell'}`}>
                                {trade.side.toUpperCase()}
                              </span>
                            </td>
                            <td>${trade.entry_price?.toFixed(2)}</td>
                            <td>${trade.exit_price?.toFixed(2)}</td>
                            <td>{trade.qty}</td>
                            <td className={trade.pnl >= 0 ? 'text-green' : 'text-red'}>
                              {trade.pnl >= 0 ? '+' : ''}${trade.pnl?.toFixed(2)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {/* Settings Tab */}
            {activeSubTab === 'settings' && (
              <div className="settings-section">
                {/* Role Management */}
                <div className="detail-section">
                  <h4>역할 관리</h4>
                  <div className="role-buttons">
                    <button
                      className={`role-btn ${userDetail.role === 'user' ? 'active' : ''}`}
                      onClick={() => handleChangeRole('user')}
                      disabled={actionLoading || userDetail.role === 'user'}
                    >
                      <User size={16} />
                      일반 사용자
                    </button>
                    <button
                      className={`role-btn admin ${userDetail.role === 'admin' ? 'active' : ''}`}
                      onClick={() => handleChangeRole('admin')}
                      disabled={actionLoading || userDetail.role === 'admin'}
                    >
                      <Crown size={16} />
                      관리자
                    </button>
                  </div>
                  <p className="hint-text">⚠️ 관리자 권한은 신중하게 부여하세요.</p>
                </div>

                {/* Account Actions */}
                <div className="detail-section">
                  <h4>계정 관리</h4>
                  <div className="action-list">
                    <div className="action-item">
                      <div>
                        <strong>비밀번호 초기화</strong>
                        <p>새로운 임시 비밀번호를 생성합니다.</p>
                      </div>
                      <button className="btn-warning" onClick={handleResetPassword} disabled={actionLoading}>
                        <Lock size={14} /> 초기화
                      </button>
                    </div>
                    <div className="action-item">
                      <div>
                        <strong>강제 로그아웃</strong>
                        <p>현재 세션을 종료하고 봇을 정지합니다.</p>
                      </div>
                      <button className="btn-secondary" onClick={handleForceLogout} disabled={actionLoading}>
                        <RefreshCw size={14} /> 로그아웃
                      </button>
                    </div>
                    <div className="action-item">
                      <div>
                        <strong>계정 {userDetail.is_active ? '정지' : '활성화'}</strong>
                        <p>{userDetail.is_active ? '로그인을 차단하고 봇을 정지합니다.' : '계정을 다시 활성화합니다.'}</p>
                      </div>
                      <button
                        className={userDetail.is_active ? 'btn-danger' : 'btn-success'}
                        onClick={handleToggleSuspend}
                        disabled={actionLoading}
                      >
                        {userDetail.is_active ? <UserX size={14} /> : <UserCheck size={14} />}
                        {userDetail.is_active ? '정지' : '활성화'}
                      </button>
                    </div>
                  </div>
                </div>

                {/* API Key Management */}
                <div className="detail-section danger-zone">
                  <h4>⚠️ 위험 영역</h4>
                  <div className="action-item">
                    <div>
                      <strong>API 키 전체 삭제</strong>
                      <p>모든 API 키를 삭제하고 봇을 정지합니다. 되돌릴 수 없습니다.</p>
                    </div>
                    <button
                      className="btn-danger"
                      onClick={handleDeleteApiKeys}
                      disabled={actionLoading || !userDetail.has_api_keys}
                    >
                      <Trash2 size={14} /> 삭제
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose}>
            닫기
          </button>
        </div>
      </div>
    </div>
  );
};

export default UserDetailModal;

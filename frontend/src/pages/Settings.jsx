import { useState, useEffect } from 'react';
import { accountAPI } from '../api/account';
import { authAPI } from '../api/auth';
import apiClient from '../api/client';
import { useAuth } from '../context/AuthContext';
import {
  KeyOutlined,
  MessageOutlined,
  LockOutlined,
  SafetyCertificateOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SaveOutlined,
  ApiOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  SendOutlined
} from '@ant-design/icons';
import TwoFactorSettings from '../components/settings/TwoFactorSettings';

// 지원 거래소 목록 (1계정 = 1거래소 정책)
const SUPPORTED_EXCHANGES = [
  { value: 'bitget', label: 'Bitget', passphraseRequired: true, logo: '🟢' },
  { value: 'binance', label: 'Binance', passphraseRequired: false, logo: '🟡' },
  { value: 'okx', label: 'OKX', passphraseRequired: true, logo: '⚫' },
  { value: 'bybit', label: 'Bybit', passphraseRequired: false, logo: '🟠' },
  { value: 'gateio', label: 'Gate.io', passphraseRequired: false, logo: '🔵' },
];

export default function Settings() {
  const { user } = useAuth();

  // 화면 크기 감지
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // API Keys State
  const [selectedExchange, setSelectedExchange] = useState('bitget'); // 선택된 거래소
  const [apiKey, setApiKey] = useState('');
  const [secretKey, setSecretKey] = useState('');
  const [passphrase, setPassphrase] = useState('');
  const [showKeys, setShowKeys] = useState(false);
  const [keysLoading, setKeysLoading] = useState(false);
  const [testingConnection, setTestingConnection] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState(null);
  const [savedKeyInfo, setSavedKeyInfo] = useState(null); // 저장된 API 키 정보 (거래소 포함)

  // Password State
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordLoading, setPasswordLoading] = useState(false);

  // Risk Management State
  const [dailyLossLimit, setDailyLossLimit] = useState('');
  const [maxLeverage, setMaxLeverage] = useState('');
  const [maxPositions, setMaxPositions] = useState('');
  const [riskLoading, setRiskLoading] = useState(false);

  // Telegram State
  const [telegramBotToken, setTelegramBotToken] = useState('');
  const [telegramChatId, setTelegramChatId] = useState('');
  const [telegramLoading, setTelegramLoading] = useState(false);
  const [telegramStatus, setTelegramStatus] = useState(null);
  const [showTelegramToken, setShowTelegramToken] = useState(false);
  const [savedTelegramInfo, setSavedTelegramInfo] = useState(null); // 저장된 텔레그램 정보
  const [deleteTelegramLoading, setDeleteTelegramLoading] = useState(false);

  // Messages
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [activeTab, setActiveTab] = useState('api'); // api, password, risk, telegram, info

  // Load saved keys status on mount
  useEffect(() => {
    checkSavedKeys();
    loadRiskSettings();
    checkTelegramStatus();
  }, []);

  // 텔레그램 상태 확인 (인증된 요청)
  const checkTelegramStatus = async () => {
    try {
      const response = await apiClient.get('/telegram/status');
      const data = response.data;
      setTelegramStatus(data);

      // 저장된 텔레그램 정보가 있으면 표시
      if (data.enabled && data.masked_bot_token) {
        setSavedTelegramInfo({
          maskedBotToken: data.masked_bot_token,
          maskedChatId: data.masked_chat_id,
          notifyTrades: data.config?.notify_trades ?? true,
          notifySystem: data.config?.notify_system ?? true,
          notifyErrors: data.config?.notify_errors ?? true,
        });
      } else {
        setSavedTelegramInfo(null);
      }
    } catch (err) {
      console.log('[Settings] Telegram status check failed:', err);
      setSavedTelegramInfo(null);
    }
  };

  // 텔레그램 설정 저장 (인증된 요청)
  const handleSaveTelegram = async (e) => {
    e.preventDefault();

    if (!telegramBotToken || !telegramChatId) {
      setError('Bot Token과 Chat ID를 모두 입력해주세요.');
      return;
    }

    setTelegramLoading(true);
    setError('');
    setSuccess('');

    try {
      // 인증된 API를 통해 텔레그램 설정 저장
      const response = await apiClient.post('/telegram/settings', {
        bot_token: telegramBotToken,
        chat_id: telegramChatId,
      });

      const data = response.data;

      if (data.success) {
        setSuccess('✅ 텔레그램 설정이 저장되었습니다!');
        console.log('[Settings] Telegram settings saved');

        // 상태 다시 확인
        await checkTelegramStatus();

        // 입력 필드 초기화
        setTelegramBotToken('');
        setTelegramChatId('');
      } else {
        setError(data.message || '텔레그램 설정 저장에 실패했습니다.');
      }
    } catch (err) {
      console.error('[Settings] Telegram save error:', err);
      const errorMessage = err.response?.data?.detail || err.response?.data?.message || '텔레그램 설정 저장에 실패했습니다.';
      setError(errorMessage);
    } finally {
      setTelegramLoading(false);
    }
  };

  // 텔레그램 설정 삭제
  const handleDeleteTelegram = async () => {
    if (!window.confirm('텔레그램 설정을 삭제하시겠습니까? 더 이상 알림을 받을 수 없습니다.')) {
      return;
    }

    setDeleteTelegramLoading(true);
    setError('');
    setSuccess('');

    try {
      const response = await apiClient.delete('/telegram/settings');
      const data = response.data;

      if (data.success) {
        setSuccess('✅ 텔레그램 설정이 삭제되었습니다.');
        setSavedTelegramInfo(null);
        setTelegramStatus(null);
        console.log('[Settings] Telegram settings deleted');
      }
    } catch (err) {
      console.error('[Settings] Telegram delete error:', err);
      setError('텔레그램 설정 삭제에 실패했습니다.');
    } finally {
      setDeleteTelegramLoading(false);
    }
  };

  // 텔레그램 테스트 메시지 전송 (인증된 요청)
  const handleTestTelegram = async () => {
    setTelegramLoading(true);
    setError('');
    setSuccess('');

    try {
      const response = await apiClient.post('/telegram/test');
      const data = response.data;

      if (data.success) {
        setSuccess('✅ 테스트 메시지가 전송되었습니다! 텔레그램을 확인하세요.');
      } else {
        setError(data.message || '테스트 메시지 전송에 실패했습니다.');
      }
    } catch (err) {
      const errorMessage = err.response?.data?.detail || '테스트 메시지 전송에 실패했습니다.';
      setError(errorMessage);
    } finally {
      setTelegramLoading(false);
    }
  };

  const loadRiskSettings = async () => {
    try {
      const data = await accountAPI.getRiskSettings();
      setDailyLossLimit(data.daily_loss_limit?.toString() || '500');
      setMaxLeverage(data.max_leverage?.toString() || '10');
      setMaxPositions(data.max_positions?.toString() || '5');
      console.log('[Settings] ✅ Risk settings loaded:', data);
    } catch (err) {
      console.error('[Settings] Failed to load risk settings:', err);
      // Fallback to defaults on error
      setDailyLossLimit('500');
      setMaxLeverage('10');
      setMaxPositions('5');
    }
  };


















  const checkSavedKeys = async () => {
    try {
      const data = await accountAPI.getMyKeys();
      if (data.api_key) {
        // API 키 정보 마스킹 처리
        const maskedApiKey = data.api_key.substring(0, 8) + '...' + data.api_key.substring(data.api_key.length - 4);
        const maskedSecretKey = data.secret_key.substring(0, 4) + '...' + data.secret_key.substring(data.secret_key.length - 4);

        // 거래소 정보 추출 및 라벨 찾기
        const exchangeValue = data.exchange || 'bitget';
        const exchangeInfo = SUPPORTED_EXCHANGES.find(ex => ex.value === exchangeValue);
        const exchangeLabel = exchangeInfo ? exchangeInfo.label : exchangeValue.toUpperCase();
        const exchangeLogo = exchangeInfo ? exchangeInfo.logo : '🔗';

        setSavedKeyInfo({
          apiKey: maskedApiKey,
          secretKey: maskedSecretKey,
          hasPassphrase: !!data.passphrase,
          exchange: exchangeValue,
          exchangeLabel: exchangeLabel,
          exchangeLogo: exchangeLogo,
        });

        // 저장된 거래소로 선택 상태 업데이트
        setSelectedExchange(exchangeValue);
        setConnectionStatus({ type: 'info', message: `${exchangeLabel} API 키가 등록되어 있습니다.` });
      }
    } catch (err) {
      // No keys saved yet
      setConnectionStatus(null);
      setSavedKeyInfo(null);
    }
  };

  const handleSaveKeys = async (e) => {
    e.preventDefault();

    if (!apiKey || !secretKey) {
      setError('API Key와 Secret Key는 필수입니다.');
      return;
    }

    // Passphrase 필수 거래소 검증
    const exchangeInfo = SUPPORTED_EXCHANGES.find(ex => ex.value === selectedExchange);
    if (exchangeInfo?.passphraseRequired && !passphrase) {
      setError(`${exchangeInfo.label} 거래소는 Passphrase가 필수입니다.`);
      return;
    }

    setKeysLoading(true);
    setError('');
    setSuccess('');

    try {
      const exchangeLabel = exchangeInfo?.label || selectedExchange.toUpperCase();
      console.log(`[Settings] Saving API keys for ${exchangeLabel}...`);
      const result = await accountAPI.saveApiKeys(apiKey, secretKey, passphrase, selectedExchange);
      console.log('[Settings] API keys saved successfully:', result);

      setSuccess(`✅ ${exchangeLabel} API 키가 성공적으로 저장되었습니다!`);
      setConnectionStatus({ type: 'success', message: `${exchangeLabel} API 키가 저장되었습니다.` });

      // 저장 후 키 정보 업데이트
      await checkSavedKeys();

      // 입력 필드 초기화
      setApiKey('');
      setSecretKey('');
      setPassphrase('');
      setShowKeys(false);
    } catch (err) {
      console.error('[Settings] Error saving API keys:', err);
      const errorMessage = err.response?.data?.detail || 'API 키 저장에 실패했습니다.';
      setError(errorMessage);
    } finally {
      setKeysLoading(false);
    }
  };

  const handleTestConnection = async () => {
    setTestingConnection(true);
    setError('');
    setSuccess('');

    try {
      // 범용 잔고 조회 API로 연결 테스트 (모든 거래소 지원)
      const balanceData = await accountAPI.getBalance();
      const exchangeName = balanceData.exchange || 'Unknown';
      const exchangeInfo = SUPPORTED_EXCHANGES.find(ex => ex.value === exchangeName);
      const exchangeLabel = exchangeInfo?.label || exchangeName.toUpperCase();

      // 선물 잔고 추출
      const futuresTotal = parseFloat(balanceData.futures?.total || 0);

      setConnectionStatus({
        type: 'success',
        message: `${exchangeLabel} 연결 성공! 잔고: ${futuresTotal.toFixed(2)} USDT`
      });
      setSuccess(`✅ ${exchangeLabel} API 연결 테스트 성공!`);
    } catch (err) {
      console.error('[Settings] Connection test failed:', err);

      // 구체적인 에러 메시지 처리
      let errorMessage = 'API 연결 실패';
      let statusMessage = 'API 연결 실패. 키를 확인하세요.';

      if (err.response) {
        const status = err.response.status;
        const detail = err.response.data?.detail || '';

        if (status === 404) {
          errorMessage = 'API 키가 등록되지 않았습니다. 먼저 API 키를 저장해주세요.';
          statusMessage = 'API 키 미등록';
        } else if (status === 401) {
          errorMessage = 'API 키가 유효하지 않습니다. 키 정보를 확인해주세요.';
          statusMessage = 'API 키 인증 실패';
        } else if (status === 400) {
          errorMessage = 'API 인증 정보가 불완전합니다. 모든 필드를 입력해주세요.';
          statusMessage = 'API 정보 불완전';
        } else if (status === 500) {
          if (detail.includes('복호화')) {
            errorMessage = 'API 키 복호화 실패. 키를 다시 등록해주세요.';
          } else if (detail.includes('not configured') || detail.includes('설정되지')) {
            errorMessage = 'API 키가 설정되지 않았습니다. Settings에서 API 키를 먼저 등록하세요.';
          } else {
            errorMessage = `서버 오류: ${detail || '잠시 후 다시 시도해주세요.'}`;
          }
          statusMessage = 'API 연결 오류';
        } else {
          errorMessage = detail || `연결 실패 (${status})`;
        }
      } else if (err.message) {
        errorMessage = err.message;
      }

      setConnectionStatus({
        type: 'error',
        message: statusMessage
      });
      setError('❌ ' + errorMessage);
    } finally {
      setTestingConnection(false);
    }
  };

  const handleViewKeys = async () => {
    setKeysLoading(true);
    setError('');

    try {
      const data = await accountAPI.getMyKeys();
      setApiKey(data.api_key);
      setSecretKey(data.secret_key);
      setPassphrase(data.passphrase || '');
      setShowKeys(true);
      setSuccess('🔍 API 키를 불러왔습니다.');
    } catch (err) {
      if (err.response?.status === 404) {
        setError('등록된 API 키가 없습니다.');
      } else if (err.response?.status === 429) {
        setError('API 키 조회 제한을 초과했습니다. 시간당 3회만 조회 가능합니다.');
      } else {
        setError(err.response?.data?.detail || 'API 키 조회에 실패했습니다.');
      }
    } finally {
      setKeysLoading(false);
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();

    if (!currentPassword || !newPassword || !confirmPassword) {
      setError('모든 비밀번호 필드를 입력해주세요.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('새 비밀번호가 일치하지 않습니다.');
      return;
    }

    if (newPassword.length < 8) {
      setError('새 비밀번호는 최소 8자 이상이어야 합니다.');
      return;
    }

    setPasswordLoading(true);
    setError('');
    setSuccess('');

    try {
      console.log('[Settings] Changing password...');
      await authAPI.changePassword(currentPassword, newPassword);

      setSuccess('✅ 비밀번호가 성공적으로 변경되었습니다!');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      console.log('[Settings] ✅ Password changed successfully');
    } catch (err) {
      console.error('[Settings] Failed to change password:', err);
      setError(err.response?.data?.detail || '비밀번호 변경에 실패했습니다.');
    } finally {
      setPasswordLoading(false);
    }
  };

  const handleSaveRiskSettings = async (e) => {
    e.preventDefault();

    if (!dailyLossLimit || !maxLeverage || !maxPositions) {
      setError('모든 리스크 한도 값을 입력해주세요.');
      return;
    }

    const dailyLoss = parseFloat(dailyLossLimit);
    const leverage = parseInt(maxLeverage);
    const positions = parseInt(maxPositions);

    if (dailyLoss <= 0) {
      setError('일일 손실 한도는 0보다 커야 합니다.');
      return;
    }

    if (leverage <= 0 || leverage > 100) {
      setError('레버리지는 1~100 사이의 값이어야 합니다.');
      return;
    }

    if (positions <= 0 || positions > 50) {
      setError('최대 포지션 개수는 1~50 사이의 값이어야 합니다.');
      return;
    }

    setRiskLoading(true);
    setError('');
    setSuccess('');

    try {
      console.log('[Settings] Saving risk settings:', {
        daily_loss_limit: dailyLoss,
        max_leverage: leverage,
        max_positions: positions
      });

      await accountAPI.saveRiskSettings(dailyLoss, leverage, positions);

      setSuccess('✅ 리스크 한도 설정이 저장되었습니다!');
      console.log('[Settings] ✅ Risk settings saved successfully');
    } catch (err) {
      console.error('[Settings] Error saving risk settings:', err);
      setError(err.response?.data?.detail || '리스크 설정 저장에 실패했습니다.');
    } finally {
      setRiskLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 1400, margin: '0 auto' }}>
      {/* Header - 표준 스펙 적용 */}
      <div style={{ marginBottom: isMobile ? 12 : 24 }}>
        <h1 style={{
          fontSize: isMobile ? 20 : 28,
          fontWeight: 600,
          margin: 0,
          marginBottom: isMobile ? 4 : 8,
          color: '#1d1d1f',
          display: 'flex',
          alignItems: 'center',
          gap: 8
        }}>
          <SafetyCertificateOutlined />
          설정
        </h1>
        {!isMobile && (
          <p style={{ color: '#86868b', margin: 0, fontSize: 14 }}>
            계정: {user?.email}
          </p>
        )}
      </div>

      {/* Messages */}
      {error && (
        <div style={{
          background: '#fff2f0',
          color: '#ff4d4f',
          padding: '1rem',
          borderRadius: '12px',
          marginBottom: '1rem',
          border: '1px solid #ffccc7',
          display: 'flex',
          alignItems: 'center',
          gap: 8
        }}>
          <CloseCircleOutlined />
          {error}
        </div>
      )}

      {success && (
        <div style={{
          background: '#f6ffed',
          color: '#52c41a',
          padding: '1rem',
          borderRadius: '12px',
          marginBottom: '1rem',
          border: '1px solid #b7eb8f',
          display: 'flex',
          alignItems: 'center',
          gap: 8
        }}>
          <CheckCircleOutlined />
          {success}
        </div>
      )}

      {/* Tabs */}
      <div style={{
        display: 'flex',
        gap: isMobile ? '0.5rem' : '1rem',
        marginBottom: isMobile ? '1rem' : '1.5rem',
        borderBottom: '1px solid #e5e5e5',
        overflowX: 'auto',
        WebkitOverflowScrolling: 'touch',
        whiteSpace: 'nowrap',
        paddingBottom: 1
      }}>
        {[
          { id: 'api', label: 'API 키', icon: <KeyOutlined /> },
          { id: 'telegram', label: '텔레그램', icon: <MessageOutlined /> },
          { id: 'password', label: '비밀번호', icon: <LockOutlined /> },
          { id: '2fa', label: '2단계 인증', icon: <SafetyCertificateOutlined /> },
          { id: 'risk', label: '리스크 관리', icon: <WarningOutlined /> },
          { id: 'info', label: '도움말', icon: <InfoCircleOutlined /> }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: isMobile ? '0.75rem 0.5rem' : '1rem 0',
              marginRight: isMobile ? '0.5rem' : '1.5rem',
              background: 'transparent',
              border: 'none',
              borderBottom: activeTab === tab.id ? '2px solid #1d1d1f' : '2px solid transparent',
              cursor: 'pointer',
              fontSize: isMobile ? '0.9rem' : '1rem',
              fontWeight: activeTab === tab.id ? '600' : '400',
              color: activeTab === tab.id ? '#1d1d1f' : '#86868b',
              transition: 'all 0.2s',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              flexShrink: 0
            }}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* API Keys Tab */}
      {activeTab === 'api' && (
        <div style={{
          background: '#ffffff',
          padding: '2rem',
          borderRadius: '16px',
          border: '1px solid #f5f5f7',
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '2rem',
            paddingBottom: '1rem',
            borderBottom: '1px solid #f5f5f7'
          }}>
            <div>
              <h2 style={{ fontSize: '1.25rem', fontWeight: '600', margin: 0, marginBottom: '0.5rem', color: '#1d1d1f' }}>
                거래소 API 키 설정
              </h2>
              <p style={{ color: '#86868b', margin: 0, fontSize: '0.9rem' }}>
                거래소를 선택하고 API 키를 등록하여 자동매매를 시작하세요 (1계정 = 1거래소)
              </p>
            </div>
            {connectionStatus && (
              <div style={{
                padding: '0.5rem 1rem',
                background: connectionStatus.type === 'success' ? '#f6ffed' :
                  connectionStatus.type === 'error' ? '#fff2f0' : '#f0f5ff',
                color: connectionStatus.type === 'success' ? '#52c41a' :
                  connectionStatus.type === 'error' ? '#ff4d4f' : '#2f54eb',
                borderRadius: '8px',
                fontSize: '0.85rem',
                fontWeight: '500',
                display: 'flex',
                alignItems: 'center',
                gap: 6
              }}>
                {connectionStatus.type === 'success' ? <CheckCircleOutlined /> :
                  connectionStatus.type === 'error' ? <CloseCircleOutlined /> : <InfoCircleOutlined />}
                {connectionStatus.message}
              </div>
            )}
          </div>

          {/* 저장된 API 키 정보 표시 */}
          {savedKeyInfo && (
            <div style={{
              background: '#f0f5ff',
              padding: '1rem 1.5rem',
              borderRadius: '12px',
              marginBottom: '2rem',
              border: '1px solid #d6e4ff'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: '0.75rem' }}>
                <CheckCircleOutlined style={{ color: '#52c41a' }} />
                <span style={{ fontWeight: '600', color: '#1d1d1f' }}>
                  현재 등록된 API 키 - {savedKeyInfo.exchangeLogo} {savedKeyInfo.exchangeLabel}
                </span>
              </div>
              <div style={{
                fontFamily: 'SF Mono, Monaco, monospace',
                fontSize: '0.85rem',
                color: '#434343',
                display: 'grid',
                gap: '0.5rem'
              }}>
                <div>
                  <span style={{ color: '#86868b', minWidth: '80px', display: 'inline-block' }}>거래소:</span>
                  <span style={{ fontWeight: '600', color: '#1890ff' }}>{savedKeyInfo.exchangeLogo} {savedKeyInfo.exchangeLabel}</span>
                </div>
                <div>
                  <span style={{ color: '#86868b', minWidth: '80px', display: 'inline-block' }}>API Key:</span>
                  <span style={{ fontWeight: '500' }}>{savedKeyInfo.apiKey}</span>
                </div>
                <div>
                  <span style={{ color: '#86868b', minWidth: '80px', display: 'inline-block' }}>Secret Key:</span>
                  <span style={{ fontWeight: '500' }}>{savedKeyInfo.secretKey}</span>
                </div>
                <div>
                  <span style={{ color: '#86868b', minWidth: '80px', display: 'inline-block' }}>Passphrase:</span>
                  <span style={{ fontWeight: '500' }}>{savedKeyInfo.hasPassphrase ? '설정됨 ✓' : '미설정'}</span>
                </div>
              </div>
            </div>
          )}

          <form onSubmit={handleSaveKeys}>
            {/* 거래소 선택 드롭다운 */}
            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{
                display: 'block',
                marginBottom: '0.5rem',
                fontWeight: '500',
                fontSize: '0.9rem',
                color: '#1d1d1f'
              }}>
                거래소 선택 <span style={{ color: '#ff4d4f' }}>*</span>
              </label>
              <select
                value={selectedExchange}
                onChange={(e) => setSelectedExchange(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.875rem',
                  border: '1px solid #d2d2d7',
                  borderRadius: '8px',
                  fontSize: '0.95rem',
                  backgroundColor: '#ffffff',
                  cursor: 'pointer',
                  outline: 'none',
                  appearance: 'none',
                  backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23666' d='M6 8L1 3h10z'/%3E%3C/svg%3E")`,
                  backgroundRepeat: 'no-repeat',
                  backgroundPosition: 'right 12px center',
                }}
              >
                {SUPPORTED_EXCHANGES.map(exchange => (
                  <option key={exchange.value} value={exchange.value}>
                    {exchange.logo} {exchange.label} {exchange.passphraseRequired ? '(Passphrase 필수)' : ''}
                  </option>
                ))}
              </select>
              <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: '#86868b' }}>
                {savedKeyInfo && savedKeyInfo.exchange !== selectedExchange && (
                  <span style={{ color: '#faad14' }}>
                    ⚠️ 거래소 변경 시 기존 API 키가 새 거래소 키로 덮어씌워집니다.
                  </span>
                )}
              </div>
            </div>

            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{
                display: 'block',
                marginBottom: '0.5rem',
                fontWeight: '500',
                fontSize: '0.9rem',
                color: '#1d1d1f'
              }}>
                API Key <span style={{ color: '#ff4d4f' }}>*</span>
              </label>
              <input
                type={showKeys ? 'text' : 'password'}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="API Key를 입력하세요"
                autoComplete="off"
                style={{
                  width: '100%',
                  padding: '0.875rem',
                  border: '1px solid #d2d2d7',
                  borderRadius: '8px',
                  fontSize: '0.95rem',
                  fontFamily: 'SF Mono, Monaco, monospace',
                  transition: 'all 0.2s',
                  outline: 'none'
                }}
                onFocus={(e) => e.target.style.borderColor = '#0071e3'}
                onBlur={(e) => e.target.style.borderColor = '#d2d2d7'}
                required
              />
            </div>

            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{
                display: 'block',
                marginBottom: '0.5rem',
                fontWeight: '500',
                fontSize: '0.9rem',
                color: '#1d1d1f'
              }}>
                Secret Key <span style={{ color: '#ff4d4f' }}>*</span>
              </label>
              <input
                type={showKeys ? 'text' : 'password'}
                value={secretKey}
                onChange={(e) => setSecretKey(e.target.value)}
                placeholder="Secret Key를 입력하세요"
                autoComplete="off"
                style={{
                  width: '100%',
                  padding: '0.875rem',
                  border: '1px solid #d2d2d7',
                  borderRadius: '8px',
                  fontSize: '0.95rem',
                  fontFamily: 'SF Mono, Monaco, monospace',
                  transition: 'all 0.2s',
                  outline: 'none'
                }}
                onFocus={(e) => e.target.style.borderColor = '#0071e3'}
                onBlur={(e) => e.target.style.borderColor = '#d2d2d7'}
                required
              />
            </div>

            <div style={{ marginBottom: '2rem' }}>
              <label style={{
                display: 'block',
                marginBottom: '0.5rem',
                fontWeight: '500',
                fontSize: '0.9rem',
                color: '#1d1d1f'
              }}>
                Passphrase {SUPPORTED_EXCHANGES.find(ex => ex.value === selectedExchange)?.passphraseRequired
                  ? <span style={{ color: '#ff4d4f' }}>* (필수)</span>
                  : <span style={{ color: '#86868b' }}>(선택사항)</span>
                }
              </label>
              <input
                type={showKeys ? 'text' : 'password'}
                value={passphrase}
                onChange={(e) => setPassphrase(e.target.value)}
                placeholder={SUPPORTED_EXCHANGES.find(ex => ex.value === selectedExchange)?.passphraseRequired
                  ? "Passphrase를 입력하세요 (필수)"
                  : "Passphrase (선택사항)"
                }
                autoComplete="off"
                style={{
                  width: '100%',
                  padding: '0.875rem',
                  border: '1px solid #d2d2d7',
                  borderRadius: '8px',
                  fontSize: '0.95rem',
                  fontFamily: 'SF Mono, Monaco, monospace',
                  transition: 'all 0.2s',
                  outline: 'none'
                }}
                onFocus={(e) => e.target.style.borderColor = '#0071e3'}
                onBlur={(e) => e.target.style.borderColor = '#d2d2d7'}
              />
            </div>

            <div style={{
              display: 'flex',
              gap: '1rem',
              flexWrap: 'wrap'
            }}>
              <button
                type="submit"
                disabled={keysLoading}
                style={{
                  padding: '0.875rem 1.5rem',
                  background: keysLoading ? '#f5f5f7' : '#1d1d1f',
                  color: keysLoading ? '#86868b' : '#ffffff',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: keysLoading ? 'not-allowed' : 'pointer',
                  fontSize: '0.9rem',
                  fontWeight: '500',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  transition: 'all 0.2s'
                }}
              >
                <SaveOutlined />
                {keysLoading ? '저장 중...' : '저장'}
              </button>

              <button
                type="button"
                onClick={handleTestConnection}
                disabled={testingConnection}
                style={{
                  padding: '0.875rem 1.5rem',
                  background: '#ffffff',
                  color: testingConnection ? '#86868b' : '#1d1d1f',
                  border: '1px solid #d2d2d7',
                  borderRadius: '8px',
                  cursor: testingConnection ? 'not-allowed' : 'pointer',
                  fontSize: '0.9rem',
                  fontWeight: '500',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  transition: 'all 0.2s'
                }}
              >
                <ApiOutlined />
                {testingConnection ? '테스트 중...' : '연결 테스트'}
              </button>

              <button
                type="button"
                onClick={handleViewKeys}
                disabled={keysLoading}
                style={{
                  padding: '0.875rem 1.5rem',
                  background: 'transparent',
                  color: '#0071e3',
                  border: 'none',
                  cursor: keysLoading ? 'not-allowed' : 'pointer',
                  fontSize: '0.9rem',
                  fontWeight: '500',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  marginLeft: 'auto'
                }}
              >
                <KeyOutlined />
                {keysLoading ? '조회 중...' : '등록된 키 보기'}
              </button>

              <button
                type="button"
                onClick={() => setShowKeys(!showKeys)}
                style={{
                  padding: '0.875rem',
                  background: 'transparent',
                  color: '#86868b',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '1.1rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                {showKeys ? <EyeInvisibleOutlined /> : <EyeOutlined />}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Password Tab */}
      {activeTab === 'password' && (
        <div style={{
          background: 'white',
          padding: '2rem',
          borderRadius: '8px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          border: '1px solid #e5e7eb'
        }}>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>
            비밀번호 변경
          </h2>
          <p style={{ color: '#666', marginBottom: '1.5rem', fontSize: '0.875rem' }}>
            계정 보안을 위해 주기적으로 비밀번호를 변경하세요
          </p>

          <form onSubmit={handleChangePassword}>
            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{
                display: 'block',
                marginBottom: '0.5rem',
                fontWeight: 'bold',
                fontSize: '0.875rem'
              }}>
                현재 비밀번호
              </label>
              <input
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="현재 비밀번호를 입력하세요"
                style={{
                  width: '100%',
                  padding: '0.875rem',
                  border: '2px solid #e5e7eb',
                  borderRadius: '6px',
                  fontSize: '1rem'
                }}
              />
            </div>

            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{
                display: 'block',
                marginBottom: '0.5rem',
                fontWeight: 'bold',
                fontSize: '0.875rem'
              }}>
                새 비밀번호
              </label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="새 비밀번호 (최소 6자)"
                style={{
                  width: '100%',
                  padding: '0.875rem',
                  border: '2px solid #e5e7eb',
                  borderRadius: '6px',
                  fontSize: '1rem'
                }}
              />
            </div>

            <div style={{ marginBottom: '2rem' }}>
              <label style={{
                display: 'block',
                marginBottom: '0.5rem',
                fontWeight: 'bold',
                fontSize: '0.875rem'
              }}>
                비밀번호 확인
              </label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="새 비밀번호를 다시 입력하세요"
                style={{
                  width: '100%',
                  padding: '0.875rem',
                  border: '2px solid #e5e7eb',
                  borderRadius: '6px',
                  fontSize: '1rem'
                }}
              />
            </div>

            <button
              type="submit"
              disabled={passwordLoading}
              style={{
                width: '100%',
                padding: '1rem',
                background: passwordLoading ? '#e0e0e0' : 'linear-gradient(135deg, #ff9800 0%, #ffb74d 100%)',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: passwordLoading ? 'not-allowed' : 'pointer',
                fontSize: '1rem',
                fontWeight: 'bold',
                boxShadow: passwordLoading ? 'none' : '0 4px 6px rgba(255, 152, 0, 0.3)'
              }}
            >
              {passwordLoading ? '⏳ 변경 중...' : '🔒 비밀번호 변경'}
            </button>
          </form>
        </div>
      )}

      {/* 2FA Tab */}
      {activeTab === '2fa' && (
        <TwoFactorSettings />
      )}

      {/* Risk Management Tab */}
      {activeTab === 'risk' && (
        <div style={{
          background: 'white',
          padding: '2rem',
          borderRadius: '8px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          border: '1px solid #e5e7eb'
        }}>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>
            리스크 한도 설정
          </h2>
          <p style={{ color: '#666', marginBottom: '1.5rem', fontSize: '0.875rem' }}>
            자동매매 시스템의 리스크를 제한하여 계정을 보호하세요
          </p>

          <form onSubmit={handleSaveRiskSettings}>
            {/* 일일 손실 한도 */}
            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{
                display: 'block',
                marginBottom: '0.5rem',
                fontWeight: 'bold',
                fontSize: '0.875rem',
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                color: '#333'
              }}>
                일일 손실 한도 (USDT)
              </label>
              <input
                type="number"
                value={dailyLossLimit}
                onChange={(e) => setDailyLossLimit(e.target.value)}
                placeholder="예: 500"
                step="0.01"
                min="0"
                style={{
                  width: '100%',
                  padding: '0.875rem',
                  border: '2px solid #e5e7eb',
                  borderRadius: '6px',
                  fontSize: '1rem',
                  fontFamily: 'monospace',
                  transition: 'all 0.2s'
                }}
                onFocus={(e) => e.target.style.borderColor = '#f44336'}
                onBlur={(e) => e.target.style.borderColor = '#e5e7eb'}
                required
              />
              <div style={{ marginTop: '0.5rem', fontSize: '0.75rem', color: '#666' }}>
                💡 하루에 손실이 이 금액을 초과하면 자동으로 봇이 정지됩니다.
              </div>
            </div>

            {/* 최대 레버리지 */}
            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{
                display: 'block',
                marginBottom: '0.5rem',
                fontWeight: 'bold',
                fontSize: '0.875rem',
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                color: '#333'
              }}>
                최대 레버리지 (배)
              </label>
              <input
                type="number"
                value={maxLeverage}
                onChange={(e) => setMaxLeverage(e.target.value)}
                placeholder="예: 10"
                step="1"
                min="1"
                max="100"
                style={{
                  width: '100%',
                  padding: '0.875rem',
                  border: '2px solid #e5e7eb',
                  borderRadius: '6px',
                  fontSize: '1rem',
                  fontFamily: 'monospace',
                  transition: 'all 0.2s'
                }}
                onFocus={(e) => e.target.style.borderColor = '#ff9800'}
                onBlur={(e) => e.target.style.borderColor = '#e5e7eb'}
                required
              />
              <div style={{ marginTop: '0.5rem', fontSize: '0.75rem', color: '#666' }}>
                💡 시스템이 사용할 수 있는 최대 레버리지를 제한합니다. (권장: 10배 이하)
              </div>
            </div>

            {/* 최대 포지션 개수 */}
            <div style={{ marginBottom: '2rem' }}>
              <label style={{
                display: 'block',
                marginBottom: '0.5rem',
                fontWeight: 'bold',
                fontSize: '0.875rem',
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                color: '#333'
              }}>
                최대 포지션 개수
              </label>
              <input
                type="number"
                value={maxPositions}
                onChange={(e) => setMaxPositions(e.target.value)}
                placeholder="예: 5"
                step="1"
                min="1"
                max="50"
                style={{
                  width: '100%',
                  padding: '0.875rem',
                  border: '2px solid #e5e7eb',
                  borderRadius: '6px',
                  fontSize: '1rem',
                  fontFamily: 'monospace',
                  transition: 'all 0.2s'
                }}
                onFocus={(e) => e.target.style.borderColor = '#2196f3'}
                onBlur={(e) => e.target.style.borderColor = '#e5e7eb'}
                required
              />
              <div style={{ marginTop: '0.5rem', fontSize: '0.75rem', color: '#666' }}>
                💡 동시에 열 수 있는 최대 포지션 개수를 제한합니다.
              </div>
            </div>

            {/* 저장 버튼 */}
            <button
              type="submit"
              disabled={riskLoading}
              style={{
                width: '100%',
                padding: '1rem',
                background: riskLoading ? '#e0e0e0' : 'linear-gradient(135deg, #f44336 0%, #e91e63 100%)',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: riskLoading ? 'not-allowed' : 'pointer',
                fontSize: '1rem',
                fontWeight: 'bold',
                boxShadow: riskLoading ? 'none' : '0 4px 6px rgba(244, 67, 54, 0.3)',
                transition: 'all 0.2s'
              }}
              onMouseEnter={(e) => {
                if (!riskLoading) {
                  e.target.style.transform = 'translateY(-2px)';
                  e.target.style.boxShadow = '0 6px 12px rgba(244, 67, 54, 0.4)';
                }
              }}
              onMouseLeave={(e) => {
                if (!riskLoading) {
                  e.target.style.transform = 'translateY(0)';
                  e.target.style.boxShadow = '0 4px 6px rgba(244, 67, 54, 0.3)';
                }
              }}
            >
              {riskLoading ? '⏳ 저장 중...' : '⚠️ 리스크 한도 저장'}
            </button>
          </form>

          {/* 경고 메시지 */}
          {/* 경고 메시지 */}
          <div style={{
            marginTop: '1.5rem',
            padding: '1rem',
            background: '#fff2f0',
            border: '1px solid #ffccc7',
            borderRadius: '8px',
            color: '#ff4d4f'
          }}>
            <div style={{ fontWeight: '600', marginBottom: '0.5rem', fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: 8 }}>
              <WarningOutlined /> 중요 안내
            </div>
            <ul style={{ margin: 0, paddingLeft: '1.5rem', lineHeight: '1.8', fontSize: '0.85rem', color: '#595959' }}>
              <li>일일 손실 한도에 도달하면 <strong>모든 포지션이 자동으로 청산</strong>됩니다.</li>
              <li>레버리지가 높을수록 청산 리스크가 커집니다. 신중하게 설정하세요.</li>
              <li>포지션 개수를 제한하여 분산 투자와 리스크 관리를 할 수 있습니다.</li>
              <li>이 설정은 실시간으로 적용되며, 백엔드 구현 후 활성화됩니다.</li>
            </ul>
          </div>
        </div>
      )}

      {/* Telegram Tab */}
      {activeTab === 'telegram' && (
        <div style={{
          background: 'white',
          padding: '2rem',
          borderRadius: '16px',
          border: '1px solid #f5f5f7'
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '2rem',
            paddingBottom: '1rem',
            borderBottom: '1px solid #f5f5f7'
          }}>
            <div>
              <h2 style={{ fontSize: '1.25rem', fontWeight: '600', margin: 0, marginBottom: '0.5rem', color: '#1d1d1f' }}>
                텔레그램 알림 설정
              </h2>
              <p style={{ color: '#86868b', margin: 0, fontSize: '0.9rem' }}>
                실시간 거래 알림을 텔레그램으로 받으세요
              </p>
            </div>
            {telegramStatus && (
              <div style={{
                padding: '0.5rem 1rem',
                background: telegramStatus.enabled ? '#f6ffed' : '#fffbe6',
                color: telegramStatus.enabled ? '#52c41a' : '#faad14',
                borderRadius: '8px',
                fontSize: '0.85rem',
                fontWeight: '500',
                border: `1px solid ${telegramStatus.enabled ? '#b7eb8f' : '#ffe58f'}`,
                display: 'flex',
                alignItems: 'center',
                gap: 6
              }}>
                {telegramStatus.enabled ? <CheckCircleOutlined /> : <WarningOutlined />}
                {telegramStatus.enabled ? '연결됨' : '미설정'}
              </div>
            )}
          </div>

          {/* 저장된 텔레그램 설정 정보 */}
          {savedTelegramInfo && (
            <div style={{
              background: '#f6ffed',
              padding: '1rem 1.5rem',
              borderRadius: '12px',
              marginBottom: '2rem',
              border: '1px solid #b7eb8f'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <CheckCircleOutlined style={{ color: '#52c41a' }} />
                  <span style={{ fontWeight: '600', color: '#1d1d1f' }}>현재 등록된 텔레그램 설정</span>
                </div>
                <button
                  onClick={handleDeleteTelegram}
                  disabled={deleteTelegramLoading}
                  style={{
                    padding: '0.5rem 1rem',
                    background: deleteTelegramLoading ? '#f5f5f7' : '#ff4d4f',
                    color: deleteTelegramLoading ? '#86868b' : '#ffffff',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: deleteTelegramLoading ? 'not-allowed' : 'pointer',
                    fontSize: '0.8rem',
                    fontWeight: '500',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4,
                    transition: 'all 0.2s'
                  }}
                >
                  <CloseCircleOutlined />
                  {deleteTelegramLoading ? '삭제 중...' : '설정 삭제'}
                </button>
              </div>
              <div style={{
                fontFamily: 'SF Mono, Monaco, monospace',
                fontSize: '0.85rem',
                color: '#434343',
                display: 'grid',
                gap: '0.5rem'
              }}>
                <div>
                  <span style={{ color: '#86868b', minWidth: '80px', display: 'inline-block' }}>Bot Token:</span>
                  <span style={{ fontWeight: '500' }}>{savedTelegramInfo.maskedBotToken}</span>
                </div>
                <div>
                  <span style={{ color: '#86868b', minWidth: '80px', display: 'inline-block' }}>Chat ID:</span>
                  <span style={{ fontWeight: '500' }}>{savedTelegramInfo.maskedChatId}</span>
                </div>
                <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: '#52c41a' }}>
                  ✓ 거래 알림: {savedTelegramInfo.notifyTrades ? '활성' : '비활성'} |
                  시스템 알림: {savedTelegramInfo.notifySystem ? '활성' : '비활성'} |
                  에러 알림: {savedTelegramInfo.notifyErrors ? '활성' : '비활성'}
                </div>
              </div>
            </div>
          )}

          {/* 설정 가이드 */}
          <div style={{
            background: '#f0f5ff',
            padding: '1.5rem',
            borderRadius: '12px',
            marginBottom: '2rem',
            border: '1px solid #d6e4ff'
          }}>
            <h4 style={{ margin: '0 0 1rem 0', color: '#1d1d1f', fontSize: '1rem', fontWeight: '600' }}>
              <InfoCircleOutlined style={{ marginRight: 8, color: '#1890ff' }} />
              텔레그램 봇 설정 방법
            </h4>
            <ol style={{ margin: 0, paddingLeft: '1.5rem', color: '#434343', lineHeight: '1.8', fontSize: '0.9rem' }}>
              <li>텔레그램에서 <strong>@BotFather</strong> 검색 후 대화 시작</li>
              <li><code>/newbot</code> 명령어로 새 봇 생성</li>
              <li>봇 이름 입력 후 <strong>Bot Token</strong> 복사</li>
              <li>생성된 봇에게 아무 메시지 전송</li>
              <li><a href="#" style={{ color: '#1890ff' }}>이 링크</a>에서 <strong>Chat ID</strong> 확인 (응답의 chat.id 값)</li>
            </ol>
          </div>

          <form onSubmit={handleSaveTelegram}>
            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{
                display: 'block',
                marginBottom: '0.5rem',
                fontWeight: '500',
                fontSize: '0.9rem',
                color: '#1d1d1f'
              }}>
                Bot Token <span style={{ color: '#ff4d4f' }}>*</span>
              </label>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <input
                  type={showTelegramToken ? 'text' : 'password'}
                  value={telegramBotToken}
                  onChange={(e) => setTelegramBotToken(e.target.value)}
                  placeholder="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
                  autoComplete="off"
                  style={{
                    flex: 1,
                    padding: '0.875rem',
                    border: '1px solid #d2d2d7',
                    borderRadius: '8px',
                    fontSize: '0.95rem',
                    fontFamily: 'SF Mono, Monaco, monospace',
                    transition: 'all 0.2s',
                    outline: 'none'
                  }}
                  onFocus={(e) => e.target.style.borderColor = '#0071e3'}
                  onBlur={(e) => e.target.style.borderColor = '#d2d2d7'}
                />
                <button
                  type="button"
                  onClick={() => setShowTelegramToken(!showTelegramToken)}
                  style={{
                    padding: '0.875rem',
                    background: 'transparent',
                    border: '1px solid #d2d2d7',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    color: '#86868b',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: '46px'
                  }}
                >
                  {showTelegramToken ? <EyeInvisibleOutlined /> : <EyeOutlined />}
                </button>
              </div>
            </div>

            <div style={{ marginBottom: '2rem' }}>
              <label style={{
                display: 'block',
                marginBottom: '0.5rem',
                fontWeight: '500',
                fontSize: '0.9rem',
                color: '#1d1d1f'
              }}>
                Chat ID <span style={{ color: '#ff4d4f' }}>*</span>
              </label>
              <input
                type="text"
                value={telegramChatId}
                onChange={(e) => setTelegramChatId(e.target.value)}
                placeholder="예: 123456789 또는 -1001234567890"
                autoComplete="off"
                style={{
                  width: '100%',
                  padding: '0.875rem',
                  border: '1px solid #d2d2d7',
                  borderRadius: '8px',
                  fontSize: '0.95rem',
                  fontFamily: 'SF Mono, Monaco, monospace',
                  transition: 'all 0.2s',
                  outline: 'none'
                }}
                onFocus={(e) => e.target.style.borderColor = '#0071e3'}
                onBlur={(e) => e.target.style.borderColor = '#d2d2d7'}
              />
              <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: '#86868b' }}>
                <p style={{ margin: 0 }}>
                  Chat ID 확인 방법: 봇에게 아무 메시지 전송 후
                  <a
                    href={`https://api.telegram.org/bot${telegramBotToken || 'YOUR_BOT_TOKEN'}/getUpdates`}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: '#1890ff', marginLeft: '4px' }}
                  >
                    이 링크
                  </a>
                  에서 확인 (result[0].message.chat.id 값)
                </p>
                <p style={{ margin: '4px 0 0 0' }}>
                  그룹 채팅의 경우 Chat ID가 음수입니다 (예: -1001234567890)
                </p>
              </div>
            </div>

            <div style={{
              display: 'flex',
              gap: '1rem',
              flexWrap: 'wrap'
            }}>
              <button
                type="submit"
                disabled={telegramLoading}
                style={{
                  padding: '0.875rem 1.5rem',
                  background: telegramLoading ? '#f5f5f7' : '#1d1d1f',
                  color: telegramLoading ? '#86868b' : '#ffffff',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: telegramLoading ? 'not-allowed' : 'pointer',
                  fontSize: '0.9rem',
                  fontWeight: '500',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  transition: 'all 0.2s'
                }}
              >
                <SaveOutlined />
                {telegramLoading ? '저장 중...' : '설정 저장'}
              </button>

              <button
                type="button"
                onClick={handleTestTelegram}
                disabled={telegramLoading}
                style={{
                  padding: '0.875rem 1.5rem',
                  background: '#ffffff',
                  color: telegramLoading ? '#86868b' : '#1d1d1f',
                  border: '1px solid #d2d2d7',
                  borderRadius: '8px',
                  cursor: telegramLoading ? 'not-allowed' : 'pointer',
                  fontSize: '0.9rem',
                  fontWeight: '500',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  transition: 'all 0.2s'
                }}
              >
                <SendOutlined />
                {telegramLoading ? '전송 중...' : '테스트 메시지'}
              </button>
            </div>
          </form>

          {/* 알림 유형 안내 */}
          <div style={{
            marginTop: '2rem',
            padding: '1.5rem',
            background: '#f5f5f7',
            borderRadius: '12px',
            border: '1px solid #e5e5e5'
          }}>
            <h4 style={{ margin: '0 0 1rem 0', fontSize: '0.95rem', fontWeight: '600', color: '#1d1d1f' }}>알림 유형</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem' }}>
              <div>
                <div style={{ fontWeight: '600', marginBottom: 4, color: '#1d1d1f' }}>거래 알림</div>
                <p style={{ margin: 0, fontSize: '0.85rem', color: '#86868b' }}>
                  신규 진입, 포지션 종료, 손익 알림
                </p>
              </div>
              <div>
                <div style={{ fontWeight: '600', marginBottom: 4, color: '#1d1d1f' }}>시스템 알림</div>
                <p style={{ margin: 0, fontSize: '0.85rem', color: '#86868b' }}>
                  봇 시작/종료, 미청산 포지션 경고
                </p>
              </div>
              <div>
                <div style={{ fontWeight: '600', marginBottom: 4, color: '#1d1d1f' }}>에러 알림</div>
                <p style={{ margin: 0, fontSize: '0.85rem', color: '#86868b' }}>
                  API 연결 실패, 주문 실패 등
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Info Tab */}
      {activeTab === 'info' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Security Info */}
          <div style={{
            background: 'linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%)',
            padding: '1.5rem',
            borderRadius: '8px',
            border: '1px solid #90caf9'
          }}>
            <h3 style={{ fontSize: '1.25rem', marginBottom: '1rem', color: '#1565c0', fontWeight: 'bold' }}>
              🔐 보안 안내
            </h3>
            <ul style={{ margin: 0, paddingLeft: '1.5rem', color: '#1976d2', lineHeight: '1.8' }}>
              <li>API 키는 AES-256 암호화되어 안전하게 저장됩니다.</li>
              <li>등록된 API 키 조회는 보안상의 이유로 시간당 3회로 제한됩니다.</li>
              <li>API 키 생성 시 IP 화이트리스트를 설정하는 것을 권장합니다.</li>
              <li><strong>출금 권한은 절대 부여하지 마세요.</strong> 읽기 및 거래 권한만 필요합니다.</li>
              <li>API 키가 노출된 경우 즉시 거래소에서 키를 삭제하세요.</li>
            </ul>
          </div>

          {/* Bitget API Guide */}
          <div style={{
            background: 'white',
            padding: '1.5rem',
            borderRadius: '8px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            border: '1px solid #e5e7eb'
          }}>
            <h3 style={{ fontSize: '1.25rem', marginBottom: '1rem', fontWeight: 'bold' }}>
              📖 Bitget API 키 생성 가이드
            </h3>
            <ol style={{ margin: 0, paddingLeft: '1.5rem', color: '#666', lineHeight: '2' }}>
              <li><a href="https://www.bitget.com" target="_blank" rel="noopener noreferrer" style={{ color: '#667eea' }}>Bitget 웹사이트</a>에 로그인합니다.</li>
              <li>우측 상단 프로필 &gt; <strong>API 관리</strong>로 이동합니다.</li>
              <li>'API 키 생성' 버튼을 클릭합니다.</li>
              <li>API 이름을 입력하고, 권한 설정에서:
                <ul style={{ marginTop: '0.5rem' }}>
                  <li>✅ <strong>읽기 권한</strong> 활성화</li>
                  <li>✅ <strong>거래 권한</strong> 활성화</li>
                  <li>❌ <strong>출금 권한</strong> 비활성화 (중요!)</li>
                </ul>
              </li>
              <li>IP 화이트리스트 설정 (선택사항이지만 권장)</li>
              <li>생성된 API Key와 Secret Key를 안전하게 복사합니다.</li>
              <li>위 'API 키' 탭에서 복사한 키를 입력하고 저장합니다.</li>
              <li>'연결 테스트' 버튼으로 정상 작동 확인</li>
            </ol>
          </div>

          {/* FAQ */}
          <div style={{
            background: 'white',
            padding: '1.5rem',
            borderRadius: '8px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            border: '1px solid #e5e7eb'
          }}>
            <h3 style={{ fontSize: '1.25rem', marginBottom: '1rem', fontWeight: 'bold' }}>
              ❓ 자주 묻는 질문
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <h4 style={{ fontSize: '1rem', fontWeight: 'bold', marginBottom: '0.5rem', color: '#333' }}>
                  Q. API 키가 안전한가요?
                </h4>
                <p style={{ color: '#666', margin: 0 }}>
                  네, API 키는 암호화되어 데이터베이스에 저장되며, HTTPS를 통해 전송됩니다.
                </p>
              </div>
              <div>
                <h4 style={{ fontSize: '1rem', fontWeight: 'bold', marginBottom: '0.5rem', color: '#333' }}>
                  Q. 연결 테스트가 실패하면?
                </h4>
                <p style={{ color: '#666', margin: 0 }}>
                  API 키와 Secret Key가 정확한지 확인하고, IP 화이트리스트 설정을 확인하세요.
                </p>
              </div>
              <div>
                <h4 style={{ fontSize: '1rem', fontWeight: 'bold', marginBottom: '0.5rem', color: '#333' }}>
                  Q. 여러 거래소를 지원하나요?
                </h4>
                <p style={{ color: '#666', margin: 0 }}>
                  네, 현재 <strong>5개 거래소</strong>를 지원합니다: Bitget, Binance, OKX, Bybit, Gate.io.
                  단, 1계정당 1개 거래소만 연결 가능하며, 거래소 변경 시 기존 키가 덮어씌워집니다.
                </p>
              </div>
              <div>
                <h4 style={{ fontSize: '1rem', fontWeight: 'bold', marginBottom: '0.5rem', color: '#333' }}>
                  Q. Passphrase가 무엇인가요?
                </h4>
                <p style={{ color: '#666', margin: 0 }}>
                  Bitget과 OKX는 API 키 생성 시 Passphrase를 설정해야 합니다.
                  Binance, Bybit, Gate.io는 Passphrase가 필요 없습니다.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

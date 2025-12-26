import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Form, Input, Button, Alert, Typography, Space, Divider, Tabs, message, Modal } from 'antd';
import {
  LoginOutlined,
  SafetyOutlined,
  PhoneOutlined,
  IdcardOutlined,
  GoogleOutlined,
  UserAddOutlined,
  LockOutlined,
  MenuOutlined,
  RobotOutlined,
  LineChartOutlined,
  ThunderboltOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import { useAuth } from '../context/AuthContext';
import { authAPI } from '../api/auth';

const { Title, Text } = Typography;

// Deep Signal 브랜드 색상 - Antigravity Blue
const BRAND_COLOR = '#0066FF';
const BRAND_DARK = '#1A1A1A';

// 플로팅 애니메이션 컴포넌트
const FloatingElement = ({ children, delay = '0s', style }) => (
  <div style={{ animation: `float 6s ease-in-out infinite`, animationDelay: delay, ...style }}>
    {children}
  </div>
);

// 플로팅 달러 지폐 SVG
const FloatingBill = ({ style, delay, rotate }) => (
  <div style={{ position: 'absolute', ...style, transform: `rotate(${rotate}deg)` }}>
    <FloatingElement delay={delay}>
      <svg width="80" height="48" viewBox="0 0 160 90">
        <defs>
          <linearGradient id={`billGrad-${delay}`} x1="0" y1="0" x2="160" y2="90">
            <stop offset="0" stopColor="#6EE7B7" />
            <stop offset="1" stopColor="#34D399" />
          </linearGradient>
        </defs>
        <rect x="2" y="2" width="156" height="86" rx="6" fill={`url(#billGrad-${delay})`} stroke="#065F46" strokeWidth="2" />
        <rect x="12" y="12" width="136" height="66" rx="4" fill="none" stroke="white" strokeWidth="2" strokeOpacity="0.6" />
        <circle cx="80" cy="45" r="20" fill="none" stroke="white" strokeWidth="2" />
        <text x="80" y="55" fontSize="24" fontWeight="bold" fill="#065F46" textAnchor="middle" fontFamily="sans-serif">$</text>
      </svg>
    </FloatingElement>
  </div>
);

// 플로팅 비트코인 SVG
const FloatingCoin = ({ style, delay }) => (
  <div style={{ position: 'absolute', ...style }}>
    <FloatingElement delay={delay}>
      <svg width="56" height="56" viewBox="0 0 100 100">
        <defs>
          <linearGradient id={`goldGrad-${delay}`} x1="0" y1="0" x2="100" y2="100">
            <stop offset="0" stopColor="#FCD34D" />
            <stop offset="1" stopColor="#F59E0B" />
          </linearGradient>
          <linearGradient id={`goldRim-${delay}`} x1="100" y1="0" x2="0" y2="100">
            <stop offset="0" stopColor="#F59E0B" />
            <stop offset="1" stopColor="#FCD34D" />
          </linearGradient>
        </defs>
        <circle cx="50" cy="50" r="45" fill={`url(#goldGrad-${delay})`} stroke={`url(#goldRim-${delay})`} strokeWidth="4" />
        <circle cx="50" cy="50" r="35" fill="none" stroke="#B45309" strokeWidth="2" strokeOpacity="0.3" strokeDasharray="4 2" />
        <text x="50" y="62" fontSize="40" fontWeight="bold" fill="#B45309" textAnchor="middle" fontFamily="sans-serif">₿</text>
      </svg>
    </FloatingElement>
  </div>
);

// 플로팅 다이아몬드 SVG
const FloatingGem = ({ style, delay }) => (
  <div style={{ position: 'absolute', ...style }}>
    <FloatingElement delay={delay}>
      <svg width="48" height="48" viewBox="0 0 100 100">
        <path d="M50 0 L100 40 L50 100 L0 40 Z" fill="#60A5FA" stroke="#2563EB" strokeWidth="2" />
        <path d="M50 0 L100 40 L50 40 Z" fill="#93C5FD" />
        <path d="M0 40 L50 0 L50 40 Z" fill="#3B82F6" />
      </svg>
    </FloatingElement>
  </div>
);

// 폰 목업 컴포넌트
const PhoneMockup = ({ isMobile }) => (
  <div style={{
    width: isMobile ? 260 : 320,
    height: isMobile ? 540 : 650,
    background: '#1a1a1a',
    borderRadius: 48,
    padding: 8,
    boxShadow: '0 30px 60px rgba(0,0,0,0.25), 0 10px 20px rgba(0,0,0,0.15)',
    position: 'relative',
    zIndex: 10,
  }}>
    {/* Notch */}
    <div style={{
      position: 'absolute',
      top: 0,
      left: '50%',
      transform: 'translateX(-50%)',
      width: 140,
      height: 28,
      background: '#1a1a1a',
      borderRadius: '0 0 16px 16px',
      zIndex: 20,
    }} />

    {/* Screen */}
    <div style={{
      width: '100%',
      height: '100%',
      borderRadius: 40,
      background: 'linear-gradient(180deg, #5236FF 0%, #3a25b3 100%)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Background glow */}
      <div style={{
        position: 'absolute',
        top: '30%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        width: 200,
        height: 200,
        background: 'rgba(255,255,255,0.15)',
        borderRadius: '50%',
        filter: 'blur(60px)',
      }} />

      {/* App Header */}
      <div style={{ paddingTop: 50, textAlign: 'center', zIndex: 10 }}>
        <h2 style={{ fontSize: 24, fontWeight: 700, color: '#fff', margin: 0, letterSpacing: '-0.5px' }}>Deep Signal</h2>
        <p style={{ fontSize: 11, color: 'rgba(147, 197, 253, 1)', marginTop: 4, fontWeight: 500, letterSpacing: '1px', textTransform: 'uppercase' }}>AI-POWERED TRADING</p>
      </div>

      {/* Central Icon */}
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', zIndex: 10 }}>
        <div style={{ position: 'relative' }}>
          {/* Glow */}
          <div style={{
            position: 'absolute',
            inset: -30,
            background: 'rgba(99, 102, 241, 0.5)',
            borderRadius: '50%',
            filter: 'blur(40px)',
          }} />
          <svg width="112" height="112" viewBox="0 0 100 100" style={{ position: 'relative', zIndex: 1 }}>
            <defs>
              <linearGradient id="mainIconGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#4F46E5" />
                <stop offset="50%" stopColor="#818CF8" />
                <stop offset="100%" stopColor="#C7D2FE" />
              </linearGradient>
            </defs>
            <circle cx="50" cy="50" r="48" fill="url(#mainIconGrad)" stroke="white" strokeWidth="2" strokeOpacity="0.5" />
            <path d="M30 50 L45 65 L75 35" fill="none" stroke="white" strokeWidth="8" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>

      {/* Floating UI Elements */}
      <div style={{
        position: 'absolute',
        top: 70,
        right: 20,
        width: 48,
        height: 48,
        background: 'rgba(255,255,255,0.1)',
        backdropFilter: 'blur(10px)',
        border: '1px solid rgba(255,255,255,0.2)',
        borderRadius: 16,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        animation: 'float 6s ease-in-out 1s infinite',
      }}>
        <span style={{ fontSize: 20, color: '#fde047' }}>⚡</span>
      </div>

      <div style={{
        position: 'absolute',
        bottom: 120,
        left: 20,
        width: 56,
        height: 56,
        background: 'rgba(255,255,255,0.1)',
        backdropFilter: 'blur(10px)',
        border: '1px solid rgba(255,255,255,0.2)',
        borderRadius: 16,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        animation: 'float 6s ease-in-out 2s infinite',
      }}>
        <span style={{ fontSize: 24, color: '#86efac' }}>📈</span>
      </div>

      {/* Price Pill */}
      <div style={{
        position: 'absolute',
        bottom: 100,
        right: 24,
        padding: '6px 12px',
        background: 'rgba(255,255,255,0.1)',
        backdropFilter: 'blur(10px)',
        border: '1px solid rgba(255,255,255,0.2)',
        borderRadius: 20,
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        animation: 'float 6s ease-in-out 3s infinite',
      }}>
        <div style={{ width: 8, height: 8, background: '#4ade80', borderRadius: '50%', animation: 'pulse 2s infinite' }} />
        <span style={{ fontSize: 12, fontWeight: 700, color: '#fff' }}>+24.5%</span>
      </div>

      {/* Bottom Navigation */}
      <div style={{
        height: 90,
        width: '100%',
        background: 'rgba(255,255,255,0.1)',
        backdropFilter: 'blur(10px)',
        borderTop: '1px solid rgba(255,255,255,0.05)',
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-around',
        paddingTop: 20,
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 20, color: '#fff' }}>🛡️</span>
          <div style={{ width: 4, height: 4, background: '#fff', borderRadius: '50%' }} />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6, opacity: 0.4 }}>
          <span style={{ fontSize: 20, color: '#fff' }}>📈</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6, opacity: 0.4 }}>
          <div style={{ width: 24, height: 24, borderRadius: '50%', border: '2px solid #fff' }} />
        </div>
      </div>

      {/* Home Indicator */}
      <div style={{
        position: 'absolute',
        bottom: 8,
        left: '50%',
        transform: 'translateX(-50%)',
        width: 120,
        height: 4,
        background: 'rgba(255,255,255,0.3)',
        borderRadius: 2,
      }} />
    </div>
  </div>
);

export default function Login() {
  const [isMobile, setIsMobile] = useState(window.innerWidth < 900);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('login');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [requires2FA, setRequires2FA] = useState(false);
  const [tempCredentials, setTempCredentials] = useState(null);
  const [totpCode, setTotpCode] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();
  const totpInputRef = useRef(null);
  const [loginForm] = Form.useForm();
  const [registerForm] = Form.useForm();

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 900);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    if (requires2FA && totpInputRef.current) totpInputRef.current.focus();
  }, [requires2FA]);

  const handleLoginSubmit = async (values) => {
    setError('');
    setLoading(true);
    try {
      const result = await login(values.email, values.password);
      if (result.requires_2fa) {
        setRequires2FA(true);
        setTempCredentials({ email: values.email, password: values.password });
        setLoading(false);
        return;
      }
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || '로그인에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleRegisterSubmit = async (values) => {
    setError('');
    setLoading(true);
    try {
      const result = await authAPI.register(values.email, values.password, values.passwordConfirm, values.name, values.phone);
      if (result.access_token) {
        message.success('회원가입이 완료되었습니다!');
        setActiveTab('login');
        loginForm.setFieldsValue({ email: values.email, password: '' });
        registerForm.resetFields();
      }
    } catch (err) {
      // 다양한 에러 응답 형식 처리
      const detail = err.response?.data?.detail;
      const error = err.response?.data?.error;

      let errorMsg = '회원가입 실패';

      if (Array.isArray(detail)) {
        // Pydantic 검증 에러 (배열)
        errorMsg = detail.map(e => e.message || e.msg).join(', ');
      } else if (error?.message) {
        // 커스텀 에러 응답
        errorMsg = error.message;
      } else if (error?.details?.errors) {
        // 표준화된 에러 응답
        errorMsg = error.details.errors.map(e => e.message).join(', ');
      } else if (typeof detail === 'string') {
        errorMsg = detail;
      }

      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handle2FASubmit = async () => {
    if (!totpCode || totpCode.length !== 6) { setError('6자리 코드 입력'); return; }
    setError('');
    setLoading(true);
    try {
      await login(tempCredentials.email, tempCredentials.password, totpCode);
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || '인증 코드 오류');
      setTotpCode('');
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    setRequires2FA(false);
    setTempCredentials(null);
    setTotpCode('');
    setError('');
  };

  const handleTotpChange = (e) => {
    const value = e.target.value.replace(/\D/g, '').slice(0, 6);
    setTotpCode(value);
    if (value.length === 6) setTimeout(() => handle2FASubmit(), 100);
  };

  // 🔒 SECURITY FIX: API URL 검증 (프로덕션에서 fallback 없음)
  const API_BASE_URL = (() => {
    const apiUrl = import.meta.env.VITE_API_URL;

    // 개발 환경에서는 localhost fallback 허용
    if (import.meta.env.DEV) {
      return apiUrl || 'http://localhost:8000';
    }

    // 프로덕션 환경에서는 필수
    if (!apiUrl) {
      throw new Error('VITE_API_URL must be set in production environment');
    }

    return apiUrl;
  })();

  const handleGoogleLogin = () => { window.location.href = `${API_BASE_URL}/auth/google/login`; };
  const handleKakaoLogin = () => { window.location.href = `${API_BASE_URL}/auth/kakao/login`; };
  const openModal = () => { setIsModalOpen(true); setActiveTab('login'); setError(''); };

  // 탭 아이템
  const tabItems = [
    {
      key: 'login',
      label: <span><LoginOutlined /> 로그인</span>,
      children: (
        <>
          <Form form={loginForm} name="login" onFinish={handleLoginSubmit} layout="vertical" size="large">
            <Form.Item name="email" rules={[{ required: true, message: '사용자명을 입력해주세요' }]}>
              <Input prefix={<IdcardOutlined style={{ color: '#9ca3af' }} />} placeholder="사용자명" style={{ borderRadius: 8, height: 48 }} />
            </Form.Item>
            <Form.Item name="password" rules={[{ required: true, message: '비밀번호 입력' }]}>
              <Input.Password prefix={<LockOutlined style={{ color: '#9ca3af' }} />} placeholder="비밀번호" style={{ borderRadius: 8, height: 48 }} />
            </Form.Item>
            {error && activeTab === 'login' && <Alert message={error} type="error" showIcon style={{ marginBottom: 16, borderRadius: 8 }} />}
            <Form.Item style={{ marginBottom: 16 }}>
              <Button type="primary" htmlType="submit" loading={loading} block style={{ height: 48, borderRadius: 24, fontWeight: 600, background: BRAND_COLOR, border: 'none' }}>로그인</Button>
            </Form.Item>
          </Form>
          <Divider style={{ margin: '16px 0' }}>소셜 로그인</Divider>
          <Space direction="vertical" style={{ width: '100%' }} size={12}>
            <Button block size="large" onClick={handleGoogleLogin} style={{ height: 48, borderRadius: 24, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, background: '#fff', border: '1px solid #e5e7eb' }}>
              <GoogleOutlined style={{ fontSize: 18, color: '#4285F4' }} /><span>Google로 로그인</span>
            </Button>
            <Button block size="large" onClick={handleKakaoLogin} style={{ height: 48, borderRadius: 24, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, background: '#FEE500', border: 'none', color: '#000' }}>
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path fillRule="evenodd" clipRule="evenodd" d="M9 0.5C4.02944 0.5 0 3.69256 0 7.64516C0 10.1108 1.55556 12.2742 3.93333 13.5161L2.93333 17.0323C2.87778 17.2419 3.12222 17.4113 3.3 17.2823L7.46667 14.5726C7.96667 14.6532 8.47778 14.6935 9 14.6935C13.9706 14.6935 18 11.5009 18 7.54839C18 3.59589 13.9706 0.5 9 0.5Z" fill="#000" /></svg>
              <span>카카오로 로그인</span>
            </Button>
          </Space>
          {/* SECURITY: 테스트 계정 정보는 개발 환경에서만 표시 */}
          {import.meta.env.DEV && (
            <div style={{ marginTop: 20 }}>
              <Divider style={{ margin: '16px 0' }}>테스트 계정 (개발용)</Divider>
              <div style={{ padding: 14, background: '#fff3cd', borderRadius: 8, border: '1px solid #ffc107' }}>
                <div style={{ marginBottom: 8, color: '#856404', fontSize: 12 }}>⚠️ 개발 환경에서만 표시됩니다</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}><Text style={{ color: '#86868b', fontSize: 13 }}>사용자명:</Text><Text strong copyable style={{ fontSize: 13 }}>admin</Text></div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}><Text style={{ color: '#86868b', fontSize: 13 }}>비밀번호:</Text><Text strong copyable style={{ fontSize: 13 }}>admin123</Text></div>
              </div>
            </div>
          )}
        </>
      ),
    },
    {
      key: 'register',
      label: <span><UserAddOutlined /> 회원가입</span>,
      children: (
        <Form form={registerForm} name="register" onFinish={handleRegisterSubmit} layout="vertical" size="large">
          <Form.Item name="email" rules={[{ required: true, message: '사용자명을 입력해주세요' }, { min: 4, message: '사용자명은 최소 4자 이상이어야 합니다' }, { max: 20, message: '사용자명은 20자를 초과할 수 없습니다' }, { pattern: /^[a-zA-Z0-9_-]+$/, message: '영문자, 숫자, 밑줄(_), 하이픈(-)만 사용 가능합니다' }]}><Input prefix={<IdcardOutlined style={{ color: '#9ca3af' }} />} placeholder="사용자명 (4-20자)" style={{ borderRadius: 8, height: 48 }} /></Form.Item>
          <Form.Item name="name" rules={[{ required: true }, { min: 2 }]}><Input prefix={<IdcardOutlined style={{ color: '#9ca3af' }} />} placeholder="이름" style={{ borderRadius: 8, height: 48 }} /></Form.Item>
          <Form.Item name="phone" rules={[{ required: true }, { pattern: /^[\d-]+$/ }]}><Input prefix={<PhoneOutlined style={{ color: '#9ca3af' }} />} placeholder="전화번호" style={{ borderRadius: 8, height: 48 }} /></Form.Item>
          <Form.Item
            name="password"
            rules={[
              { required: true, message: '비밀번호를 입력해주세요' },
              { min: 8, message: '비밀번호는 최소 8자 이상이어야 합니다' },
              { pattern: /[A-Z]/, message: '대문자를 포함해야 합니다' },
              { pattern: /[a-z]/, message: '소문자를 포함해야 합니다' },
              { pattern: /\d/, message: '숫자를 포함해야 합니다' },
              { pattern: /[@$!%*?&]/, message: '특수문자(@$!%*?&)를 포함해야 합니다' }
            ]}
          >
            <Input.Password
              prefix={<LockOutlined style={{ color: '#9ca3af' }} />}
              placeholder="비밀번호 (8자 이상, 대/소문자, 숫자, 특수문자)"
              style={{ borderRadius: 8, height: 48 }}
            />
          </Form.Item>
          <Form.Item name="passwordConfirm" dependencies={['password']} rules={[{ required: true }, ({ getFieldValue }) => ({ validator(_, v) { return !v || getFieldValue('password') === v ? Promise.resolve() : Promise.reject('비밀번호 불일치'); } })]}><Input.Password prefix={<LockOutlined style={{ color: '#9ca3af' }} />} placeholder="비밀번호 확인" style={{ borderRadius: 8, height: 48 }} /></Form.Item>
          {error && activeTab === 'register' && <Alert message={error} type="error" showIcon style={{ marginBottom: 16, borderRadius: 8 }} />}
          <Form.Item><Button type="primary" htmlType="submit" loading={loading} block style={{ height: 48, borderRadius: 24, fontWeight: 600, background: BRAND_COLOR, border: 'none' }}>가입하기</Button></Form.Item>
        </Form>
      ),
    },
  ];

  return (
    <div style={{ minHeight: '100vh', background: '#fff', fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif", position: 'relative', overflow: 'hidden' }}>
      {/* Background Gradient Mesh */}
      <div style={{ position: 'absolute', top: 0, right: 0, width: 800, height: 800, background: 'rgba(238, 242, 255, 0.5)', borderRadius: '50%', filter: 'blur(80px)', transform: 'translate(30%, -50%)', pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', bottom: 0, left: 0, width: 600, height: 600, background: 'rgba(219, 234, 254, 0.3)', borderRadius: '50%', filter: 'blur(80px)', transform: 'translate(-25%, 50%)', pointerEvents: 'none' }} />

      {/* SVG Wave Background (Bottom) */}
      <div style={{ position: 'absolute', bottom: 0, left: 0, width: '100%', height: '50vh', zIndex: 0, pointerEvents: 'none', opacity: 0.4 }}>
        <svg width="100%" height="100%" viewBox="0 0 1440 800" fill="none" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="none">
          <path d="M0 800V400C200 380 400 350 600 500C800 650 1000 600 1200 450C1300 375 1400 350 1440 340V800H0Z" fill="#F8FAFC" />
          <path d="M0 800V550C250 500 500 650 750 600C1000 550 1250 650 1440 700V800H0Z" fill="#F1F5F9" />
          <path d="M0 400 C 400 300, 800 600, 1440 200" stroke="#E0E7FF" strokeWidth="1" fill="none" />
          <path d="M0 420 C 400 320, 800 620, 1440 220" stroke="#E0E7FF" strokeWidth="1" fill="none" />
          <path d="M0 440 C 400 340, 800 640, 1440 240" stroke="#E0E7FF" strokeWidth="1" fill="none" />
        </svg>
      </div>

      {/* Header Navigation */}
      <nav style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: isMobile ? '16px 24px' : '24px 60px',
        background: 'transparent',
        position: 'relative',
        zIndex: 50,
      }}>
        <div style={{ fontSize: 28, fontWeight: 700, color: BRAND_DARK, letterSpacing: '-0.5px' }}>
          Deep Signal
        </div>

        {/* Desktop Nav */}
        {!isMobile && (
          <div style={{ display: 'flex', gap: 48 }}>
            {['Features', 'Pricing', 'Market Cap', 'Ticker'].map(item => (
              <span
                key={item}
                style={{
                  color: '#6b7280',
                  fontSize: 15,
                  fontWeight: 500,
                  cursor: 'pointer',
                  transition: 'color 0.2s'
                }}
                onMouseEnter={e => e.target.style.color = BRAND_COLOR}
                onMouseLeave={e => e.target.style.color = '#6b7280'}
              >
                {item}
              </span>
            ))}
          </div>
        )}

        {/* Login & Sign Up Buttons */}
        {!isMobile && (
          <div style={{ display: 'flex', gap: 12 }}>
            <button
              onClick={() => { setActiveTab('login'); openModal(); }}
              style={{
                background: 'transparent',
                color: BRAND_DARK,
                border: `2px solid ${BRAND_DARK}`,
                borderRadius: 24,
                padding: '10px 28px',
                fontWeight: 600,
                fontSize: 15,
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
              onMouseEnter={e => { e.target.style.background = BRAND_DARK; e.target.style.color = '#fff'; }}
              onMouseLeave={e => { e.target.style.background = 'transparent'; e.target.style.color = BRAND_DARK; }}
            >
              로그인
            </button>
            <button
              onClick={() => { setActiveTab('register'); openModal(); }}
              style={{
                background: BRAND_COLOR,
                color: '#fff',
                border: 'none',
                borderRadius: 24,
                padding: '12px 28px',
                fontWeight: 600,
                fontSize: 15,
                cursor: 'pointer',
                boxShadow: '0 4px 14px rgba(82, 54, 255, 0.3)',
                transition: 'all 0.2s',
              }}
              onMouseEnter={e => { e.target.style.transform = 'translateY(-2px)'; e.target.style.boxShadow = '0 6px 20px rgba(82, 54, 255, 0.4)'; }}
              onMouseLeave={e => { e.target.style.transform = 'translateY(0)'; e.target.style.boxShadow = '0 4px 14px rgba(82, 54, 255, 0.3)'; }}
            >
              회원가입
            </button>
          </div>
        )}

        {/* Mobile Menu Button */}
        {isMobile && (
          <button
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 8 }}
          >
            <MenuOutlined style={{ fontSize: 24, color: BRAND_DARK }} />
          </button>
        )}

        {/* Mobile Menu */}
        {isMobile && isMenuOpen && (
          <div style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            width: '100%',
            background: '#fff',
            boxShadow: '0 10px 40px rgba(0,0,0,0.1)',
            padding: 24,
            display: 'flex',
            flexDirection: 'column',
            gap: 16,
            zIndex: 100,
            borderTop: '1px solid #f3f4f6',
          }}>
            {['Features', 'Pricing', 'Market Cap', 'Ticker'].map(item => (
              <span key={item} style={{ color: BRAND_DARK, fontSize: 16, fontWeight: 500, padding: '8px 0' }}>{item}</span>
            ))}
            <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
              <button
                onClick={() => { setIsMenuOpen(false); setActiveTab('login'); openModal(); }}
                style={{
                  flex: 1,
                  background: 'transparent',
                  color: BRAND_DARK,
                  border: `2px solid ${BRAND_DARK}`,
                  borderRadius: 24,
                  padding: '14px 20px',
                  fontWeight: 600,
                  fontSize: 15,
                  cursor: 'pointer',
                }}
              >
                로그인
              </button>
              <button
                onClick={() => { setIsMenuOpen(false); setActiveTab('register'); openModal(); }}
                style={{
                  flex: 1,
                  background: BRAND_COLOR,
                  color: '#fff',
                  border: 'none',
                  borderRadius: 24,
                  padding: '14px 20px',
                  fontWeight: 600,
                  fontSize: 15,
                  cursor: 'pointer',
                }}
              >
                회원가입
              </button>
            </div>
          </div>
        )}
      </nav>

      {/* Main Hero Section */}
      <main style={{
        display: 'flex',
        flexDirection: isMobile ? 'column' : 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: isMobile ? '40px 24px 80px' : '60px 60px 120px',
        maxWidth: 1400,
        margin: '0 auto',
        position: 'relative',
        zIndex: 10,
      }}>
        {/* Left Column: Text */}
        <div style={{
          flex: 1,
          maxWidth: 520,
          textAlign: isMobile ? 'center' : 'left',
          marginBottom: isMobile ? 60 : 0
        }}>
          <h1 style={{
            fontSize: isMobile ? 42 : 64,
            fontWeight: 700,
            lineHeight: 1.1,
            margin: 0,
            marginBottom: 24,
            color: BRAND_DARK,
            letterSpacing: '-2px',
            fontFamily: "'Space Grotesk', 'Inter', sans-serif",
          }}>
            AI Trading crypto<br />
            never felt so<br />
            good
          </h1>
          <p style={{
            fontSize: 18,
            color: '#6b7280',
            lineHeight: 1.7,
            margin: 0,
            marginBottom: 36,
            maxWidth: 400,
          }}>
            Deep Signal allows you to trade crypto currency without all the confusion.
          </p>
          <div style={{ display: 'flex', gap: 16, justifyContent: isMobile ? 'center' : 'flex-start', flexWrap: 'wrap' }}>
            <button
              onClick={openModal}
              style={{
                background: BRAND_COLOR,
                color: '#fff',
                border: 'none',
                borderRadius: 28,
                padding: '16px 40px',
                fontWeight: 600,
                fontSize: 16,
                cursor: 'pointer',
                boxShadow: '0 6px 20px rgba(82, 54, 255, 0.35)',
                transition: 'all 0.2s',
              }}
              onMouseEnter={e => { e.target.style.transform = 'translateY(-2px)'; e.target.style.boxShadow = '0 8px 28px rgba(82, 54, 255, 0.45)'; }}
              onMouseLeave={e => { e.target.style.transform = 'translateY(0)'; e.target.style.boxShadow = '0 6px 20px rgba(82, 54, 255, 0.35)'; }}
            >
              Start Trading
            </button>
            <button
              style={{
                background: 'transparent',
                color: BRAND_DARK,
                border: '2px solid #1a1a1a',
                borderRadius: 28,
                padding: '14px 40px',
                fontWeight: 600,
                fontSize: 16,
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
              onMouseEnter={e => { e.target.style.background = BRAND_DARK; e.target.style.color = '#fff'; }}
              onMouseLeave={e => { e.target.style.background = 'transparent'; e.target.style.color = BRAND_DARK; }}
            >
              Learn More
            </button>
          </div>
        </div>

        {/* Right Column: Phone & Graphics */}
        <div style={{
          flex: 1,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          position: 'relative',
          minHeight: isMobile ? 560 : 680,
        }}>
          {/* Phone Mockup */}
          <PhoneMockup isMobile={isMobile} />

          {/* Floating Elements */}
          <FloatingBill style={{ top: -10, left: isMobile ? 0 : -80 }} delay="0s" rotate={-15} />
          <FloatingBill style={{ bottom: 100, left: isMobile ? 10 : -20 }} delay="2s" rotate={10} />
          <FloatingBill style={{ top: 80, right: isMobile ? 0 : -60 }} delay="1s" rotate={25} />

          <FloatingCoin style={{ top: 140, left: isMobile ? 20 : 40 }} delay="1.5s" />
          <FloatingCoin style={{ bottom: 160, right: isMobile ? 10 : -40 }} delay="0.5s" />
          <FloatingCoin style={{ bottom: -20, left: 50 }} delay="3s" />

          <FloatingGem style={{ top: 10, right: isMobile ? 20 : 40 }} delay="2.5s" />
        </div>
      </main>

      {/* AI Auto Trading Features Section */}
      <section style={{
        background: 'linear-gradient(180deg, #f8fafc 0%, #fff 100%)',
        padding: isMobile ? '60px 24px' : '100px 60px',
        position: 'relative',
        zIndex: 10,
      }}>
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
          {/* Section Header */}
          <div style={{ textAlign: 'center', marginBottom: isMobile ? 40 : 60 }}>
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              background: 'rgba(0, 102, 255, 0.1)',
              padding: '8px 20px',
              borderRadius: 30,
              marginBottom: 20,
            }}>
              <RobotOutlined style={{ fontSize: 18, color: BRAND_COLOR }} />
              <span style={{ fontSize: 14, fontWeight: 600, color: BRAND_COLOR }}>AI 기반 자동매매</span>
            </div>
            <h2 style={{
              fontSize: isMobile ? 28 : 42,
              fontWeight: 700,
              color: BRAND_DARK,
              margin: 0,
              marginBottom: 16,
              letterSpacing: '-1px',
            }}>
              24시간 쉬지 않는<br />당신만의 AI 트레이더
            </h2>
            <p style={{ fontSize: 17, color: '#6b7280', maxWidth: 550, margin: '0 auto', lineHeight: 1.7 }}>
              복잡한 차트 분석과 감정적인 매매는 이제 그만!<br />
              Deep Signal AI가 최적의 타이밍에 자동으로 거래합니다.
            </p>
          </div>

          {/* Feature Cards */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: isMobile ? '1fr' : 'repeat(3, 1fr)',
            gap: isMobile ? 20 : 24,
          }}>
            {/* Card 1 */}
            <div style={{
              background: '#fff',
              borderRadius: 24,
              padding: isMobile ? 28 : 36,
              boxShadow: '0 4px 20px rgba(0,0,0,0.06)',
              border: '1px solid #f0f0f5',
              transition: 'transform 0.3s, box-shadow 0.3s',
            }}
              onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-8px)'; e.currentTarget.style.boxShadow = '0 12px 40px rgba(82, 54, 255, 0.12)'; }}
              onMouseLeave={e => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = '0 4px 20px rgba(0,0,0,0.06)'; }}
            >
              <div style={{
                width: 56,
                height: 56,
                background: 'linear-gradient(135deg, #0066FF 0%, #0052CC 100%)',
                borderRadius: 16,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: 20,
              }}>
                <LineChartOutlined style={{ fontSize: 28, color: '#fff' }} />
              </div>
              <h3 style={{ fontSize: 20, fontWeight: 700, color: BRAND_DARK, margin: 0, marginBottom: 12 }}>
                실시간 시장 분석
              </h3>
              <p style={{ fontSize: 15, color: '#6b7280', lineHeight: 1.7, margin: 0 }}>
                AI가 수백 개의 기술적 지표와 온체인 데이터를 실시간으로 분석하여 최적의 진입/청산 시점을 포착합니다.
              </p>
            </div>

            {/* Card 2 */}
            <div style={{
              background: '#fff',
              borderRadius: 24,
              padding: isMobile ? 28 : 36,
              boxShadow: '0 4px 20px rgba(0,0,0,0.06)',
              border: '1px solid #f0f0f5',
              transition: 'transform 0.3s, box-shadow 0.3s',
            }}
              onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-8px)'; e.currentTarget.style.boxShadow = '0 12px 40px rgba(82, 54, 255, 0.12)'; }}
              onMouseLeave={e => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = '0 4px 20px rgba(0,0,0,0.06)'; }}
            >
              <div style={{
                width: 56,
                height: 56,
                background: 'linear-gradient(135deg, #0066FF 0%, #0052CC 100%)',
                borderRadius: 16,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: 20,
              }}>
                <ThunderboltOutlined style={{ fontSize: 28, color: '#fff' }} />
              </div>
              <h3 style={{ fontSize: 20, fontWeight: 700, color: BRAND_DARK, margin: 0, marginBottom: 12 }}>
                초고속 자동 매매
              </h3>
              <p style={{ fontSize: 15, color: '#6b7280', lineHeight: 1.7, margin: 0 }}>
                밀리초 단위의 초고속 주문 실행으로 시장 변동성을 놓치지 않습니다. 당신이 잠든 사이에도 AI가 수익을 창출합니다.
              </p>
            </div>

            {/* Card 3 */}
            <div style={{
              background: '#fff',
              borderRadius: 24,
              padding: isMobile ? 28 : 36,
              boxShadow: '0 4px 20px rgba(0,0,0,0.06)',
              border: '1px solid #f0f0f5',
              transition: 'transform 0.3s, box-shadow 0.3s',
            }}
              onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-8px)'; e.currentTarget.style.boxShadow = '0 12px 40px rgba(82, 54, 255, 0.12)'; }}
              onMouseLeave={e => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = '0 4px 20px rgba(0,0,0,0.06)'; }}
            >
              <div style={{
                width: 56,
                height: 56,
                background: 'linear-gradient(135deg, #0066FF 0%, #0052CC 100%)',
                borderRadius: 16,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: 20,
              }}>
                <SafetyCertificateOutlined style={{ fontSize: 28, color: '#fff' }} />
              </div>
              <h3 style={{ fontSize: 20, fontWeight: 700, color: BRAND_DARK, margin: 0, marginBottom: 12 }}>
                철저한 리스크 관리
              </h3>
              <p style={{ fontSize: 15, color: '#6b7280', lineHeight: 1.7, margin: 0 }}>
                스톱로스, 테이크프로핏, 포지션 사이징을 자동으로 관리합니다. 감정 없는 규칙 기반 트레이딩으로 자산을 보호합니다.
              </p>
            </div>
          </div>

          {/* Bottom Stats */}
          <div style={{
            display: 'flex',
            justifyContent: 'center',
            gap: isMobile ? 30 : 80,
            marginTop: isMobile ? 40 : 60,
            flexWrap: 'wrap',
          }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: isMobile ? 32 : 42, fontWeight: 700, color: BRAND_COLOR }}>24/7</div>
              <div style={{ fontSize: 14, color: '#6b7280', marginTop: 4 }}>무중단 자동매매</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: isMobile ? 32 : 42, fontWeight: 700, color: BRAND_COLOR }}>0.1초</div>
              <div style={{ fontSize: 14, color: '#6b7280', marginTop: 4 }}>주문 실행 속도</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: isMobile ? 32 : 42, fontWeight: 700, color: BRAND_COLOR }}>100+</div>
              <div style={{ fontSize: 14, color: '#6b7280', marginTop: 4 }}>분석 지표</div>
            </div>
          </div>
        </div>
      </section>

      {/* Login Modal */}
      <Modal
        open={isModalOpen}
        onCancel={() => setIsModalOpen(false)}
        footer={null}
        width={420}
        centered
        styles={{ body: { padding: '24px 24px 16px' } }}
      >
        {requires2FA ? (
          <div style={{ padding: '20px 0' }}>
            <div style={{ textAlign: 'center', marginBottom: 24 }}>
              <div style={{ width: 56, height: 56, background: `${BRAND_COLOR}15`, borderRadius: 14, display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
                <SafetyOutlined style={{ fontSize: 28, color: BRAND_COLOR }} />
              </div>
              <Title level={4} style={{ margin: 0 }}>2단계 인증</Title>
              <Text type="secondary">인증 앱에서 6자리 코드를 입력하세요</Text>
            </div>
            <Input ref={totpInputRef} size="large" placeholder="000000" value={totpCode} onChange={handleTotpChange} onPressEnter={handle2FASubmit} maxLength={6} style={{ textAlign: 'center', fontSize: 28, letterSpacing: 8, borderRadius: 12, height: 56, fontFamily: 'monospace', fontWeight: 'bold', marginBottom: 16 }} />
            {error && <Alert message={error} type="error" showIcon style={{ marginBottom: 16, borderRadius: 8 }} />}
            <Space direction="vertical" style={{ width: '100%' }}>
              <Button type="primary" onClick={handle2FASubmit} loading={loading} block style={{ height: 48, borderRadius: 24, fontWeight: 600, background: BRAND_COLOR, border: 'none' }}>인증</Button>
              <Button type="text" onClick={handleBack} block style={{ color: '#666' }}>← 돌아가기</Button>
            </Space>
          </div>
        ) : (
          <>
            <div style={{ textAlign: 'center', marginBottom: 20 }}>
              <div style={{ width: 56, height: 56, background: `linear-gradient(135deg, ${BRAND_COLOR} 0%, #4f46e5 100%)`, borderRadius: 14, display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 12px' }}>
                <span style={{ fontSize: 24, color: '#fff', fontWeight: 'bold' }}>DS</span>
              </div>
              <Title level={4} style={{ margin: 0, color: '#333' }}>Deep Signal</Title>
              <Text type="secondary">AI 기반 자동 트레이딩 플랫폼</Text>
            </div>
            <Tabs activeKey={activeTab} onChange={(key) => { setActiveTab(key); setError(''); }} centered items={tabItems} />
            <div style={{ textAlign: 'center', marginTop: 12 }}><Text type="secondary" style={{ fontSize: 11 }}>© 2025 Deep Signal. All rights reserved.</Text></div>
          </>
        )}
      </Modal>

      {/* Global Animations */}
      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-20px); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');
      `}</style>
    </div>
  );
}

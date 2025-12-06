import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Spin, Result, Typography } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';

const { Text } = Typography;

/**
 * OAuth 콜백 페이지
 * 소셜 로그인 완료 후 백엔드에서 이 페이지로 리다이렉트됩니다.
 * URL 파라미터에서 토큰을 추출하여 저장하고 대시보드로 이동합니다.
 */
export default function OAuthCallback() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const [status, setStatus] = useState('loading'); // loading, success, error
    const [message, setMessage] = useState('');

    useEffect(() => {
        const token = searchParams.get('token');
        const provider = searchParams.get('provider');
        const error = searchParams.get('error');

        if (error) {
            setStatus('error');
            const errorMessages = {
                google_auth_failed: 'Google 로그인이 취소되었거나 실패했습니다.',
                kakao_auth_failed: '카카오 로그인이 취소되었거나 실패했습니다.',
                invalid_state: '보안 검증에 실패했습니다. 다시 시도해주세요.',
                token_exchange_failed: '인증 토큰 교환에 실패했습니다.',
                userinfo_failed: '사용자 정보를 가져오는데 실패했습니다.',
                email_required: '이메일 정보가 필요합니다.',
                server_error: '서버 오류가 발생했습니다.',
            };
            setMessage(errorMessages[error] || '로그인 중 오류가 발생했습니다.');

            // 3초 후 로그인 페이지로 이동
            setTimeout(() => {
                navigate('/login');
            }, 3000);
            return;
        }

        if (token) {
            // 토큰 저장
            localStorage.setItem('token', token);

            // 토큰에서 사용자 정보 추출
            try {
                const base64Url = token.split('.')[1];
                const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
                const jsonPayload = decodeURIComponent(
                    atob(base64)
                        .split('')
                        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
                        .join('')
                );
                const payload = JSON.parse(jsonPayload);

                localStorage.setItem('userEmail', payload.email);
                localStorage.setItem('userId', payload.user_id);
                localStorage.setItem('userRole', payload.role || 'user');
            } catch (e) {
                console.error('Failed to decode token:', e);
            }

            setStatus('success');
            setMessage(`${provider === 'google' ? 'Google' : '카카오'} 로그인 성공!`);

            // 1초 후 대시보드로 이동
            setTimeout(() => {
                navigate('/dashboard');
            }, 1000);
        } else {
            setStatus('error');
            setMessage('인증 정보를 받지 못했습니다.');

            setTimeout(() => {
                navigate('/login');
            }, 3000);
        }
    }, [searchParams, navigate]);

    return (
        <div
            style={{
                minHeight: '100vh',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: '#f5f5f7',
                padding: 24,
            }}
        >
            {status === 'loading' && (
                <div style={{ textAlign: 'center' }}>
                    <Spin size="large" />
                    <div style={{ marginTop: 24 }}>
                        <Text style={{ fontSize: 16, color: '#86868b' }}>
                            로그인 처리 중...
                        </Text>
                    </div>
                </div>
            )}

            {status === 'success' && (
                <Result
                    icon={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
                    title="로그인 성공!"
                    subTitle={message}
                    extra={
                        <Text type="secondary">
                            잠시 후 대시보드로 이동합니다...
                        </Text>
                    }
                />
            )}

            {status === 'error' && (
                <Result
                    icon={<CloseCircleOutlined style={{ color: '#ff4d4f' }} />}
                    title="로그인 실패"
                    subTitle={message}
                    extra={
                        <Text type="secondary">
                            잠시 후 로그인 페이지로 이동합니다...
                        </Text>
                    }
                />
            )}
        </div>
    );
}

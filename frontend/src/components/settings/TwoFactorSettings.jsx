import { useState, useEffect } from 'react';
import { Card, Button, Input, Alert, Space, Typography, Modal, Divider, Spin, Steps, message } from 'antd';
import {
    SafetyOutlined,
    CheckCircleOutlined,
    CloseCircleOutlined,
    QrcodeOutlined,
    CopyOutlined,
    ExclamationCircleOutlined,
    LoadingOutlined,
} from '@ant-design/icons';
import { twoFactorAPI } from '../../api/auth';

const { Title, Text, Paragraph } = Typography;
const { Step } = Steps;

export default function TwoFactorSettings() {
    const [loading, setLoading] = useState(true);
    const [is2FAEnabled, setIs2FAEnabled] = useState(false);
    const [email, setEmail] = useState('');

    // Setup state
    const [setupModalVisible, setSetupModalVisible] = useState(false);
    const [setupStep, setSetupStep] = useState(0);
    const [setupData, setSetupData] = useState(null);
    const [verifyCode, setVerifyCode] = useState('');
    const [setupLoading, setSetupLoading] = useState(false);

    // Disable state
    const [disableModalVisible, setDisableModalVisible] = useState(false);
    const [disableCode, setDisableCode] = useState('');
    const [disablePassword, setDisablePassword] = useState('');
    const [disableLoading, setDisableLoading] = useState(false);

    useEffect(() => {
        loadStatus();
    }, []);

    const loadStatus = async () => {
        setLoading(true);
        try {
            const data = await twoFactorAPI.getStatus();
            setIs2FAEnabled(data.is_enabled);
            setEmail(data.email);
        } catch (err) {
            console.error('[2FA] Failed to load status:', err);
            message.error('2FA 상태 조회 실패');
        } finally {
            setLoading(false);
        }
    };

    const handleStartSetup = async () => {
        setSetupLoading(true);
        try {
            const data = await twoFactorAPI.setup();
            setSetupData(data);
            setSetupStep(0);
            setSetupModalVisible(true);
        } catch (err) {
            console.error('[2FA] Setup failed:', err);
            message.error(err.response?.data?.detail || '2FA 설정 시작 실패');
        } finally {
            setSetupLoading(false);
        }
    };

    const handleVerify = async () => {
        if (!verifyCode || verifyCode.length !== 6) {
            message.warning('6자리 인증 코드를 입력하세요');
            return;
        }

        setSetupLoading(true);
        try {
            await twoFactorAPI.verify(verifyCode);
            message.success('🎉 2FA가 활성화되었습니다!');
            setIs2FAEnabled(true);
            setSetupModalVisible(false);
            setSetupData(null);
            setVerifyCode('');
            setSetupStep(0);
        } catch (err) {
            console.error('[2FA] Verification failed:', err);
            message.error(err.response?.data?.detail || '인증 코드가 올바르지 않습니다');
            setVerifyCode('');
        } finally {
            setSetupLoading(false);
        }
    };

    const handleDisable = async () => {
        if (!disableCode || disableCode.length !== 6) {
            message.warning('6자리 인증 코드를 입력하세요');
            return;
        }
        if (!disablePassword) {
            message.warning('비밀번호를 입력하세요');
            return;
        }

        setDisableLoading(true);
        try {
            await twoFactorAPI.disable(disableCode, disablePassword);
            message.success('2FA가 비활성화되었습니다');
            setIs2FAEnabled(false);
            setDisableModalVisible(false);
            setDisableCode('');
            setDisablePassword('');
        } catch (err) {
            console.error('[2FA] Disable failed:', err);
            message.error(err.response?.data?.detail || '2FA 비활성화 실패');
            setDisableCode('');
        } finally {
            setDisableLoading(false);
        }
    };

    const copyToClipboard = (text) => {
        navigator.clipboard.writeText(text);
        message.success('복사되었습니다');
    };

    if (loading) {
        return (
            <Card>
                <div style={{ textAlign: 'center', padding: 40 }}>
                    <Spin indicator={<LoadingOutlined style={{ fontSize: 24 }} spin />} />
                    <p>2FA 상태 확인 중...</p>
                </div>
            </Card>
        );
    }

    return (
        <>
            <Card
                title={
                    <Space>
                        <SafetyOutlined style={{ color: '#10b981' }} />
                        <span>2단계 인증 (2FA)</span>
                    </Space>
                }
                extra={
                    is2FAEnabled ? (
                        <span style={{ color: '#10b981', fontWeight: 'bold' }}>
                            <CheckCircleOutlined /> 활성화됨
                        </span>
                    ) : (
                        <span style={{ color: '#f59e0b', fontWeight: 'bold' }}>
                            <CloseCircleOutlined /> 비활성화
                        </span>
                    )
                }
            >
                <div style={{ marginBottom: 24 }}>
                    <Paragraph type="secondary">
                        2단계 인증을 활성화하면 로그인 시 비밀번호 외에 추가 인증 코드가 필요합니다.
                        Google Authenticator, Microsoft Authenticator 등의 앱을 사용할 수 있습니다.
                    </Paragraph>
                </div>

                {is2FAEnabled ? (
                    <div>
                        <Alert
                            type="success"
                            showIcon
                            message="2FA가 활성화되어 있습니다"
                            description="계정이 추가적인 보안 레이어로 보호되고 있습니다."
                            style={{ marginBottom: 16 }}
                        />
                        <Button
                            danger
                            icon={<CloseCircleOutlined />}
                            onClick={() => setDisableModalVisible(true)}
                        >
                            2FA 비활성화
                        </Button>
                    </div>
                ) : (
                    <div>
                        <Alert
                            type="warning"
                            showIcon
                            icon={<ExclamationCircleOutlined />}
                            message="2FA가 비활성화되어 있습니다"
                            description="계정 보안을 위해 2단계 인증을 활성화하는 것을 권장합니다."
                            style={{ marginBottom: 16 }}
                        />
                        <Button
                            type="primary"
                            icon={<SafetyOutlined />}
                            onClick={handleStartSetup}
                            loading={setupLoading}
                            style={{ background: '#10b981', borderColor: '#10b981' }}
                        >
                            2FA 활성화
                        </Button>
                    </div>
                )}
            </Card>

            {/* Setup Modal */}
            <Modal
                title={
                    <Space>
                        <QrcodeOutlined style={{ color: '#3b82f6' }} />
                        <span>2FA 설정</span>
                    </Space>
                }
                open={setupModalVisible}
                onCancel={() => {
                    setSetupModalVisible(false);
                    setVerifyCode('');
                    setSetupStep(0);
                }}
                footer={null}
                width={500}
            >
                <Steps current={setupStep} style={{ marginBottom: 24 }}>
                    <Step title="QR 스캔" />
                    <Step title="코드 확인" />
                    <Step title="완료" />
                </Steps>

                {setupStep === 0 && setupData && (
                    <div style={{ textAlign: 'center' }}>
                        <Title level={5}>1. 인증 앱에서 QR 코드를 스캔하세요</Title>
                        <div
                            style={{
                                padding: 20,
                                background: '#f9fafb',
                                borderRadius: 12,
                                marginBottom: 16,
                            }}
                        >
                            <img
                                src={setupData.qr_code}
                                alt="2FA QR Code"
                                style={{ maxWidth: 200 }}
                            />
                        </div>

                        <Divider>또는 수동 입력</Divider>

                        <div
                            style={{
                                padding: 12,
                                background: '#f3f4f6',
                                borderRadius: 8,
                                fontFamily: 'monospace',
                                marginBottom: 16,
                            }}
                        >
                            <Text copyable={{ text: setupData.secret }}>
                                {setupData.secret}
                            </Text>
                        </div>

                        <Button type="primary" onClick={() => setSetupStep(1)}>
                            다음 →
                        </Button>
                    </div>
                )}

                {setupStep === 1 && (
                    <div style={{ textAlign: 'center' }}>
                        <Title level={5}>2. 인증 앱에서 표시된 코드를 입력하세요</Title>
                        <Input
                            size="large"
                            placeholder="000000"
                            value={verifyCode}
                            onChange={(e) => setVerifyCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                            maxLength={6}
                            style={{
                                textAlign: 'center',
                                fontSize: 24,
                                letterSpacing: 8,
                                fontFamily: 'monospace',
                                marginBottom: 16,
                            }}
                            onPressEnter={handleVerify}
                        />
                        <Space>
                            <Button onClick={() => setSetupStep(0)}>← 이전</Button>
                            <Button
                                type="primary"
                                onClick={handleVerify}
                                loading={setupLoading}
                                disabled={verifyCode.length !== 6}
                            >
                                인증하기
                            </Button>
                        </Space>
                    </div>
                )}

                {setupData?.backup_codes && setupStep === 0 && (
                    <div style={{ marginTop: 24 }}>
                        <Alert
                            type="warning"
                            message="백업 코드를 안전하게 보관하세요!"
                            description="인증 앱에 접근할 수 없을 때 이 코드로 로그인할 수 있습니다."
                            style={{ marginBottom: 12 }}
                        />
                        <div
                            style={{
                                padding: 12,
                                background: '#fffbeb',
                                border: '1px solid #fbbf24',
                                borderRadius: 8,
                            }}
                        >
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8 }}>
                                {setupData.backup_codes.map((code, idx) => (
                                    <Text key={idx} code copyable>
                                        {code}
                                    </Text>
                                ))}
                            </div>
                        </div>
                    </div>
                )}
            </Modal>

            {/* Disable Modal */}
            <Modal
                title={
                    <Space>
                        <ExclamationCircleOutlined style={{ color: '#ef4444' }} />
                        <span>2FA 비활성화</span>
                    </Space>
                }
                open={disableModalVisible}
                onCancel={() => {
                    setDisableModalVisible(false);
                    setDisableCode('');
                    setDisablePassword('');
                }}
                footer={null}
                width={400}
            >
                <Alert
                    type="warning"
                    message="보안 경고"
                    description="2FA를 비활성화하면 계정 보안이 약해집니다."
                    style={{ marginBottom: 16 }}
                />

                <div style={{ marginBottom: 16 }}>
                    <Text strong>현재 비밀번호</Text>
                    <Input.Password
                        placeholder="비밀번호"
                        value={disablePassword}
                        onChange={(e) => setDisablePassword(e.target.value)}
                        style={{ marginTop: 8 }}
                    />
                </div>

                <div style={{ marginBottom: 16 }}>
                    <Text strong>2FA 인증 코드</Text>
                    <Input
                        placeholder="000000"
                        value={disableCode}
                        onChange={(e) => setDisableCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                        maxLength={6}
                        style={{
                            marginTop: 8,
                            textAlign: 'center',
                            fontSize: 18,
                            letterSpacing: 4,
                            fontFamily: 'monospace',
                        }}
                    />
                </div>

                <Button
                    danger
                    block
                    onClick={handleDisable}
                    loading={disableLoading}
                    disabled={disableCode.length !== 6 || !disablePassword}
                >
                    2FA 비활성화
                </Button>
            </Modal>
        </>
    );
}

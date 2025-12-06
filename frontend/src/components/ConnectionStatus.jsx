import { memo } from 'react';
import { useWebSocket } from '../context/WebSocketContext';

/**
 * WebSocket 연결 상태 표시 컴포넌트
 * 화면 우측 하단에 연결 상태를 표시하고, 재연결 버튼 제공
 */
function ConnectionStatus() {
    const {
        isConnected,
        connectionState,
        retryCount,
        nextRetryIn,
        maxRetries,
        reconnect
    } = useWebSocket();

    // 연결된 상태에서는 표시하지 않음 (선택적)
    // if (isConnected) return null;

    const getStatusConfig = () => {
        switch (connectionState) {
            case 'connected':
                return {
                    icon: '🟢',
                    color: '#4caf50',
                    bgColor: 'rgba(76, 175, 80, 0.1)',
                    borderColor: '#4caf50',
                    text: '연결됨',
                    showReconnect: false,
                };
            case 'connecting':
                return {
                    icon: '🔄',
                    color: '#2196f3',
                    bgColor: 'rgba(33, 150, 243, 0.1)',
                    borderColor: '#2196f3',
                    text: '연결 중...',
                    showReconnect: false,
                };
            case 'reconnecting':
                return {
                    icon: '🔄',
                    color: '#ff9800',
                    bgColor: 'rgba(255, 152, 0, 0.1)',
                    borderColor: '#ff9800',
                    text: nextRetryIn
                        ? `재연결 중... (${nextRetryIn}초 후 시도 ${retryCount}/${maxRetries})`
                        : `재연결 중... (${retryCount}/${maxRetries})`,
                    showReconnect: true,
                };
            case 'failed':
                return {
                    icon: '❌',
                    color: '#f44336',
                    bgColor: 'rgba(244, 67, 54, 0.1)',
                    borderColor: '#f44336',
                    text: '연결 실패',
                    showReconnect: true,
                };
            case 'disconnected':
            default:
                return {
                    icon: '⚪',
                    color: '#9e9e9e',
                    bgColor: 'rgba(158, 158, 158, 0.1)',
                    borderColor: '#9e9e9e',
                    text: '연결 끊김',
                    showReconnect: true,
                };
        }
    };

    const config = getStatusConfig();

    // 연결된 상태에서는 작은 인디케이터만 표시
    if (isConnected) {
        return (
            <div
                style={{
                    position: 'fixed',
                    bottom: '20px',
                    right: '20px',
                    padding: '8px 12px',
                    background: config.bgColor,
                    border: `1px solid ${config.borderColor}`,
                    borderRadius: '20px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    fontSize: '12px',
                    fontWeight: '500',
                    color: config.color,
                    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                    zIndex: 9999,
                    transition: 'all 0.3s ease',
                }}
            >
                <span style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    background: config.color,
                    animation: 'pulse 2s infinite',
                }} />
                실시간 연결
            </div>
        );
    }

    return (
        <div
            style={{
                position: 'fixed',
                bottom: '20px',
                right: '20px',
                padding: '12px 16px',
                background: 'white',
                border: `2px solid ${config.borderColor}`,
                borderRadius: '12px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
                minWidth: '200px',
                boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                zIndex: 9999,
                animation: 'slideIn 0.3s ease',
            }}
        >
            <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
            }}>
                <span style={{ fontSize: '16px' }}>{config.icon}</span>
                <span style={{
                    fontWeight: 'bold',
                    color: config.color,
                    fontSize: '14px',
                }}>
                    {config.text}
                </span>
            </div>

            {config.showReconnect && (
                <button
                    onClick={reconnect}
                    style={{
                        padding: '8px 16px',
                        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                        color: 'white',
                        border: 'none',
                        borderRadius: '6px',
                        fontSize: '12px',
                        fontWeight: 'bold',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '6px',
                        transition: 'all 0.2s',
                    }}
                    onMouseEnter={(e) => {
                        e.currentTarget.style.transform = 'translateY(-1px)';
                        e.currentTarget.style.boxShadow = '0 4px 8px rgba(102, 126, 234, 0.3)';
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.transform = 'translateY(0)';
                        e.currentTarget.style.boxShadow = 'none';
                    }}
                >
                    🔄 지금 재연결
                </button>
            )}

            {connectionState === 'failed' && (
                <div style={{
                    fontSize: '11px',
                    color: '#666',
                    textAlign: 'center',
                }}>
                    네트워크 상태를 확인하세요
                </div>
            )}

            <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
        </div>
    );
}

export default memo(ConnectionStatus);

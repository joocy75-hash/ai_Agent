import { useState, useEffect, useContext } from 'react';
import { Badge, Dropdown, List, Button, Empty, Spin } from 'antd';
import {
    BellOutlined,
    CheckOutlined,
    DeleteOutlined,
    WarningOutlined,
    InfoCircleOutlined,
    CloseCircleOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import alertsAPI from '../api/alerts';
import { WebSocketContext } from '../context/WebSocketContext';

export default function NotificationBell() {
    const [visible, setVisible] = useState(false);
    const [notifications, setNotifications] = useState([]);
    const [unreadCount, setUnreadCount] = useState(0);
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();
    const { lastMessage } = useContext(WebSocketContext);

    useEffect(() => {
        loadNotifications();
    }, []);

    // WebSocket으로 실시간 알림 수신
    useEffect(() => {
        if (lastMessage && typeof lastMessage === 'object') {
            if (lastMessage.type === 'alert') {
                // 새 알림 추가
                setNotifications(prev => [lastMessage, ...prev].slice(0, 10));
                setUnreadCount(prev => prev + 1);
            }
        }
    }, [lastMessage]);

    const loadNotifications = async () => {
        setLoading(true);
        try {
            const [alertsData, statsData] = await Promise.all([
                alertsAPI.getAll(10, 0), // 최근 10개만 로드
                alertsAPI.getStatistics()
            ]);

            setNotifications(alertsData.alerts || []);
            setUnreadCount(statsData.unresolved_count || 0);
        } catch (error) {
            console.error('Failed to load notifications:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleMarkAsRead = async (alertId) => {
        try {
            await alertsAPI.resolve(alertId);
            setNotifications(prev =>
                prev.map(n => n.id === alertId ? { ...n, resolved: true } : n)
            );
            setUnreadCount(prev => Math.max(0, prev - 1));
        } catch (error) {
            console.error('Failed to mark as read:', error);
        }
    };

    const handleMarkAllAsRead = async () => {
        try {
            await alertsAPI.resolveAll();
            setNotifications(prev => prev.map(n => ({ ...n, resolved: true })));
            setUnreadCount(0);
        } catch (error) {
            console.error('Failed to mark all as read:', error);
        }
    };

    const handleViewAll = () => {
        setVisible(false);
        navigate('/notifications');
    };

    const getIcon = (severity) => {
        switch (severity) {
            case 'ERROR':
                return <CloseCircleOutlined style={{ color: '#f5222d', fontSize: 18 }} />;
            case 'WARNING':
                return <WarningOutlined style={{ color: '#faad14', fontSize: 18 }} />;
            case 'INFO':
                return <InfoCircleOutlined style={{ color: '#1890ff', fontSize: 18 }} />;
            default:
                return <InfoCircleOutlined style={{ color: '#52c41a', fontSize: 18 }} />;
        }
    };

    const getTimeAgo = (timestamp) => {
        const now = new Date();
        const then = new Date(timestamp);
        const diffMs = now - then;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return '방금 전';
        if (diffMins < 60) return `${diffMins}분 전`;
        if (diffHours < 24) return `${diffHours}시간 전`;
        return `${diffDays}일 전`;
    };

    const dropdownContent = (
        <div
            style={{
                width: 360,
                maxHeight: 480,
                background: '#fff',
                borderRadius: 8,
                boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                overflow: 'hidden',
            }}
        >
            {/* 헤더 */}
            <div
                style={{
                    padding: '12px 16px',
                    borderBottom: '1px solid #f0f0f0',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                }}
            >
                <span style={{ fontWeight: 'bold', fontSize: 16, color: '#fff' }}>
                    알림 ({unreadCount})
                </span>
                {unreadCount > 0 && (
                    <Button
                        type="text"
                        size="small"
                        icon={<CheckOutlined />}
                        onClick={handleMarkAllAsRead}
                        style={{ color: '#fff' }}
                    >
                        모두 읽음
                    </Button>
                )}
            </div>

            {/* 알림 목록 */}
            <div style={{ maxHeight: 360, overflowY: 'auto' }}>
                {loading ? (
                    <div style={{ padding: 40, textAlign: 'center' }}>
                        <Spin />
                    </div>
                ) : notifications.length === 0 ? (
                    <Empty
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                        description="알림이 없습니다"
                        style={{ padding: 40 }}
                    />
                ) : (
                    <List
                        dataSource={notifications}
                        renderItem={(item) => (
                            <List.Item
                                key={item.id}
                                style={{
                                    padding: '12px 16px',
                                    background: item.resolved ? '#fafafa' : '#fff',
                                    borderBottom: '1px solid #f0f0f0',
                                    cursor: 'pointer',
                                    transition: 'background 0.2s',
                                }}
                                onMouseEnter={(e) => {
                                    e.currentTarget.style.background = '#f5f5f5';
                                }}
                                onMouseLeave={(e) => {
                                    e.currentTarget.style.background = item.resolved ? '#fafafa' : '#fff';
                                }}
                            >
                                <div style={{ display: 'flex', gap: 12, width: '100%' }}>
                                    <div style={{ flexShrink: 0 }}>
                                        {getIcon(item.severity)}
                                    </div>
                                    <div style={{ flex: 1, minWidth: 0 }}>
                                        <div
                                            style={{
                                                fontSize: 14,
                                                fontWeight: item.resolved ? 'normal' : 'bold',
                                                marginBottom: 4,
                                                color: item.resolved ? '#888' : '#333',
                                                wordBreak: 'break-word',
                                            }}
                                        >
                                            {item.message}
                                        </div>
                                        <div style={{ fontSize: 12, color: '#999' }}>
                                            {getTimeAgo(item.timestamp)}
                                        </div>
                                    </div>
                                    {!item.resolved && (
                                        <Button
                                            type="text"
                                            size="small"
                                            icon={<CheckOutlined />}
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                handleMarkAsRead(item.id);
                                            }}
                                            style={{ flexShrink: 0 }}
                                        />
                                    )}
                                </div>
                            </List.Item>
                        )}
                    />
                )}
            </div>

            {/* 푸터 */}
            {notifications.length > 0 && (
                <div
                    style={{
                        padding: '12px 16px',
                        borderTop: '1px solid #f0f0f0',
                        textAlign: 'center',
                    }}
                >
                    <Button type="link" onClick={handleViewAll} block>
                        모든 알림 보기
                    </Button>
                </div>
            )}
        </div>
    );

    return (
        <Dropdown
            dropdownRender={() => dropdownContent}
            trigger={['click']}
            open={visible}
            onOpenChange={setVisible}
            placement="bottomRight"
        >
            <Badge count={unreadCount} overflowCount={99}>
                <Button
                    type="text"
                    icon={<BellOutlined style={{ fontSize: 20 }} />}
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        height: 40,
                        width: 40,
                    }}
                />
            </Badge>
        </Dropdown>
    );
}

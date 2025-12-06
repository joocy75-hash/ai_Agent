import { useEffect, useState, useContext } from 'react';
import { Card, List, Button, Badge, Select, Empty, Spin, message, Typography, Row, Col, Statistic } from 'antd';
import {
    BellOutlined,
    CheckOutlined,
    DeleteOutlined,
    WarningOutlined,
    InfoCircleOutlined,
    CloseCircleOutlined,
    ReloadOutlined,
} from '@ant-design/icons';
import alertsAPI from '../api/alerts';
import { WebSocketContext } from '../context/WebSocketContext';

const { Title } = Typography;
const { Option } = Select;

export default function Notifications() {
    const [notifications, setNotifications] = useState([]);
    const [statistics, setStatistics] = useState({});
    const [loading, setLoading] = useState(false);
    const [filter, setFilter] = useState('all'); // all, unread, ERROR, WARNING, INFO
    const { lastMessage } = useContext(WebSocketContext);

    useEffect(() => {
        loadNotifications();
    }, []);

    // WebSocket으로 실시간 알림 수신
    useEffect(() => {
        if (lastMessage && typeof lastMessage === 'object') {
            if (lastMessage.type === 'alert') {
                setNotifications(prev => [lastMessage, ...prev]);
                setStatistics(prev => ({
                    ...prev,
                    total: (prev.total || 0) + 1,
                    unresolved_count: (prev.unresolved_count || 0) + 1,
                }));
            }
        }
    }, [lastMessage]);

    const loadNotifications = async () => {
        setLoading(true);
        try {
            const [alertsData, statsData] = await Promise.all([
                alertsAPI.getAll(100, 0),
                alertsAPI.getStatistics()
            ]);

            setNotifications(alertsData.alerts || []);
            setStatistics(statsData);
        } catch (error) {
            console.error('Failed to load notifications:', error);
            message.error('알림을 불러오는데 실패했습니다');
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
            setStatistics(prev => ({
                ...prev,
                unresolved_count: Math.max(0, (prev.unresolved_count || 0) - 1)
            }));
            message.success('알림을 읽음으로 표시했습니다');
        } catch (error) {
            console.error('Failed to mark as read:', error);
            message.error('알림 처리에 실패했습니다');
        }
    };

    const handleMarkAllAsRead = async () => {
        try {
            await alertsAPI.resolveAll();
            setNotifications(prev => prev.map(n => ({ ...n, resolved: true })));
            setStatistics(prev => ({ ...prev, unresolved_count: 0 }));
            message.success('모든 알림을 읽음으로 표시했습니다');
        } catch (error) {
            console.error('Failed to mark all as read:', error);
            message.error('알림 처리에 실패했습니다');
        }
    };

    const handleClearResolved = async () => {
        try {
            await alertsAPI.clearResolved();
            setNotifications(prev => prev.filter(n => !n.resolved));
            message.success('읽은 알림을 삭제했습니다');
        } catch (error) {
            console.error('Failed to clear resolved:', error);
            message.error('알림 삭제에 실패했습니다');
        }
    };

    const getIcon = (severity) => {
        switch (severity) {
            case 'ERROR':
                return <CloseCircleOutlined style={{ color: '#f5222d', fontSize: 24 }} />;
            case 'WARNING':
                return <WarningOutlined style={{ color: '#faad14', fontSize: 24 }} />;
            case 'INFO':
                return <InfoCircleOutlined style={{ color: '#1890ff', fontSize: 24 }} />;
            default:
                return <InfoCircleOutlined style={{ color: '#52c41a', fontSize: 24 }} />;
        }
    };

    const getSeverityBadge = (severity) => {
        const colors = {
            ERROR: '#f5222d',
            WARNING: '#faad14',
            INFO: '#1890ff',
            SUCCESS: '#52c41a',
        };
        return (
            <Badge
                color={colors[severity] || colors.INFO}
                text={severity}
                style={{ fontWeight: 'bold' }}
            />
        );
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

    const filteredNotifications = notifications.filter(n => {
        if (filter === 'all') return true;
        if (filter === 'unread') return !n.resolved;
        return n.severity === filter;
    });

    return (
        <div style={{ padding: 24 }}>
            {/* 페이지 헤더 */}
            <div style={{ marginBottom: 24 }}>
                <Title level={2}>
                    <BellOutlined style={{ marginRight: 12 }} />
                    알림 센터
                </Title>
                <p style={{ color: '#888', margin: 0 }}>
                    시스템 알림과 거래 알림을 확인하세요
                </p>
            </div>

            {/* 통계 카드 */}
            <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
                <Col xs={12} sm={6}>
                    <Card>
                        <Statistic
                            title="총 알림"
                            value={statistics.total || 0}
                            prefix={<BellOutlined />}
                        />
                    </Card>
                </Col>
                <Col xs={12} sm={6}>
                    <Card>
                        <Statistic
                            title="읽지 않음"
                            value={statistics.unresolved_count || 0}
                            prefix={<BellOutlined />}
                            valueStyle={{ color: '#faad14' }}
                        />
                    </Card>
                </Col>
                <Col xs={12} sm={6}>
                    <Card>
                        <Statistic
                            title="에러"
                            value={notifications.filter(n => n.severity === 'ERROR').length}
                            prefix={<CloseCircleOutlined />}
                            valueStyle={{ color: '#f5222d' }}
                        />
                    </Card>
                </Col>
                <Col xs={12} sm={6}>
                    <Card>
                        <Statistic
                            title="경고"
                            value={notifications.filter(n => n.severity === 'WARNING').length}
                            prefix={<WarningOutlined />}
                            valueStyle={{ color: '#faad14' }}
                        />
                    </Card>
                </Col>
            </Row>

            {/* 알림 목록 */}
            <Card
                title={
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span>알림 목록</span>
                        <div style={{ display: 'flex', gap: 8 }}>
                            <Select
                                value={filter}
                                onChange={setFilter}
                                style={{ width: 120 }}
                                size="small"
                            >
                                <Option value="all">전체</Option>
                                <Option value="unread">읽지 않음</Option>
                                <Option value="ERROR">에러</Option>
                                <Option value="WARNING">경고</Option>
                                <Option value="INFO">정보</Option>
                            </Select>
                            <Button
                                size="small"
                                icon={<ReloadOutlined />}
                                onClick={loadNotifications}
                                loading={loading}
                            >
                                새로고침
                            </Button>
                            {statistics.unresolved_count > 0 && (
                                <Button
                                    size="small"
                                    type="primary"
                                    icon={<CheckOutlined />}
                                    onClick={handleMarkAllAsRead}
                                >
                                    모두 읽음
                                </Button>
                            )}
                            <Button
                                size="small"
                                danger
                                icon={<DeleteOutlined />}
                                onClick={handleClearResolved}
                            >
                                읽은 알림 삭제
                            </Button>
                        </div>
                    </div>
                }
            >
                <Spin spinning={loading}>
                    {filteredNotifications.length === 0 ? (
                        <Empty
                            image={Empty.PRESENTED_IMAGE_SIMPLE}
                            description="알림이 없습니다"
                            style={{ padding: 60 }}
                        />
                    ) : (
                        <List
                            dataSource={filteredNotifications}
                            renderItem={(item) => (
                                <List.Item
                                    key={item.id}
                                    style={{
                                        padding: 16,
                                        background: item.resolved ? '#fafafa' : '#fff',
                                        borderRadius: 8,
                                        marginBottom: 8,
                                        border: item.resolved ? '1px solid #f0f0f0' : '1px solid #e6e6e6',
                                        transition: 'all 0.3s',
                                    }}
                                    actions={[
                                        !item.resolved && (
                                            <Button
                                                type="text"
                                                icon={<CheckOutlined />}
                                                onClick={() => handleMarkAsRead(item.id)}
                                            >
                                                읽음
                                            </Button>
                                        ),
                                    ].filter(Boolean)}
                                >
                                    <List.Item.Meta
                                        avatar={getIcon(item.severity)}
                                        title={
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                                {getSeverityBadge(item.severity)}
                                                {!item.resolved && (
                                                    <Badge status="processing" text="읽지 않음" />
                                                )}
                                            </div>
                                        }
                                        description={
                                            <div>
                                                <div
                                                    style={{
                                                        fontSize: 15,
                                                        color: item.resolved ? '#888' : '#333',
                                                        fontWeight: item.resolved ? 'normal' : 'bold',
                                                        marginBottom: 8,
                                                        wordBreak: 'break-word',
                                                    }}
                                                >
                                                    {item.message}
                                                </div>
                                                <div style={{ fontSize: 13, color: '#999' }}>
                                                    {getTimeAgo(item.timestamp)} · {new Date(item.timestamp).toLocaleString('ko-KR')}
                                                </div>
                                            </div>
                                        }
                                    />
                                </List.Item>
                            )}
                            pagination={{
                                pageSize: 20,
                                showTotal: (total) => `총 ${total}개`,
                                showSizeChanger: false,
                            }}
                        />
                    )}
                </Spin>
            </Card>
        </div>
    );
}

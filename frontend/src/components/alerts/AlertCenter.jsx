import { useEffect, useState } from 'react';
import { Card, List, Tag, Button, Modal, Statistic, Row, Col, Empty, Spin } from 'antd';
import {
    BellOutlined,
    CheckCircleOutlined,
    CloseCircleOutlined,
    WarningOutlined,
    InfoCircleOutlined,
    DeleteOutlined,
    ReloadOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/ko';

dayjs.extend(relativeTime);
dayjs.locale('ko');

const API_BASE_URL = 'http://localhost:8000';

export default function AlertCenter() {
    const [alerts, setAlerts] = useState([]);
    const [statistics, setStatistics] = useState(null);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState('all'); // all, unresolved, resolved

    useEffect(() => {
        loadData();
    }, [filter]);

    const loadData = async () => {
        setLoading(true);
        try {
            const token = localStorage.getItem('token');
            if (!token) return;

            const headers = { 'Authorization': `Bearer ${token}` };

            const [alertsRes, statsRes] = await Promise.all([
                axios.get(`${API_BASE_URL}/alerts/all`, { headers }),
                axios.get(`${API_BASE_URL}/alerts/statistics`, { headers }),
            ]);

            let alertsData = alertsRes.data.alerts || [];

            // 필터 적용
            if (filter === 'unresolved') {
                alertsData = alertsData.filter(a => !a.is_resolved);
            } else if (filter === 'resolved') {
                alertsData = alertsData.filter(a => a.is_resolved);
            }

            setAlerts(alertsData);
            setStatistics(statsRes.data);
        } catch (error) {
            console.error('[AlertCenter] Error loading data:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleResolve = async (alertId) => {
        try {
            const token = localStorage.getItem('token');
            const headers = { 'Authorization': `Bearer ${token}` };

            await axios.post(`${API_BASE_URL}/alerts/resolve/${alertId}`, {}, { headers });
            loadData();
        } catch (error) {
            console.error('[AlertCenter] Error resolving alert:', error);
        }
    };

    const handleResolveAll = async () => {
        Modal.confirm({
            title: '모든 알림 해결',
            content: '모든 미해결 알림을 해결 처리하시겠습니까?',
            okText: '확인',
            cancelText: '취소',
            onOk: async () => {
                try {
                    const token = localStorage.getItem('token');
                    const headers = { 'Authorization': `Bearer ${token}` };

                    await axios.post(`${API_BASE_URL}/alerts/resolve-all`, {}, { headers });
                    loadData();
                } catch (error) {
                    console.error('[AlertCenter] Error resolving all alerts:', error);
                }
            },
        });
    };

    const handleClearResolved = async () => {
        Modal.confirm({
            title: '해결된 알림 삭제',
            content: '해결된 모든 알림을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.',
            okText: '삭제',
            cancelText: '취소',
            okType: 'danger',
            onOk: async () => {
                try {
                    const token = localStorage.getItem('token');
                    const headers = { 'Authorization': `Bearer ${token}` };

                    await axios.delete(`${API_BASE_URL}/alerts/clear-resolved`, { headers });
                    loadData();
                } catch (error) {
                    console.error('[AlertCenter] Error clearing resolved alerts:', error);
                }
            },
        });
    };

    const getAlertIcon = (level) => {
        const icons = {
            ERROR: <CloseCircleOutlined style={{ color: '#f5222d', fontSize: 20 }} />,
            WARNING: <WarningOutlined style={{ color: '#faad14', fontSize: 20 }} />,
            INFO: <InfoCircleOutlined style={{ color: '#1890ff', fontSize: 20 }} />,
        };
        return icons[level] || icons.INFO;
    };

    const getAlertColor = (level) => {
        const colors = {
            ERROR: 'red',
            WARNING: 'orange',
            INFO: 'blue',
        };
        return colors[level] || 'default';
    };

    return (
        <div style={{ padding: '24px' }}>
            <h1 style={{ fontSize: '24px', marginBottom: '24px' }}>
                <BellOutlined style={{ marginRight: '8px' }} />
                알림 센터
            </h1>

            {/* 통계 - 컴팩트 카드 */}
            {statistics && (
                <Row gutter={[8, 8]} style={{ marginBottom: '16px' }}>
                    <Col xs={12} sm={12} md={6}>
                        <div style={{
                            background: '#ffffff',
                            borderRadius: 12,
                            padding: '12px 14px',
                            border: '1px solid #f5f5f7',
                        }}>
                            <div style={{ fontSize: 11, color: '#86868b', fontWeight: 500, marginBottom: 4 }}>
                                전체 알림
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                <BellOutlined style={{ fontSize: 14, color: '#86868b' }} />
                                <span style={{ fontSize: 20, fontWeight: 600, color: '#1d1d1f' }}>
                                    {statistics.total}
                                </span>
                            </div>
                        </div>
                    </Col>
                    <Col xs={12} sm={12} md={6}>
                        <div style={{
                            background: '#ffffff',
                            borderRadius: 12,
                            padding: '12px 14px',
                            border: '1px solid #f5f5f7',
                        }}>
                            <div style={{ fontSize: 11, color: '#86868b', fontWeight: 500, marginBottom: 4 }}>
                                미해결
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                <WarningOutlined style={{ fontSize: 14, color: '#ff3b30' }} />
                                <span style={{ fontSize: 20, fontWeight: 600, color: '#ff3b30' }}>
                                    {statistics.unresolved}
                                </span>
                            </div>
                        </div>
                    </Col>
                    <Col xs={12} sm={12} md={6}>
                        <div style={{
                            background: '#ffffff',
                            borderRadius: 12,
                            padding: '12px 14px',
                            border: '1px solid #f5f5f7',
                        }}>
                            <div style={{ fontSize: 11, color: '#86868b', fontWeight: 500, marginBottom: 4 }}>
                                해결됨
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                <CheckCircleOutlined style={{ fontSize: 14, color: '#34c759' }} />
                                <span style={{ fontSize: 20, fontWeight: 600, color: '#34c759' }}>
                                    {statistics.resolved}
                                </span>
                            </div>
                        </div>
                    </Col>
                    <Col xs={12} sm={12} md={6}>
                        <div style={{
                            background: '#ffffff',
                            borderRadius: 12,
                            padding: '12px 14px',
                            border: '1px solid #f5f5f7',
                        }}>
                            <div style={{ fontSize: 11, color: '#86868b', fontWeight: 500, marginBottom: 4 }}>
                                최근 24시간
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                <BellOutlined style={{ fontSize: 14, color: '#0071e3' }} />
                                <span style={{ fontSize: 20, fontWeight: 600, color: '#1d1d1f' }}>
                                    {statistics.recent_24h}
                                </span>
                            </div>
                        </div>
                    </Col>
                </Row>
            )}

            {/* 필터 및 액션 버튼 - 컴팩트 */}
            <div style={{
                background: '#ffffff',
                borderRadius: 12,
                padding: '12px 14px',
                border: '1px solid #f5f5f7',
                marginBottom: '12px',
            }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {/* 필터 버튼 */}
                    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                        <Button
                            type={filter === 'all' ? 'primary' : 'default'}
                            onClick={() => setFilter('all')}
                            size="small"
                            style={{ borderRadius: 16, fontSize: 12 }}
                        >
                            전체
                        </Button>
                        <Button
                            type={filter === 'unresolved' ? 'primary' : 'default'}
                            onClick={() => setFilter('unresolved')}
                            size="small"
                            style={{ borderRadius: 16, fontSize: 12 }}
                        >
                            미해결
                        </Button>
                        <Button
                            type={filter === 'resolved' ? 'primary' : 'default'}
                            onClick={() => setFilter('resolved')}
                            size="small"
                            style={{ borderRadius: 16, fontSize: 12 }}
                        >
                            해결됨
                        </Button>
                    </div>

                    {/* 액션 버튼 */}
                    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                        <Button
                            icon={<ReloadOutlined />}
                            onClick={loadData}
                            size="small"
                            style={{ borderRadius: 16, fontSize: 12 }}
                        >
                            새로고침
                        </Button>
                        <Button
                            onClick={handleResolveAll}
                            size="small"
                            style={{ borderRadius: 16, fontSize: 12 }}
                        >
                            모두 해결
                        </Button>
                        <Button
                            danger
                            icon={<DeleteOutlined />}
                            onClick={handleClearResolved}
                            size="small"
                            style={{ borderRadius: 16, fontSize: 12 }}
                        >
                            해결된 알림 삭제
                        </Button>
                    </div>
                </div>
            </div>

            {/* 알림 목록 */}
            <Card>
                {loading ? (
                    <div style={{ textAlign: 'center', padding: '40px' }}>
                        <Spin size="large" />
                    </div>
                ) : alerts.length === 0 ? (
                    <Empty description="알림이 없습니다" />
                ) : (
                    <List
                        dataSource={alerts}
                        renderItem={(alert) => (
                            <List.Item
                                key={alert.id}
                                actions={[
                                    !alert.is_resolved && (
                                        <Button
                                            type="link"
                                            onClick={() => handleResolve(alert.id)}
                                        >
                                            해결
                                        </Button>
                                    ),
                                ]}
                                style={{
                                    background: alert.is_resolved ? '#f5f5f5' : 'white',
                                    opacity: alert.is_resolved ? 0.7 : 1,
                                }}
                            >
                                <List.Item.Meta
                                    avatar={getAlertIcon(alert.level)}
                                    title={
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                            <Tag color={getAlertColor(alert.level)}>{alert.level}</Tag>
                                            {alert.is_resolved && (
                                                <Tag color="green">해결됨</Tag>
                                            )}
                                            <span style={{ fontSize: '12px', color: '#888' }}>
                                                {dayjs(alert.timestamp).fromNow()}
                                            </span>
                                        </div>
                                    }
                                    description={
                                        <div style={{ marginTop: '8px' }}>
                                            {alert.message}
                                        </div>
                                    }
                                />
                            </List.Item>
                        )}
                    />
                )}
            </Card>

            {/* 레벨별 통계 */}
            {statistics && (
                <Card style={{ marginTop: '16px' }} title="레벨별 통계">
                    <Row gutter={[16, 16]}>
                        <Col span={8}>
                            <Statistic
                                title="ERROR"
                                value={statistics.by_level.ERROR}
                                valueStyle={{ color: '#f5222d' }}
                                prefix={<CloseCircleOutlined />}
                            />
                        </Col>
                        <Col span={8}>
                            <Statistic
                                title="WARNING"
                                value={statistics.by_level.WARNING}
                                valueStyle={{ color: '#faad14' }}
                                prefix={<WarningOutlined />}
                            />
                        </Col>
                        <Col span={8}>
                            <Statistic
                                title="INFO"
                                value={statistics.by_level.INFO}
                                valueStyle={{ color: '#1890ff' }}
                                prefix={<InfoCircleOutlined />}
                            />
                        </Col>
                    </Row>
                </Card>
            )}
        </div>
    );
}

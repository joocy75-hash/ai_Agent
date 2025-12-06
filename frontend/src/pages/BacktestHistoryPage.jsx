import { useState, useEffect } from 'react';
import { Card, Table, Typography, Tag, Button, Space, Tooltip, Modal, Descriptions, Statistic, Row, Col, Empty, message } from 'antd';
import {
    HistoryOutlined,
    EyeOutlined,
    DeleteOutlined,
    ReloadOutlined,
    CheckCircleOutlined,
    CloseCircleOutlined,
    LoadingOutlined,
    RiseOutlined,
    FallOutlined
} from '@ant-design/icons';
import { backtestAPI } from '../api/backtest';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

export default function BacktestHistory() {
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(false);
    const [selectedResult, setSelectedResult] = useState(null);
    const [detailModalOpen, setDetailModalOpen] = useState(false);

    useEffect(() => {
        loadHistory();
    }, []);

    const loadHistory = async () => {
        setLoading(true);
        try {
            const response = await backtestAPI.getHistory();
            setHistory(response.results || []);
        } catch (error) {
            console.error('Failed to load backtest history:', error);
            message.error('백테스트 이력을 불러오지 못했습니다');
        } finally {
            setLoading(false);
        }
    };

    const handleViewDetail = (record) => {
        setSelectedResult(record);
        setDetailModalOpen(true);
    };

    const handleDelete = async (id) => {
        Modal.confirm({
            title: '백테스트 결과 삭제',
            content: '이 백테스트 결과를 삭제하시겠습니까?',
            okText: '삭제',
            okType: 'danger',
            cancelText: '취소',
            onOk: async () => {
                try {
                    await backtestAPI.deleteResult(id);
                    message.success('삭제되었습니다');
                    loadHistory();
                } catch (error) {
                    message.error('삭제 실패');
                }
            }
        });
    };

    const getStatusTag = (status) => {
        const statusConfig = {
            completed: { color: 'success', icon: <CheckCircleOutlined />, text: '완료' },
            running: { color: 'processing', icon: <LoadingOutlined />, text: '실행 중' },
            pending: { color: 'default', icon: <LoadingOutlined />, text: '대기 중' },
            failed: { color: 'error', icon: <CloseCircleOutlined />, text: '실패' },
        };
        const config = statusConfig[status] || statusConfig.pending;
        return <Tag color={config.color} icon={config.icon}>{config.text}</Tag>;
    };

    const columns = [
        {
            title: '#',
            dataIndex: 'id',
            width: 60,
        },
        {
            title: '전략',
            dataIndex: 'strategy_name',
            render: (text, record) => text || `전략 #${record.strategy_id}`,
        },
        {
            title: '심볼',
            dataIndex: 'symbol',
            width: 100,
            render: (text) => <Tag color="blue">{text}</Tag>,
        },
        {
            title: '기간',
            render: (_, record) => (
                <span>
                    {record.start_date} ~ {record.end_date}
                </span>
            ),
        },
        {
            title: '수익률',
            dataIndex: 'total_return',
            width: 120,
            render: (value) => (
                <span style={{
                    color: value >= 0 ? '#52c41a' : '#ff4d4f',
                    fontWeight: 'bold'
                }}>
                    {value >= 0 ? <RiseOutlined /> : <FallOutlined />}
                    {' '}{value?.toFixed(2)}%
                </span>
            ),
        },
        {
            title: '거래 수',
            dataIndex: 'total_trades',
            width: 80,
            render: (value) => `${value}회`,
        },
        {
            title: '상태',
            dataIndex: 'status',
            width: 100,
            render: (status) => getStatusTag(status),
        },
        {
            title: '실행일시',
            dataIndex: 'created_at',
            width: 160,
            render: (text) => dayjs(text).format('YYYY-MM-DD HH:mm'),
        },
        {
            title: '작업',
            width: 100,
            render: (_, record) => (
                <Space>
                    <Tooltip title="상세 보기">
                        <Button
                            type="text"
                            icon={<EyeOutlined />}
                            onClick={() => handleViewDetail(record)}
                        />
                    </Tooltip>
                    <Tooltip title="삭제">
                        <Button
                            type="text"
                            danger
                            icon={<DeleteOutlined />}
                            onClick={() => handleDelete(record.id)}
                        />
                    </Tooltip>
                </Space>
            ),
        },
    ];

    return (
        <div style={{ padding: 24 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
                <div>
                    <Title level={2}>
                        <HistoryOutlined style={{ marginRight: 12 }} />
                        백테스트 이력
                    </Title>
                    <Text type="secondary">
                        지금까지 실행한 백테스트 결과를 확인하세요
                    </Text>
                </div>
                <Button
                    icon={<ReloadOutlined />}
                    onClick={loadHistory}
                    loading={loading}
                >
                    새로고침
                </Button>
            </div>

            <Card>
                <Table
                    columns={columns}
                    dataSource={history}
                    rowKey="id"
                    loading={loading}
                    locale={{
                        emptyText: (
                            <Empty
                                description="백테스트 이력이 없습니다"
                                image={Empty.PRESENTED_IMAGE_SIMPLE}
                            />
                        )
                    }}
                    pagination={{
                        pageSize: 10,
                        showSizeChanger: true,
                        showTotal: (total) => `총 ${total}개`,
                    }}
                />
            </Card>

            {/* 상세 보기 모달 */}
            <Modal
                title={
                    <span>
                        <EyeOutlined style={{ marginRight: 8 }} />
                        백테스트 상세 결과
                    </span>
                }
                open={detailModalOpen}
                onCancel={() => setDetailModalOpen(false)}
                footer={[
                    <Button key="close" onClick={() => setDetailModalOpen(false)}>
                        닫기
                    </Button>
                ]}
                width={700}
            >
                {selectedResult && (
                    <div>
                        <Row gutter={[16, 16]}>
                            <Col span={8}>
                                <Statistic
                                    title="총 수익률"
                                    value={selectedResult.total_return || 0}
                                    precision={2}
                                    suffix="%"
                                    valueStyle={{
                                        color: (selectedResult.total_return || 0) >= 0 ? '#52c41a' : '#ff4d4f'
                                    }}
                                    prefix={(selectedResult.total_return || 0) >= 0 ? <RiseOutlined /> : <FallOutlined />}
                                />
                            </Col>
                            <Col span={8}>
                                <Statistic
                                    title="최종 자금"
                                    value={selectedResult.final_balance || 0}
                                    precision={2}
                                    prefix="$"
                                />
                            </Col>
                            <Col span={8}>
                                <Statistic
                                    title="승률"
                                    value={selectedResult.win_rate || 0}
                                    precision={1}
                                    suffix="%"
                                />
                            </Col>
                        </Row>

                        <Descriptions
                            bordered
                            size="small"
                            column={2}
                            style={{ marginTop: 24 }}
                        >
                            <Descriptions.Item label="전략">
                                {selectedResult.strategy_name || `전략 #${selectedResult.strategy_id}`}
                            </Descriptions.Item>
                            <Descriptions.Item label="심볼">
                                <Tag color="blue">{selectedResult.symbol}</Tag>
                            </Descriptions.Item>
                            <Descriptions.Item label="테스트 기간">
                                {selectedResult.start_date} ~ {selectedResult.end_date}
                            </Descriptions.Item>
                            <Descriptions.Item label="타임프레임">
                                {selectedResult.timeframe}
                            </Descriptions.Item>
                            <Descriptions.Item label="초기 자금">
                                ${selectedResult.initial_balance?.toLocaleString()}
                            </Descriptions.Item>
                            <Descriptions.Item label="총 거래 수">
                                {selectedResult.total_trades}회
                            </Descriptions.Item>
                            <Descriptions.Item label="최대 손실">
                                <span style={{ color: '#ff4d4f' }}>
                                    {selectedResult.max_drawdown?.toFixed(2)}%
                                </span>
                            </Descriptions.Item>
                            <Descriptions.Item label="Profit Factor">
                                {selectedResult.profit_factor?.toFixed(2)}
                            </Descriptions.Item>
                            <Descriptions.Item label="실행 일시" span={2}>
                                {dayjs(selectedResult.created_at).format('YYYY-MM-DD HH:mm:ss')}
                            </Descriptions.Item>
                        </Descriptions>
                    </div>
                )}
            </Modal>
        </div>
    );
}

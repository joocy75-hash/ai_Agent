import { useEffect, useState } from 'react';
import { Card, Table, Tag, Button, Space, Switch, Popconfirm, message } from 'antd';
import {
    UnorderedListOutlined,
    PlusOutlined,
    EditOutlined,
    DeleteOutlined,
    PlayCircleOutlined,
    PauseCircleOutlined,
    ReloadOutlined,
} from '@ant-design/icons';

export default function StrategyList({ onEdit, onNew, onStrategiesLoaded }) {
    const [strategies, setStrategies] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        loadStrategies();
    }, []);

    const loadStrategies = async () => {
        setLoading(true);
        try {
            const token = localStorage.getItem('token');
            if (!token) {
                message.error('로그인이 필요합니다');
                setLoading(false);
                return;
            }

            // AI 생성 전략 조회
            const response = await fetch('http://localhost:8000/ai/strategies/list', {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error('Failed to fetch strategies');
            }

            const data = await response.json();

            // 전략 데이터를 테이블 형식으로 변환
            const formattedStrategies = data.strategies.map(s => ({
                id: s.id,
                name: s.name,
                description: s.description,
                type: s.type || 'TREND_FOLLOWING',
                status: s.is_active ? 'ACTIVE' : 'INACTIVE',
                symbols: [s.symbol],
                timeframe: s.timeframe,
                winRate: s.parameters?.win_rate || 0,
                totalTrades: s.parameters?.total_trades || 0,
                profit: s.parameters?.profit || 0,
                parameters: s.parameters,
            }));

            setStrategies(formattedStrategies);

            // 부모 컴포넌트에 전략 목록 전달
            if (onStrategiesLoaded) {
                onStrategiesLoaded(formattedStrategies);
            }

            setLoading(false);
        } catch (error) {
            console.error('[StrategyList] Error loading strategies:', error);
            message.error('전략 목록을 불러오는데 실패했습니다');
            setLoading(false);
        }
    };

    const generateMockStrategies = () => {
        // 가상 데이터를 빈 배열로 반환 (실제 백엔드 연동 전까지)
        return [];
    };

    const handleToggleStatus = async (strategy) => {
        try {
            const token = localStorage.getItem('token');

            // 백엔드 API 호출하여 실제로 상태 변경
            const response = await fetch(`http://localhost:8000/strategy/${strategy.id}/toggle`, {
                method: 'PATCH',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error('Failed to toggle strategy status');
            }

            const data = await response.json();
            const newStatus = data.is_active ? 'ACTIVE' : 'INACTIVE';

            // 백엔드 응답에 따라 프론트엔드 상태 업데이트
            setStrategies(strategies.map(s =>
                s.id === strategy.id ? { ...s, status: newStatus } : s
            ));

            message.success(`전략이 ${newStatus === 'ACTIVE' ? '활성화' : '비활성화'}되었습니다`);
        } catch (error) {
            console.error('[StrategyList] Error toggling status:', error);
            message.error('전략 상태 변경에 실패했습니다');
        }
    };

    const handleDelete = async (strategyId) => {
        try {
            const token = localStorage.getItem('token');

            const response = await fetch(`http://localhost:8000/ai/strategies/${strategyId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error('Failed to delete strategy');
            }

            setStrategies(strategies.filter(s => s.id !== strategyId));
            message.success('전략이 삭제되었습니다');
        } catch (error) {
            console.error('[StrategyList] Error deleting strategy:', error);
            message.error('전략 삭제에 실패했습니다');
        }
    };

    const getStatusTag = (status) => {
        const statusConfig = {
            ACTIVE: { color: 'success', text: '활성' },
            INACTIVE: { color: 'default', text: '비활성' },
            TESTING: { color: 'processing', text: '테스트' },
            ERROR: { color: 'error', text: '오류' },
        };

        const config = statusConfig[status] || statusConfig.INACTIVE;
        return <Tag color={config.color}>{config.text}</Tag>;
    };

    const getTypeTag = (type) => {
        const typeConfig = {
            TREND_FOLLOWING: { color: 'blue', text: '추세 추종' },
            MEAN_REVERSION: { color: 'purple', text: '평균 회귀' },
            BREAKOUT: { color: 'orange', text: '돌파' },
            GRID: { color: 'cyan', text: '그리드' },
            SCALPING: { color: 'magenta', text: '스캘핑' },
        };

        const config = typeConfig[type] || { color: 'default', text: type };
        return <Tag color={config.color}>{config.text}</Tag>;
    };

    const columns = [
        {
            title: '전략명',
            dataIndex: 'name',
            key: 'name',
            width: 200,
            render: (name, record) => (
                <div>
                    <div style={{ fontWeight: 'bold' }}>{name}</div>
                    <div style={{ fontSize: 12, color: '#888' }}>{record.description}</div>
                </div>
            ),
        },
        {
            title: '유형',
            dataIndex: 'type',
            key: 'type',
            width: 120,
            render: getTypeTag,
        },
        {
            title: '상태',
            dataIndex: 'status',
            key: 'status',
            width: 100,
            render: getStatusTag,
        },
        {
            title: '심볼',
            dataIndex: 'symbols',
            key: 'symbols',
            width: 180,
            render: (symbols) => (
                <div>
                    {symbols.map((symbol, index) => (
                        <Tag key={index} style={{ marginBottom: 4 }}>
                            {symbol}
                        </Tag>
                    ))}
                </div>
            ),
        },
        {
            title: '타임프레임',
            dataIndex: 'timeframe',
            key: 'timeframe',
            width: 100,
            align: 'center',
        },
        {
            title: '승률',
            dataIndex: 'winRate',
            key: 'winRate',
            width: 100,
            align: 'right',
            render: (winRate) => (
                <span style={{ color: winRate >= 60 ? '#3f8600' : winRate >= 50 ? '#faad14' : '#cf1322' }}>
                    {winRate.toFixed(1)}%
                </span>
            ),
            sorter: (a, b) => a.winRate - b.winRate,
        },
        {
            title: '거래 수',
            dataIndex: 'totalTrades',
            key: 'totalTrades',
            width: 100,
            align: 'right',
            sorter: (a, b) => a.totalTrades - b.totalTrades,
        },
        {
            title: '총 손익',
            dataIndex: 'profit',
            key: 'profit',
            width: 120,
            align: 'right',
            render: (profit) => (
                <span style={{
                    color: profit >= 0 ? '#3f8600' : '#cf1322',
                    fontWeight: 'bold',
                }}>
                    {profit >= 0 ? '+' : ''}${profit.toFixed(2)}
                </span>
            ),
            sorter: (a, b) => a.profit - b.profit,
        },
        {
            title: '작업',
            key: 'actions',
            width: 200,
            fixed: 'right',
            render: (_, record) => (
                <Space size="small">
                    <Switch
                        checked={record.status === 'ACTIVE'}
                        onChange={() => handleToggleStatus(record)}
                        checkedChildren={<PlayCircleOutlined />}
                        unCheckedChildren={<PauseCircleOutlined />}
                        size="small"
                    />
                    <Button
                        type="link"
                        icon={<EditOutlined />}
                        onClick={() => onEdit && onEdit(record)}
                        size="small"
                    >
                        편집
                    </Button>
                    <Popconfirm
                        title="전략 삭제"
                        description="정말로 이 전략을 삭제하시겠습니까?"
                        onConfirm={() => handleDelete(record.id)}
                        okText="삭제"
                        cancelText="취소"
                        okButtonProps={{ danger: true }}
                    >
                        <Button
                            type="link"
                            danger
                            icon={<DeleteOutlined />}
                            size="small"
                        >
                            삭제
                        </Button>
                    </Popconfirm>
                </Space>
            ),
        },
    ];

    return (
        <Card
            title={
                <span>
                    <UnorderedListOutlined style={{ marginRight: 8 }} />
                    전략 목록
                </span>
            }
            extra={
                <Space>
                    <Button
                        icon={<ReloadOutlined />}
                        onClick={loadStrategies}
                        loading={loading}
                        size="small"
                    >
                        새로고침
                    </Button>
                    <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={() => onNew && onNew()}
                    >
                        새 전략
                    </Button>
                </Space>
            }
        >
            <Table
                columns={columns}
                dataSource={strategies}
                rowKey="id"
                loading={loading}
                pagination={{
                    pageSize: 10,
                    showSizeChanger: true,
                    showTotal: (total) => `총 ${total}개`,
                }}
                scroll={{ x: 1200 }}
            />
        </Card>
    );
}

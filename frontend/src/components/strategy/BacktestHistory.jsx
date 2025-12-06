import { useState, useEffect } from 'react';
import { Card, Table, Button, Tag, Space, Spin, message, Tooltip, Modal } from 'antd';
import {
    HistoryOutlined,
    ReloadOutlined,
    EyeOutlined,
    DeleteOutlined,
    RiseOutlined,
    FallOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import backtestAPI from '../../api/backtest';

export default function BacktestHistory() {
    const [loading, setLoading] = useState(false);
    const [backtests, setBacktests] = useState([]);
    const [detailModalVisible, setDetailModalVisible] = useState(false);
    const [selectedBacktest, setSelectedBacktest] = useState(null);
    const navigate = useNavigate();

    useEffect(() => {
        loadBacktests();
    }, []);

    const loadBacktests = async () => {
        setLoading(true);
        try {
            const data = await backtestAPI.getAllBacktests();
            setBacktests(data.backtests || []);
        } catch (error) {
            console.error('Failed to load backtests:', error);
            message.error('백테스트 이력을 불러오는데 실패했습니다');
        } finally {
            setLoading(false);
        }
    };

    const handleViewDetail = async (record) => {
        try {
            const result = await backtestAPI.getBacktestResult(record.id);
            setSelectedBacktest(result);
            setDetailModalVisible(true);
        } catch (error) {
            console.error('Failed to load backtest detail:', error);
            message.error('백테스트 상세 정보를 불러오는데 실패했습니다');
        }
    };

    const handleCompare = () => {
        navigate('/backtest-comparison');
    };

    const getStatusTag = (status) => {
        const statusConfig = {
            completed: { color: 'success', text: '완료' },
            running: { color: 'processing', text: '실행중' },
            failed: { color: 'error', text: '실패' },
            pending: { color: 'default', text: '대기중' },
        };
        const config = statusConfig[status] || statusConfig.pending;
        return <Tag color={config.color}>{config.text}</Tag>;
    };

    const columns = [
        {
            title: 'ID',
            dataIndex: 'id',
            key: 'id',
            width: 80,
            render: (id) => <span style={{ fontFamily: 'monospace' }}>#{id}</span>,
        },
        {
            title: '전략',
            dataIndex: ['config', 'strategy_type'],
            key: 'strategy',
            width: 150,
            render: (strategy) => strategy || 'N/A',
        },
        {
            title: '심볼',
            dataIndex: ['config', 'symbol'],
            key: 'symbol',
            width: 120,
            render: (symbol) => <Tag color="blue">{symbol || 'N/A'}</Tag>,
        },
        {
            title: '기간',
            key: 'period',
            width: 200,
            render: (_, record) => {
                const start = record.config?.start_date || 'N/A';
                const end = record.config?.end_date || 'N/A';
                return (
                    <span style={{ fontSize: 12 }}>
                        {start} ~ {end}
                    </span>
                );
            },
        },
        {
            title: '초기 자본',
            dataIndex: 'initial_balance',
            key: 'initial_balance',
            width: 120,
            align: 'right',
            render: (balance) => `$${parseFloat(balance || 0).toFixed(2)}`,
        },
        {
            title: '최종 자본',
            dataIndex: 'final_balance',
            key: 'final_balance',
            width: 120,
            align: 'right',
            render: (balance, record) => {
                const initial = parseFloat(record.initial_balance || 0);
                const final = parseFloat(balance || 0);
                const isProfit = final >= initial;
                return (
                    <span style={{
                        color: isProfit ? '#52c41a' : '#f5222d',
                        fontWeight: 'bold',
                    }}>
                        {isProfit ? <RiseOutlined /> : <FallOutlined />} ${final.toFixed(2)}
                    </span>
                );
            },
        },
        {
            title: '총 수익률',
            key: 'total_return',
            width: 120,
            align: 'right',
            render: (_, record) => {
                const metrics = record.metrics || {};
                const totalReturn = metrics.total_return || 0;
                const isProfit = totalReturn >= 0;
                return (
                    <span style={{
                        color: isProfit ? '#52c41a' : '#f5222d',
                        fontWeight: 'bold',
                        fontSize: 14,
                    }}>
                        {isProfit ? '+' : ''}{totalReturn.toFixed(2)}%
                    </span>
                );
            },
        },
        {
            title: '승률',
            key: 'win_rate',
            width: 100,
            align: 'right',
            render: (_, record) => {
                const metrics = record.metrics || {};
                return `${(metrics.win_rate || 0).toFixed(1)}%`;
            },
        },
        {
            title: 'Sharpe',
            key: 'sharpe_ratio',
            width: 100,
            align: 'right',
            render: (_, record) => {
                const metrics = record.metrics || {};
                return (metrics.sharpe_ratio || 0).toFixed(2);
            },
        },
        {
            title: '상태',
            dataIndex: 'status',
            key: 'status',
            width: 100,
            align: 'center',
            render: (status) => getStatusTag(status),
        },
        {
            title: '실행 시간',
            dataIndex: 'created_at',
            key: 'created_at',
            width: 180,
            render: (date) => new Date(date).toLocaleString('ko-KR'),
        },
        {
            title: '작업',
            key: 'actions',
            width: 120,
            fixed: 'right',
            render: (_, record) => (
                <Space size="small">
                    <Tooltip title="상세 보기">
                        <Button
                            type="text"
                            icon={<EyeOutlined />}
                            onClick={() => handleViewDetail(record)}
                            size="small"
                        />
                    </Tooltip>
                </Space>
            ),
        },
    ];

    return (
        <Card
            title={
                <span>
                    <HistoryOutlined style={{ marginRight: 8 }} />
                    백테스트 실행 이력
                </span>
            }
            extra={
                <Space>
                    <Button
                        icon={<ReloadOutlined />}
                        onClick={loadBacktests}
                        loading={loading}
                    >
                        새로고침
                    </Button>
                    <Button
                        type="primary"
                        onClick={handleCompare}
                    >
                        결과 비교
                    </Button>
                </Space>
            }
        >
            <Spin spinning={loading}>
                <Table
                    columns={columns}
                    dataSource={backtests}
                    rowKey="id"
                    pagination={{
                        pageSize: 10,
                        showTotal: (total) => `총 ${total}개`,
                        showSizeChanger: false,
                    }}
                    scroll={{ x: 1400 }}
                    locale={{
                        emptyText: '백테스트 이력이 없습니다',
                    }}
                />
            </Spin>

            {/* 상세 정보 모달 */}
            <Modal
                title="백테스트 상세 결과"
                open={detailModalVisible}
                onCancel={() => setDetailModalVisible(false)}
                footer={[
                    <Button key="close" onClick={() => setDetailModalVisible(false)}>
                        닫기
                    </Button>,
                ]}
                width={800}
            >
                {selectedBacktest && (
                    <div>
                        <div style={{ marginBottom: 16 }}>
                            <strong>전략:</strong> {selectedBacktest.config?.strategy_type || 'N/A'}<br />
                            <strong>심볼:</strong> {selectedBacktest.config?.symbol || 'N/A'}<br />
                            <strong>기간:</strong> {selectedBacktest.config?.start_date} ~ {selectedBacktest.config?.end_date}<br />
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
                            <div style={{ padding: 12, background: '#f5f5f5', borderRadius: 4 }}>
                                <div style={{ fontSize: 12, color: '#888' }}>초기 자본</div>
                                <div style={{ fontSize: 18, fontWeight: 'bold' }}>
                                    ${parseFloat(selectedBacktest.initial_balance || 0).toFixed(2)}
                                </div>
                            </div>
                            <div style={{ padding: 12, background: '#f5f5f5', borderRadius: 4 }}>
                                <div style={{ fontSize: 12, color: '#888' }}>최종 자본</div>
                                <div style={{ fontSize: 18, fontWeight: 'bold' }}>
                                    ${parseFloat(selectedBacktest.final_balance || 0).toFixed(2)}
                                </div>
                            </div>
                            <div style={{ padding: 12, background: '#f5f5f5', borderRadius: 4 }}>
                                <div style={{ fontSize: 12, color: '#888' }}>총 수익률</div>
                                <div style={{
                                    fontSize: 18,
                                    fontWeight: 'bold',
                                    color: (selectedBacktest.metrics?.total_return || 0) >= 0 ? '#52c41a' : '#f5222d',
                                }}>
                                    {(selectedBacktest.metrics?.total_return || 0) >= 0 ? '+' : ''}
                                    {(selectedBacktest.metrics?.total_return || 0).toFixed(2)}%
                                </div>
                            </div>
                            <div style={{ padding: 12, background: '#f5f5f5', borderRadius: 4 }}>
                                <div style={{ fontSize: 12, color: '#888' }}>총 거래</div>
                                <div style={{ fontSize: 18, fontWeight: 'bold' }}>
                                    {selectedBacktest.metrics?.total_trades || 0}
                                </div>
                            </div>
                            <div style={{ padding: 12, background: '#f5f5f5', borderRadius: 4 }}>
                                <div style={{ fontSize: 12, color: '#888' }}>승률</div>
                                <div style={{ fontSize: 18, fontWeight: 'bold' }}>
                                    {(selectedBacktest.metrics?.win_rate || 0).toFixed(1)}%
                                </div>
                            </div>
                            <div style={{ padding: 12, background: '#f5f5f5', borderRadius: 4 }}>
                                <div style={{ fontSize: 12, color: '#888' }}>Profit Factor</div>
                                <div style={{ fontSize: 18, fontWeight: 'bold' }}>
                                    {(selectedBacktest.metrics?.profit_factor || 0).toFixed(2)}
                                </div>
                            </div>
                            <div style={{ padding: 12, background: '#f5f5f5', borderRadius: 4 }}>
                                <div style={{ fontSize: 12, color: '#888' }}>Sharpe Ratio</div>
                                <div style={{ fontSize: 18, fontWeight: 'bold' }}>
                                    {(selectedBacktest.metrics?.sharpe_ratio || 0).toFixed(2)}
                                </div>
                            </div>
                            <div style={{ padding: 12, background: '#f5f5f5', borderRadius: 4 }}>
                                <div style={{ fontSize: 12, color: '#888' }}>최대 낙폭</div>
                                <div style={{ fontSize: 18, fontWeight: 'bold', color: '#f5222d' }}>
                                    -{Math.abs(selectedBacktest.metrics?.max_drawdown || 0).toFixed(2)}%
                                </div>
                            </div>
                            <div style={{ padding: 12, background: '#f5f5f5', borderRadius: 4 }}>
                                <div style={{ fontSize: 12, color: '#888' }}>평균 수익</div>
                                <div style={{ fontSize: 18, fontWeight: 'bold', color: '#52c41a' }}>
                                    ${(selectedBacktest.metrics?.avg_profit || 0).toFixed(2)}
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </Modal>
        </Card>
    );
}

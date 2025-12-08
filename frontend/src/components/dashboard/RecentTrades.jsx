import { useEffect, useState } from 'react';
import { Card, Table, Tag } from 'antd';
import { HistoryOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function RecentTrades() {
    const [trades, setTrades] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadTrades();
        const interval = setInterval(loadTrades, 15000); // 15초마다 갱신
        return () => clearInterval(interval);
    }, []);

    const loadTrades = async () => {
        try {
            const token = localStorage.getItem('token');
            if (!token) {
                setLoading(false);
                return;
            }

            const headers = {
                'Authorization': `Bearer ${token}`,
            };

            const response = await axios.get(`${API_BASE_URL}/trades/recent-trades?limit=5`, { headers });

            // API 응답 데이터 매핑
            const tradesData = response.data.trades || [];
            const mappedTrades = tradesData.map(trade => ({
                id: trade.id,
                symbol: trade.symbol,
                side: trade.side,
                closedAt: trade.closed_at || trade.timestamp,
                pnl: parseFloat(trade.pnl || 0),
                pnlPercent: parseFloat(trade.pnl_percent || 0),
            }));

            setTrades(mappedTrades);
            setLoading(false);
        } catch (error) {
            console.error('[RecentTrades] Error loading trades:', error);
            setTrades([]);
            setLoading(false);
        }
    };

    const columns = [
        {
            title: '시간',
            dataIndex: 'closedAt',
            key: 'closedAt',
            width: 120,
            render: (time) => time ? dayjs(time).format('HH:mm:ss') : '-',
        },
        {
            title: '심볼',
            dataIndex: 'symbol',
            key: 'symbol',
            width: 120,
        },
        {
            title: '방향',
            dataIndex: 'side',
            key: 'side',
            width: 80,
            render: (side) => (
                <Tag color={side === 'BUY' ? 'green' : 'red'}>
                    {side}
                </Tag>
            ),
        },
        {
            title: '손익',
            dataIndex: 'pnl',
            key: 'pnl',
            width: 120,
            align: 'right',
            render: (pnl) => (
                <span style={{
                    color: pnl >= 0 ? '#3f8600' : '#cf1322',
                    fontWeight: 'bold',
                }}>
                    {pnl >= 0 ? '+' : ''}${pnl.toFixed(2)}
                </span>
            ),
        },
        {
            title: '수익률',
            dataIndex: 'pnlPercent',
            key: 'pnlPercent',
            width: 100,
            align: 'right',
            render: (percent) => (
                <span style={{ color: percent >= 0 ? '#3f8600' : '#cf1322' }}>
                    {percent >= 0 ? '+' : ''}{percent.toFixed(2)}%
                </span>
            ),
        },
    ];

    // 통계 계산
    const stats = {
        total: trades.length,
        winning: trades.filter(t => t.pnl > 0).length,
        losing: trades.filter(t => t.pnl < 0).length,
        totalPnL: trades.reduce((sum, t) => sum + t.pnl, 0),
    };

    return (
        <Card
            title={
                <span>
                    <HistoryOutlined style={{ marginRight: 8 }} />
                    최근 거래 (최근 5개)
                </span>
            }
            extra={
                stats.total > 0 ? (
                    <div style={{ fontSize: 14 }}>
                        <span style={{ marginRight: 16 }}>
                            승: <span style={{ color: '#3f8600', fontWeight: 'bold' }}>{stats.winning}</span>
                        </span>
                        <span style={{ marginRight: 16 }}>
                            패: <span style={{ color: '#cf1322', fontWeight: 'bold' }}>{stats.losing}</span>
                        </span>
                        <span>
                            합계: <span style={{
                                color: stats.totalPnL >= 0 ? '#3f8600' : '#cf1322',
                                fontWeight: 'bold',
                            }}>
                                {stats.totalPnL >= 0 ? '+' : ''}${stats.totalPnL.toFixed(2)}
                            </span>
                        </span>
                    </div>
                ) : null
            }
            size="small"
        >
            <Table
                columns={columns}
                dataSource={trades}
                rowKey="id"
                loading={loading}
                pagination={false}
                size="small"
                locale={{
                    emptyText: '최근 거래 내역이 없습니다',
                }}
            />
        </Card>
    );
}

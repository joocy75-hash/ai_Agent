import { useEffect, useState } from 'react';
import { Card, Table, Tag, Badge } from 'antd';
import { LineChartOutlined, RiseOutlined, FallOutlined } from '@ant-design/icons';
import useWebSocket from '../../hooks/useWebSocket';

export default function RealtimePrices() {
    const [prices, setPrices] = useState({});
    const { isConnected, lastMessage, subscribe, unsubscribe } = useWebSocket(
        localStorage.getItem('userId')
    );

    useEffect(() => {
        // 가격 채널 구독
        subscribe(['price']);

        return () => {
            unsubscribe(['price']);
        };
    }, [subscribe, unsubscribe]);

    useEffect(() => {
        if (lastMessage && lastMessage.type === 'price_update') {
            const { symbol, price, timestamp } = lastMessage;

            setPrices(prev => {
                const prevPrice = prev[symbol]?.price || price;
                const change = price - prevPrice;
                const changePercent = prevPrice > 0 ? (change / prevPrice) * 100 : 0;

                return {
                    ...prev,
                    [symbol]: {
                        price,
                        change,
                        changePercent,
                        timestamp,
                        trend: change > 0 ? 'up' : change < 0 ? 'down' : 'neutral',
                    },
                };
            });
        }
    }, [lastMessage]);

    const columns = [
        {
            title: '심볼',
            dataIndex: 'symbol',
            key: 'symbol',
            width: 150,
            render: (symbol) => <strong>{symbol}</strong>,
        },
        {
            title: '현재가',
            dataIndex: 'price',
            key: 'price',
            width: 150,
            align: 'right',
            render: (price, record) => (
                <span style={{
                    color: record.trend === 'up' ? '#3f8600' : record.trend === 'down' ? '#cf1322' : '#000',
                    fontWeight: 'bold',
                    fontSize: 16,
                }}>
                    ${price.toFixed(2)}
                </span>
            ),
        },
        {
            title: '변동',
            dataIndex: 'change',
            key: 'change',
            width: 120,
            align: 'right',
            render: (change, record) => (
                <span style={{ color: change >= 0 ? '#3f8600' : '#cf1322' }}>
                    {change >= 0 ? <RiseOutlined /> : <FallOutlined />}
                    {' '}
                    {change >= 0 ? '+' : ''}{change.toFixed(2)}
                </span>
            ),
        },
        {
            title: '변동률',
            dataIndex: 'changePercent',
            key: 'changePercent',
            width: 100,
            align: 'right',
            render: (percent) => (
                <Tag color={percent >= 0 ? 'green' : 'red'}>
                    {percent >= 0 ? '+' : ''}{percent.toFixed(2)}%
                </Tag>
            ),
        },
    ];

    const dataSource = Object.entries(prices).map(([symbol, data]) => ({
        key: symbol,
        symbol,
        ...data,
    }));

    return (
        <Card
            title={
                <span>
                    <LineChartOutlined style={{ marginRight: 8 }} />
                    실시간 가격
                    <Badge
                        status={isConnected ? 'success' : 'error'}
                        text={isConnected ? '연결됨' : '연결 끊김'}
                        style={{ marginLeft: 16 }}
                    />
                </span>
            }
            size="small"
        >
            <Table
                columns={columns}
                dataSource={dataSource}
                pagination={false}
                size="small"
                locale={{
                    emptyText: '실시간 가격 데이터를 기다리는 중...',
                }}
            />
        </Card>
    );
}

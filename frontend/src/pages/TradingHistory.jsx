import { useState, useEffect } from 'react';
import { Card, Table, Button, Input, Select, DatePicker, Space, Tag, Statistic, Row, Col, message, Typography, Tooltip } from 'antd';
import {
    HistoryOutlined,
    ReloadOutlined,
    DownloadOutlined,
    SearchOutlined,
    FilterOutlined,
    RiseOutlined,
    FallOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { orderAPI } from '../api/order';

const { Title } = Typography;
const { RangePicker } = DatePicker;
const { Option } = Select;

export default function TradingHistory() {
    // 화면 크기 감지
    const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

    useEffect(() => {
        const handleResize = () => setIsMobile(window.innerWidth < 768);
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    const [loading, setLoading] = useState(false);
    const [orders, setOrders] = useState([]);
    const [filteredOrders, setFilteredOrders] = useState([]);
    const [searchText, setSearchText] = useState('');
    const [filterSide, setFilterSide] = useState('all');
    const [filterStatus, setFilterStatus] = useState('all');
    const [dateRange, setDateRange] = useState(null);
    const [statistics, setStatistics] = useState({
        total: 0,
        buy: 0,
        sell: 0,
        totalProfit: 0,
        totalLoss: 0,
    });

    useEffect(() => {
        loadOrders();
    }, []);

    useEffect(() => {
        applyFilters();
    }, [orders, searchText, filterSide, filterStatus, dateRange]);

    const loadOrders = async () => {
        setLoading(true);
        try {
            const response = await orderAPI.getOrderHistory(500, 0);
            console.log('[TradingHistory] API response:', response);

            // API 응답 형식에 맞게 데이터 파싱
            // 백엔드는 trades 배열과 pagination 객체를 반환
            const ordersData = response.trades || response.orders || [];

            // 데이터 형식 변환 (백엔드 응답 → 프론트엔드 형식)
            const formattedOrders = ordersData.map(order => ({
                order_id: order.id?.toString() || order.order_id || `order_${Date.now()}`,
                symbol: order.symbol || order.pair || 'Unknown',
                side: order.side?.toLowerCase() || 'unknown',
                status: order.status?.toLowerCase() || 'filled',
                price: parseFloat(order.entry || order.price || 0),
                amount: parseFloat(order.size || order.amount || order.qty || 0),
                profit: parseFloat(order.pnl?.replace(/[+%]/g, '') || 0),
                fee: parseFloat(order.fee || 0),
                timestamp: order.time || order.timestamp || new Date().toISOString(),
            }));

            setOrders(formattedOrders);
            calculateStatistics(formattedOrders);

            if (formattedOrders.length === 0) {
                message.info('거래 내역이 없습니다');
            }
        } catch (error) {
            console.error('Failed to load orders:', error);

            // 더 구체적인 에러 메시지
            if (error.response?.status === 404) {
                message.warning('거래 내역이 없습니다');
                setOrders([]);
            } else if (error.response?.status === 401) {
                message.error('로그인이 필요합니다');
            } else {
                message.error('거래 내역을 불러오는데 실패했습니다: ' + (error.response?.data?.detail || error.message));
            }
        } finally {
            setLoading(false);
        }
    };

    const calculateStatistics = (ordersData) => {
        const stats = {
            total: ordersData.length,
            long: ordersData.filter(o => o.side === 'long' || o.side === 'buy').length,
            short: ordersData.filter(o => o.side === 'short' || o.side === 'sell').length,
            totalProfit: ordersData
                .filter(o => o.profit > 0)
                .reduce((sum, o) => sum + o.profit, 0),
            totalLoss: ordersData
                .filter(o => o.profit < 0)
                .reduce((sum, o) => sum + Math.abs(o.profit), 0),
        };
        setStatistics(stats);
    };

    const applyFilters = () => {
        let filtered = [...orders];

        // 텍스트 검색
        if (searchText) {
            filtered = filtered.filter(order =>
                order.symbol?.toLowerCase().includes(searchText.toLowerCase()) ||
                order.order_id?.toLowerCase().includes(searchText.toLowerCase())
            );
        }

        // Side 필터 (long/short 또는 buy/sell 모두 지원)
        if (filterSide !== 'all') {
            filtered = filtered.filter(order => {
                if (filterSide === 'long') {
                    return order.side === 'long' || order.side === 'buy';
                } else if (filterSide === 'short') {
                    return order.side === 'short' || order.side === 'sell';
                }
                return order.side === filterSide;
            });
        }

        // Status 필터
        if (filterStatus !== 'all') {
            filtered = filtered.filter(order => order.status === filterStatus);
        }

        // 날짜 범위 필터
        if (dateRange && dateRange[0] && dateRange[1]) {
            const startDate = dateRange[0].startOf('day');
            const endDate = dateRange[1].endOf('day');
            filtered = filtered.filter(order => {
                const orderDate = dayjs(order.timestamp);
                return orderDate.isAfter(startDate) && orderDate.isBefore(endDate);
            });
        }

        setFilteredOrders(filtered);
    };

    const exportToCSV = () => {
        if (filteredOrders.length === 0) {
            message.warning('내보낼 데이터가 없습니다');
            return;
        }

        const headers = ['주문 ID', '심볼', '방향', '상태', '가격', '수량', '실현 손익', '수수료', '시간'];
        const rows = filteredOrders.map(order => [
            order.order_id || 'N/A',
            order.symbol || 'N/A',
            order.side || 'N/A',
            order.status || 'N/A',
            order.price || 0,
            order.amount || 0,
            order.profit || 0,
            order.fee || 0,
            new Date(order.timestamp).toLocaleString('ko-KR'),
        ]);

        const csvContent = [
            headers.join(','),
            ...rows.map(row => row.join(','))
        ].join('\n');

        const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `trading-history-${Date.now()}.csv`;
        a.click();
        URL.revokeObjectURL(url);

        message.success('CSV 파일이 다운로드되었습니다');
    };

    const handleResetFilters = () => {
        setSearchText('');
        setFilterSide('all');
        setFilterStatus('all');
        setDateRange(null);
    };

    const columns = [
        {
            title: '주문 ID',
            dataIndex: 'order_id',
            key: 'order_id',
            width: 150,
            render: (id) => (
                <Tooltip title={id}>
                    <span style={{ fontFamily: 'monospace', fontSize: 12 }}>
                        {id ? `${id.substring(0, 8)}...` : 'N/A'}
                    </span>
                </Tooltip>
            ),
        },
        {
            title: '심볼',
            dataIndex: 'symbol',
            key: 'symbol',
            width: 120,
            render: (symbol) => <Tag color="blue">{symbol || 'N/A'}</Tag>,
        },
        {
            title: '포지션',
            dataIndex: 'side',
            key: 'side',
            width: 100,
            align: 'center',
            render: (side) => {
                const isLong = side === 'long' || side === 'buy';
                return (
                    <Tag color={isLong ? 'green' : 'red'}>
                        {isLong ? <RiseOutlined /> : <FallOutlined />} {isLong ? 'LONG' : 'SHORT'}
                    </Tag>
                );
            },
        },
        {
            title: '상태',
            dataIndex: 'status',
            key: 'status',
            width: 100,
            align: 'center',
            render: (status) => {
                const colors = {
                    filled: 'success',
                    partial: 'processing',
                    cancelled: 'default',
                    open: 'warning',
                };
                return <Tag color={colors[status] || 'default'}>{status || 'N/A'}</Tag>;
            },
        },
        {
            title: '가격',
            dataIndex: 'price',
            key: 'price',
            width: 120,
            align: 'right',
            render: (price) => `$${parseFloat(price || 0).toFixed(2)}`,
        },
        {
            title: '수량',
            dataIndex: 'amount',
            key: 'amount',
            width: 100,
            align: 'right',
            render: (amount) => parseFloat(amount || 0).toFixed(4),
        },
        {
            title: '실현 손익',
            dataIndex: 'profit',
            key: 'profit',
            width: 120,
            align: 'right',
            render: (profit) => {
                const isProfit = profit > 0;
                return (
                    <span style={{
                        color: isProfit ? '#52c41a' : profit < 0 ? '#f5222d' : '#666',
                        fontWeight: 'bold',
                    }}>
                        {isProfit ? '+' : ''}${parseFloat(profit || 0).toFixed(2)}
                    </span>
                );
            },
        },
        {
            title: '수수료',
            dataIndex: 'fee',
            key: 'fee',
            width: 100,
            align: 'right',
            render: (fee) => `$${parseFloat(fee || 0).toFixed(2)}`,
        },
        {
            title: '시간',
            dataIndex: 'timestamp',
            key: 'timestamp',
            width: 180,
            render: (timestamp) => (
                <span style={{ fontSize: 12 }}>
                    {new Date(timestamp).toLocaleString('ko-KR')}
                </span>
            ),
        },
    ];

    return (
        <div style={{ maxWidth: 1400, margin: '0 auto' }}>
            {/* 페이지 헤더 */}
            <div style={{ marginBottom: isMobile ? 12 : 24 }}>
                <Title level={isMobile ? 3 : 2}>
                    <HistoryOutlined style={{ marginRight: 8 }} />
                    거래 내역
                </Title>
                {!isMobile && (
                    <p style={{ color: '#888', margin: 0 }}>
                        전체 주문 이력을 조회하고 분석하세요
                    </p>
                )}
            </div>

            {/* 통계 카드 */}
            <Row gutter={isMobile ? [8, 8] : [16, 16]} style={{ marginBottom: isMobile ? 12 : 24 }}>
                <Col xs={12} sm={6}>
                    <Card>
                        <Statistic
                            title="총 거래"
                            value={statistics.total}
                            prefix={<HistoryOutlined />}
                        />
                    </Card>
                </Col>
                <Col xs={12} sm={6}>
                    <Card>
                        <Statistic
                            title="롱 진입"
                            value={statistics.long}
                            valueStyle={{ color: '#52c41a' }}
                            prefix={<RiseOutlined />}
                        />
                    </Card>
                </Col>
                <Col xs={12} sm={6}>
                    <Card>
                        <Statistic
                            title="숏 진입"
                            value={statistics.short}
                            valueStyle={{ color: '#f5222d' }}
                            prefix={<FallOutlined />}
                        />
                    </Card>
                </Col>
                <Col xs={12} sm={6}>
                    <Card>
                        <Statistic
                            title="순손익"
                            value={statistics.totalProfit - statistics.totalLoss}
                            precision={2}
                            prefix="$"
                            valueStyle={{
                                color: (statistics.totalProfit - statistics.totalLoss) >= 0 ? '#52c41a' : '#f5222d',
                            }}
                        />
                    </Card>
                </Col>
            </Row>

            {/* 필터 및 검색 */}
            <Card style={{ marginBottom: isMobile ? 12 : 24 }}>
                <Space direction="vertical" style={{ width: '100%' }} size="middle">
                    <Row gutter={isMobile ? [8, 8] : [16, 16]}>
                        <Col xs={24} sm={12} md={8}>
                            <Input
                                placeholder="심볼 또는 주문 ID 검색"
                                prefix={<SearchOutlined />}
                                value={searchText}
                                onChange={(e) => setSearchText(e.target.value)}
                                allowClear
                            />
                        </Col>
                        <Col xs={12} sm={6} md={4}>
                            <Select
                                style={{ width: '100%' }}
                                value={filterSide}
                                onChange={setFilterSide}
                                placeholder="방향"
                            >
                                <Option value="all">전체 포지션</Option>
                                <Option value="long">롱 (Long)</Option>
                                <Option value="short">숏 (Short)</Option>
                            </Select>
                        </Col>
                        <Col xs={12} sm={6} md={4}>
                            <Select
                                style={{ width: '100%' }}
                                value={filterStatus}
                                onChange={setFilterStatus}
                                placeholder="상태"
                            >
                                <Option value="all">전체 상태</Option>
                                <Option value="filled">체결</Option>
                                <Option value="partial">부분 체결</Option>
                                <Option value="cancelled">취소</Option>
                                <Option value="open">대기</Option>
                            </Select>
                        </Col>
                        <Col xs={24} sm={12} md={8}>
                            <RangePicker
                                style={{ width: '100%' }}
                                value={dateRange}
                                onChange={setDateRange}
                                format="YYYY-MM-DD"
                                placeholder={['시작일', '종료일']}
                            />
                        </Col>
                    </Row>

                    <Space>
                        <Button
                            icon={<FilterOutlined />}
                            onClick={handleResetFilters}
                        >
                            필터 초기화
                        </Button>
                        <Button
                            icon={<ReloadOutlined />}
                            onClick={loadOrders}
                            loading={loading}
                        >
                            새로고침
                        </Button>
                        <Button
                            type="primary"
                            icon={<DownloadOutlined />}
                            onClick={exportToCSV}
                            disabled={filteredOrders.length === 0}
                        >
                            CSV 내보내기
                        </Button>
                    </Space>
                </Space>
            </Card>

            {/* 거래 내역 테이블 */}
            <Card>
                <Table
                    columns={columns}
                    dataSource={filteredOrders}
                    rowKey={(record) => record.order_id || record.timestamp}
                    loading={loading}
                    pagination={{
                        pageSize: 20,
                        showTotal: (total) => `총 ${total}개`,
                        showSizeChanger: true,
                        pageSizeOptions: ['10', '20', '50', '100'],
                    }}
                    scroll={{ x: 1200 }}
                    locale={{
                        emptyText: '거래 내역이 없습니다',
                    }}
                />
            </Card>
        </div>
    );
}

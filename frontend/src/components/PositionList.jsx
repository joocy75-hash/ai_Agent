import { useState, useEffect, memo, useCallback, useRef } from 'react';
import { Modal, Descriptions, Tag, Badge, Table, Button, Space, Typography, Card } from 'antd';
import {
    CloseOutlined,
    ReloadOutlined,
    WarningOutlined,
    LineChartOutlined,
    ArrowUpOutlined,
    ArrowDownOutlined
} from '@ant-design/icons';
import { accountAPI } from '../api/account';
import { orderAPI } from '../api/order';
import { bitgetAPI } from '../api/bitget';
import { useWebSocket } from '../context/WebSocketContext';

const { Text } = Typography;

// 코인별 색상 맵
const coinColors = {
    'BTC': '#F7931A', 'ETH': '#627EEA', 'BNB': '#F3BA2F', 'XRP': '#23292F',
    'SOL': '#9945FF', 'ADA': '#0033AD', 'DOGE': '#C2A633', 'DOT': '#E6007A',
    'MATIC': '#8247E5', 'SHIB': '#FFA409', 'LTC': '#345D9D', 'AVAX': '#E84142',
    'LINK': '#2A5ADA', 'UNI': '#FF007A', 'ATOM': '#2E3148', 'OP': '#FF0420',
    'ARB': '#28A0F0', 'SUI': '#4DA2FF', 'PEPE': '#479F53', 'WIF': '#E8B931',
    'BONK': '#F8A628', 'INJ': '#00F2FE', 'SEI': '#9B1C1C', 'TIA': '#7B2BF9',
    'JUP': '#00C2A8', 'APT': '#000000', 'FTM': '#1969FF', 'NEAR': '#000000'
};

// 코인 아이콘 컴포넌트
const CoinIcon = memo(({ symbol }) => {
    const [imgSrc, setImgSrc] = useState(null);
    const [loadAttempt, setLoadAttempt] = useState(0);
    const coin = symbol?.replace('USDT', '').replace('_UMCBL', '').toLowerCase();
    const coinUpper = coin?.toUpperCase();

    const iconSources = [
        `https://cdn.jsdelivr.net/gh/spothq/cryptocurrency-icons@master/128/color/${coin}.png`,
        `https://assets.coincap.io/assets/icons/${coin}@2x.png`,
        `https://cdn.jsdelivr.net/gh/spothq/cryptocurrency-icons@master/32/color/${coin}.png`,
    ];

    useEffect(() => {
        setLoadAttempt(0);
        if (iconSources.length > 0) {
            setImgSrc(iconSources[0]);
        }
    }, [coin]);

    const handleError = () => {
        const nextAttempt = loadAttempt + 1;
        if (nextAttempt < iconSources.length) {
            setLoadAttempt(nextAttempt);
            setImgSrc(iconSources[nextAttempt]);
        } else {
            setImgSrc(null);
        }
    };

    if (!imgSrc) {
        const bgColor = coinColors[coinUpper] || '#667eea';
        return (
            <div style={{
                width: 28,
                height: 28,
                borderRadius: '50%',
                background: bgColor,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '11px',
                fontWeight: '700',
                color: '#fff',
                flexShrink: 0
            }}>
                {coinUpper?.substring(0, 2)}
            </div>
        );
    }

    return (
        <img
            src={imgSrc}
            alt={coinUpper}
            style={{
                width: 28,
                height: 28,
                borderRadius: '50%',
                flexShrink: 0,
                objectFit: 'cover'
            }}
            onError={handleError}
        />
    );
});

CoinIcon.displayName = 'CoinIcon';

function PositionList({ currentPrices: propCurrentPrices = {}, onPositionClosed }) {
    const [positions, setPositions] = useState([]);
    const [loading, setLoading] = useState(false); // 초기 로딩 상태 false로 변경
    const [initialLoading, setInitialLoading] = useState(true); // 첫 로딩만 표시
    const [closingPositionId, setClosingPositionId] = useState(null);
    const [panicClosing, setPanicClosing] = useState(false);
    const [useBitget, setUseBitget] = useState(true);
    const [localPrices, setLocalPrices] = useState({});
    const [selectedPosition, setSelectedPosition] = useState(null);
    const [detailModalOpen, setDetailModalOpen] = useState(false);
    const { subscribe, isConnected } = useWebSocket();

    const prevPositionsRef = useRef(null);
    const isLoadingRef = useRef(false); // 중복 로딩 방지
    const currentPrices = { ...localPrices, ...propCurrentPrices };

    const fetchCurrentPrices = useCallback(async (symbols) => {
        if (!symbols || symbols.length === 0) return;

        const uniqueSymbols = [...new Set(symbols)];
        const priceUpdates = {};

        await Promise.all(
            uniqueSymbols.map(async (symbol) => {
                try {
                    const ticker = await bitgetAPI.getTicker(symbol);
                    if (ticker && ticker.last) {
                        priceUpdates[symbol] = parseFloat(ticker.last);
                    }
                } catch (err) {
                    // 조용히 실패 처리
                }
            })
        );

        if (Object.keys(priceUpdates).length > 0) {
            setLocalPrices(prev => {
                const newPrices = { ...prev, ...priceUpdates };
                // 변경이 없으면 업데이트 하지 않음
                if (JSON.stringify(prev) === JSON.stringify(newPrices)) {
                    return prev;
                }
                return newPrices;
            });
        }
    }, []);

    const loadPositions = useCallback(async (showLoading = false) => {
        // 중복 로딩 방지
        if (isLoadingRef.current) return;
        isLoadingRef.current = true;

        if (showLoading) setLoading(true);

        try {
            if (useBitget) {
                try {
                    const data = await bitgetAPI.getPositions();

                    const formattedPositions = (data.positions || []).map(pos => {
                        const size = parseFloat(pos.total || pos.available || 0);
                        const entryPrice = parseFloat(pos.averageOpenPrice || pos.openPriceAvg || 0);
                        const marketPrice = parseFloat(pos.marketPrice || pos.markPrice || 0);
                        const unrealizedPnl = parseFloat(pos.unrealizedPL || pos.unrealizedPnl || 0);
                        const leverage = parseInt(pos.leverage || 1);
                        const margin = parseFloat(pos.margin || 0);
                        const side = (pos.holdSide || pos.posSide || 'long').toLowerCase();

                        let liquidationPrice = parseFloat(pos.liquidationPrice || pos.liqPx || 0);
                        if (!liquidationPrice && entryPrice > 0 && leverage > 0) {
                            const maintenanceMarginRate = 0.005;
                            const takerFee = 0.0006;
                            if (side === 'long' || side === 'buy') {
                                liquidationPrice = entryPrice * (1 - (1 / leverage - maintenanceMarginRate - takerFee));
                            } else {
                                liquidationPrice = entryPrice * (1 + (1 / leverage - maintenanceMarginRate - takerFee));
                            }
                        }

                        let pnlPercent = 0;
                        if (margin > 0) {
                            pnlPercent = (unrealizedPnl / margin) * 100;
                        } else if (entryPrice > 0 && size > 0) {
                            const positionValue = entryPrice * size / leverage;
                            pnlPercent = (unrealizedPnl / positionValue) * 100;
                        }

                        return {
                            id: pos.positionId || `${pos.symbol}-${side}`,
                            symbol: pos.symbol || pos.instId,
                            side: side,
                            size: size,
                            entry_price: entryPrice,
                            market_price: marketPrice,
                            liquidation_price: liquidationPrice,
                            unrealized_pnl: unrealizedPnl,
                            pnl_percent: pnlPercent,
                            leverage: leverage,
                            margin: margin,
                            margin_mode: pos.marginMode || 'cross',
                            created_at: pos.cTime ? new Date(parseInt(pos.cTime)).toISOString() : null,
                        };
                    }).filter(pos => pos.size > 0);

                    // 데이터가 실제로 변경되었을 때만 업데이트
                    const newDataStr = JSON.stringify(formattedPositions);
                    if (prevPositionsRef.current !== newDataStr) {
                        prevPositionsRef.current = newDataStr;
                        setPositions(formattedPositions);
                    }

                    return;
                } catch (bitgetError) {
                    console.warn('[PositionList] Bitget API failed:', bitgetError);
                    setUseBitget(false);
                }
            }

            const data = await accountAPI.getPositions();
            const positionsList = Array.isArray(data) ? data : (data.data || []);

            const newDataStr = JSON.stringify(positionsList);
            if (prevPositionsRef.current !== newDataStr) {
                prevPositionsRef.current = newDataStr;
                setPositions(positionsList);
            }

        } catch (err) {
            console.error('[PositionList] Error loading positions:', err);
        } finally {
            isLoadingRef.current = false;
            setLoading(false);
            setInitialLoading(false);
        }
    }, [useBitget]);

    // 초기 로딩
    useEffect(() => {
        loadPositions(true);
    }, []);

    // 자동 새로고침 (별도 useEffect로 분리하여 의존성 문제 해결)
    useEffect(() => {
        const interval = setInterval(() => {
            loadPositions(false); // 조용한 새로고침
        }, 60000);
        return () => clearInterval(interval);
    }, [loadPositions]);

    // WebSocket 실시간 포지션 업데이트 구독
    useEffect(() => {
        if (!isConnected) return;

        const unsubscribe = subscribe('position_update', (data) => {
            if (data.data) {
                const updatedPosition = data.data;

                setPositions(prevPositions => {
                    const existingIndex = prevPositions.findIndex(
                        p => p.symbol === updatedPosition.symbol && p.side === updatedPosition.side
                    );

                    if (updatedPosition.contracts === 0 || updatedPosition.size === 0) {
                        return prevPositions.filter((_, idx) => idx !== existingIndex);
                    }

                    const newPosition = {
                        id: `${updatedPosition.symbol}-${updatedPosition.side}`,
                        symbol: updatedPosition.symbol,
                        side: updatedPosition.side,
                        size: parseFloat(updatedPosition.contracts || updatedPosition.size || 0),
                        entry_price: parseFloat(updatedPosition.entryPrice || 0),
                        unrealized_pnl: parseFloat(updatedPosition.unrealizedPnl || 0),
                        market_price: parseFloat(updatedPosition.marketPrice || 0)
                    };

                    if (existingIndex >= 0) {
                        const updated = [...prevPositions];
                        updated[existingIndex] = { ...updated[existingIndex], ...newPosition };
                        return updated;
                    } else {
                        return [...prevPositions, newPosition];
                    }
                });
            }
        });

        return unsubscribe;
    }, [isConnected, subscribe]);

    const getCurrentPrice = (position) => {
        return position.market_price || currentPrices[position.symbol] || 0;
    };

    const calculatePnL = (position) => {
        if (position.unrealized_pnl !== undefined && position.unrealized_pnl !== 0) {
            return position.unrealized_pnl;
        }

        const currentPrice = getCurrentPrice(position);
        if (!currentPrice || !position.entry_price) return 0;

        const entryPrice = parseFloat(position.entry_price);
        const size = parseFloat(position.size);
        const side = position.side.toLowerCase();

        if (side === 'long' || side === 'buy') {
            return (currentPrice - entryPrice) * size;
        } else {
            return (entryPrice - currentPrice) * size;
        }
    };

    const calculatePnLPercent = (position) => {
        if (position.pnl_percent !== undefined && position.pnl_percent !== 0) {
            return position.pnl_percent;
        }

        const pnl = calculatePnL(position);
        const entryPrice = parseFloat(position.entry_price);
        const size = parseFloat(position.size);
        const leverage = parseFloat(position.leverage || 1);

        if (entryPrice > 0 && size > 0) {
            const positionValue = (entryPrice * size) / leverage;
            return (pnl / positionValue) * 100;
        }
        return 0;
    };

    const calculateLiquidationPrice = (position) => {
        if (position.liquidation_price && position.liquidation_price > 0) {
            return position.liquidation_price;
        }

        const entryPrice = parseFloat(position.entry_price);
        const leverage = parseFloat(position.leverage || 1);
        const side = position.side.toLowerCase();

        if (!entryPrice || leverage <= 0) return null;

        const maintenanceMarginRate = 0.005;
        const takerFee = 0.0006;

        if (side === 'long' || side === 'buy') {
            return entryPrice * (1 - (1 / leverage - maintenanceMarginRate - takerFee));
        } else {
            return entryPrice * (1 + (1 / leverage - maintenanceMarginRate - takerFee));
        }
    };

    const handleOpenDetail = (position) => {
        setSelectedPosition(position);
        setDetailModalOpen(true);
    };

    const handleCloseDetail = () => {
        setDetailModalOpen(false);
        setSelectedPosition(null);
    };

    const handlePanicClose = async () => {
        if (positions.length === 0) {
            Modal.warning({ title: '청산할 포지션이 없습니다.' });
            return;
        }

        Modal.confirm({
            title: '⚠️ 모든 포지션 긴급 청산',
            content: (
                <div>
                    <p>총 {positions.length}개의 포지션이 청산됩니다.</p>
                    <p>이 작업은 취소할 수 없습니다. 계속하시겠습니까?</p>
                </div>
            ),
            okText: '긴급 청산',
            okType: 'danger',
            cancelText: '취소',
            onOk: async () => {
                setPanicClosing(true);
                try {
                    let successCount = 0;
                    let failCount = 0;

                    const closePromises = positions.map(async (position) => {
                        try {
                            if (useBitget) {
                                await bitgetAPI.closePosition(position.symbol, position.side, null);
                            } else {
                                await orderAPI.closePosition(position.id, position.symbol, position.side);
                            }
                            successCount++;
                        } catch (err) {
                            failCount++;
                        }
                    });

                    await Promise.all(closePromises);

                    Modal.info({
                        title: '긴급 청산 완료',
                        content: (
                            <div>
                                <p>✅ 성공: {successCount}개</p>
                                <p>❌ 실패: {failCount}개</p>
                            </div>
                        )
                    });

                    await loadPositions(true);

                    if (onPositionClosed) {
                        onPositionClosed({ panic_close: true, success: successCount, failed: failCount });
                    }
                } catch (err) {
                    Modal.error({ title: '긴급 청산 중 오류가 발생했습니다.' });
                } finally {
                    setPanicClosing(false);
                }
            }
        });
    };

    const handleClosePosition = async (position) => {
        Modal.confirm({
            title: '포지션 청산',
            content: `${position.symbol} ${position.side.toUpperCase()} 포지션을 청산하시겠습니까?`,
            okText: '청산',
            okType: 'danger',
            cancelText: '취소',
            onOk: async () => {
                setClosingPositionId(position.id);
                try {
                    let result;
                    if (useBitget) {
                        try {
                            result = await bitgetAPI.closePosition(position.symbol, position.side, null);
                            await loadPositions(true);
                            if (onPositionClosed) onPositionClosed(result);
                            return;
                        } catch (bitgetError) {
                            // fallback
                        }
                    }

                    result = await orderAPI.closePosition(position.id, position.symbol, position.side);
                    if (result.status === 'filled') {
                        await loadPositions(true);
                        if (onPositionClosed) onPositionClosed(result);
                    } else {
                        Modal.error({ title: '청산 실패', content: `상태: ${result.status}` });
                    }
                } catch (err) {
                    Modal.error({ title: '청산 오류', content: err.response?.data?.detail || '포지션 청산에 실패했습니다.' });
                } finally {
                    setClosingPositionId(null);
                }
            }
        });
    };

    const columns = [
        {
            title: <span style={{ fontSize: '14px', fontWeight: '600', color: '#1d1d1f' }}>심볼</span>,
            dataIndex: 'symbol',
            key: 'symbol',
            render: (text) => (
                <Space>
                    <CoinIcon symbol={text} />
                    <span style={{ fontSize: '15px', fontWeight: '700', color: '#1d1d1f' }}>
                        {text.replace('USDT', '')}
                    </span>
                </Space>
            ),
        },
        {
            title: <span style={{ fontSize: '14px', fontWeight: '600', color: '#1d1d1f' }}>방향</span>,
            dataIndex: 'side',
            key: 'side',
            render: (side) => {
                const isLong = side.toLowerCase() === 'long' || side.toLowerCase() === 'buy';
                return (
                    <Tag
                        color={isLong ? '#52c41a' : '#ff4d4f'}
                        style={{
                            fontSize: '13px',
                            fontWeight: '600',
                            padding: '4px 12px',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: 4,
                            borderRadius: 6
                        }}
                    >
                        {isLong ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
                        {isLong ? 'LONG' : 'SHORT'}
                    </Tag>
                );
            },
        },
        {
            title: <span style={{ fontSize: '14px', fontWeight: '600', color: '#1d1d1f' }}>진입가</span>,
            dataIndex: 'entry_price',
            key: 'entry_price',
            align: 'right',
            render: (price) => (
                <span style={{ fontSize: '14px', fontWeight: '500', color: '#1d1d1f', fontFamily: 'SF Mono, Monaco, Consolas, monospace' }}>
                    ${parseFloat(price).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
            ),
        },
        {
            title: <span style={{ fontSize: '14px', fontWeight: '600', color: '#1d1d1f' }}>현재가</span>,
            key: 'market_price',
            align: 'right',
            render: (_, record) => {
                const price = getCurrentPrice(record);
                return (
                    <span style={{ fontSize: '14px', fontWeight: '600', color: '#1d1d1f', fontFamily: 'SF Mono, Monaco, Consolas, monospace' }}>
                        {price > 0 ? `$${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '-'}
                    </span>
                );
            },
        },
        {
            title: <span style={{ fontSize: '14px', fontWeight: '600', color: '#1d1d1f' }}>청산가</span>,
            key: 'liquidation_price',
            align: 'right',
            render: (_, record) => {
                const price = calculateLiquidationPrice(record);
                return (
                    <span style={{ fontSize: '14px', fontWeight: '500', color: '#ff4d4f', fontFamily: 'SF Mono, Monaco, Consolas, monospace' }}>
                        {price ? `$${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '-'}
                    </span>
                );
            },
        },
        {
            title: <span style={{ fontSize: '14px', fontWeight: '600', color: '#1d1d1f' }}>수량</span>,
            dataIndex: 'size',
            key: 'size',
            align: 'right',
            render: (size) => (
                <span style={{ fontSize: '14px', fontWeight: '500', color: '#434343' }}>
                    {parseFloat(size).toFixed(4)}
                </span>
            ),
        },
        {
            title: <span style={{ fontSize: '14px', fontWeight: '600', color: '#1d1d1f' }}>손익</span>,
            key: 'pnl',
            align: 'right',
            render: (_, record) => {
                const pnl = calculatePnL(record);
                const pnlPercent = calculatePnLPercent(record);
                const isPositive = pnl >= 0;
                const color = isPositive ? '#52c41a' : '#ff4d4f';
                return (
                    <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: '15px', fontWeight: '700', color }}>
                            {isPositive ? '+' : ''}{pnl.toFixed(2)} USDT
                        </div>
                        <div style={{ fontSize: '13px', fontWeight: '600', color }}>
                            {isPositive ? '+' : ''}{pnlPercent.toFixed(2)}%
                        </div>
                    </div>
                );
            },
        },
        {
            title: <span style={{ fontSize: '14px', fontWeight: '600', color: '#1d1d1f' }}>작업</span>,
            key: 'action',
            align: 'center',
            render: (_, record) => (
                <Button
                    danger
                    size="small"
                    onClick={(e) => {
                        e.stopPropagation();
                        handleClosePosition(record);
                    }}
                    loading={closingPositionId === record.id}
                    icon={<CloseOutlined />}
                    style={{ fontSize: '13px', fontWeight: '500' }}
                >
                    청산
                </Button>
            ),
        },
    ];

    return (
        <Card
            title={
                <Space>
                    <LineChartOutlined style={{ fontSize: '18px' }} />
                    <span style={{ fontSize: '16px', fontWeight: '700', color: '#1d1d1f' }}>현재 포지션</span>
                    <Badge count={positions.length} style={{ backgroundColor: '#52c41a' }} />
                </Space>
            }
            extra={
                <Space>
                    <Button
                        danger
                        type="primary"
                        icon={<WarningOutlined />}
                        onClick={handlePanicClose}
                        disabled={positions.length === 0 || panicClosing}
                        loading={panicClosing}
                        style={{ fontWeight: '500' }}
                    >
                        Panic Close
                    </Button>
                    <Button
                        icon={<ReloadOutlined />}
                        onClick={() => loadPositions(true)}
                        loading={loading}
                        style={{ fontWeight: '500' }}
                    >
                        새로고침
                    </Button>
                </Space>
            }
            style={{ marginBottom: 24, boxShadow: '0 2px 8px rgba(0,0,0,0.05)' }}
            styles={{ body: { padding: 0 } }}
        >
            <Table
                dataSource={positions}
                columns={columns}
                rowKey="id"
                pagination={false}
                loading={initialLoading}
                onRow={(record) => ({
                    onClick: () => handleOpenDetail(record),
                    style: { cursor: 'pointer' },
                })}
                locale={{ emptyText: <span style={{ fontSize: '14px', color: '#86868b' }}>현재 열린 포지션이 없습니다.</span> }}
                size="middle"
            />

            {/* Position Detail Modal */}
            <Modal
                title={
                    <Space>
                        <LineChartOutlined />
                        <Text strong style={{ fontSize: '16px' }}>{selectedPosition?.symbol?.replace('USDT', '/USDT')} 상세 정보</Text>
                        {selectedPosition && (
                            <Tag color={(selectedPosition.side?.toLowerCase() === 'long' || selectedPosition.side?.toLowerCase() === 'buy') ? 'success' : 'error'}>
                                {(selectedPosition.side?.toLowerCase() === 'long' || selectedPosition.side?.toLowerCase() === 'buy') ? 'LONG' : 'SHORT'}
                            </Tag>
                        )}
                    </Space>
                }
                open={detailModalOpen}
                onCancel={handleCloseDetail}
                footer={[
                    <Button
                        key="close"
                        danger
                        type="primary"
                        onClick={(e) => {
                            e.stopPropagation();
                            if (selectedPosition) handleClosePosition(selectedPosition);
                            handleCloseDetail();
                        }}
                    >
                        포지션 청산
                    </Button>,
                    <Button key="cancel" onClick={handleCloseDetail}>
                        닫기
                    </Button>
                ]}
                width={700}
            >
                {selectedPosition && (() => {
                    const pos = selectedPosition;
                    const pnl = calculatePnL(pos);
                    const pnlPercent = calculatePnLPercent(pos);
                    const currentPrice = getCurrentPrice(pos);
                    const liquidationPrice = calculateLiquidationPrice(pos);
                    const entryPrice = parseFloat(pos.entry_price || 0);
                    const size = parseFloat(pos.size || 0);
                    const leverage = parseFloat(pos.leverage || 1);
                    const margin = parseFloat(pos.margin || 0);
                    const stake = margin > 0 ? margin : (entryPrice * size / leverage);

                    return (
                        <Space direction="vertical" size="large" style={{ width: '100%' }}>
                            <Descriptions title="기본 정보" bordered size="small" column={2}>
                                <Descriptions.Item label="심볼">{pos.symbol?.replace('USDT', '')}</Descriptions.Item>
                                <Descriptions.Item label="진입 시간">{pos.created_at ? new Date(pos.created_at).toLocaleString('ko-KR') : '-'}</Descriptions.Item>
                                <Descriptions.Item label="투자금">{stake.toFixed(3)} USDT</Descriptions.Item>
                                <Descriptions.Item label="수량">{size.toFixed(4)}</Descriptions.Item>
                                <Descriptions.Item label="진입가">${entryPrice.toFixed(4)}</Descriptions.Item>
                                <Descriptions.Item label="현재가">${currentPrice > 0 ? currentPrice.toFixed(4) : '-'}</Descriptions.Item>
                                <Descriptions.Item label="총 손익" span={2}>
                                    <Text type={pnlPercent >= 0 ? 'success' : 'danger'} strong style={{ fontSize: '15px' }}>
                                        {pnlPercent >= 0 ? '+' : ''}{pnlPercent.toFixed(2)}% ({pnl >= 0 ? '+' : ''}{pnl.toFixed(3)} USDT)
                                    </Text>
                                </Descriptions.Item>
                            </Descriptions>

                            <Descriptions title="리스크 정보" bordered size="small" column={2}>
                                <Descriptions.Item label="레버리지">{leverage}x</Descriptions.Item>
                                <Descriptions.Item label="청산가">
                                    <Text type="danger">${liquidationPrice ? liquidationPrice.toFixed(4) : '-'}</Text>
                                </Descriptions.Item>
                                <Descriptions.Item label="마진 모드">{pos.margin_mode}</Descriptions.Item>
                            </Descriptions>
                        </Space>
                    );
                })()}
            </Modal>
        </Card>
    );
}

export default memo(PositionList);

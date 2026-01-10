/**
 * BotManagement Page
 *
 * 다중 봇 관리 페이지 - AI 봇 + 그리드 봇 통합 관리
 *
 * 기능:
 * - 탭 기반 봇 타입 분류 (AI 추세 / 그리드)
 * - 봇 목록 카드 그리드 표시
 * - 잔고 할당 시각화 바
 * - 전체 봇 시작/중지
 * - 봇 생성/수정/삭제
 * - 봇별 상세 통계
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import {
    Row,
    Col,
    Typography,
    Button,
    Space,
    message,
    Card,
    Statistic,
    Tabs,
    Spin,
    Badge,
} from 'antd';
import {
    RobotOutlined,
    PlayCircleOutlined,
    PauseCircleOutlined,
    ReloadOutlined,
    DashboardOutlined,
    TrophyOutlined,
    RiseOutlined,
    FallOutlined,
    ThunderboltOutlined,
    LineChartOutlined,
} from '@ant-design/icons';

import botInstancesAPI from '../api/botInstances';
import multibotAPI from '../api/multibot';
// import { useStrategies } from '../context/StrategyContext';  // 템플릿 컴셉으로 사용 안함

// AI 봇 컴포넌트
// import AllocationBar from '../components/bot/AllocationBar';  // 잔고 할당 숨김
import BotCard from '../components/bot/BotCard';
// import AddBotCard from '../components/bot/AddBotCard';  // 새봇추가 숨김
import BotStatsModal from '../components/bot/BotStatsModal';
import EditBotModal from '../components/bot/EditBotModal';

// 그리드 봇 컴포넌트
import GridBotCard from '../components/grid/GridBotCard';
import CreateGridBotModal from '../components/grid/CreateGridBotModal';
import { GridBotTabs } from '../components/grid';  // 그리드 템플릿 컴포넌트

// AI 추세 봇 컴포넌트
import { TrendBotTabs } from '../components/trend';  // AI 추세 템플릿 컴포넌트

// 전략 선택 컴포넌트 - 숨김 처리됨
// import SimpleStrategyCreator from '../components/strategy/SimpleStrategyCreator';

const { Title, Text } = Typography;

export default function BotManagement() {
    // State
    const [bots, setBots] = useState([]);
    const [totalAllocation, setTotalAllocation] = useState(0);
    const [availableAllocation, setAvailableAllocation] = useState(100);
    const [runningCount, setRunningCount] = useState(0);
    const [loading, setLoading] = useState(false);
    const [actionLoading, setActionLoading] = useState(false);
    const [activeTab, setActiveTab] = useState('ai_trend');  // 기본 탭: AI 추세

    // 전략 컨텍스트 - 템플릿 컴셉으로 사용 안함
    // const { getActiveStrategies } = useStrategies();
    // const strategies = getActiveStrategies();

    // 모달 상태
    const [statsModal, setStatsModal] = useState({ open: false, botId: null, botName: null });
    const [editModal, setEditModal] = useState({ open: false, bot: null });
    const [gridBotModal, setGridBotModal] = useState({ open: false, bot: null });

    // 통계 요약
    const [summary, setSummary] = useState(null);

    // 화면 크기 감지
    const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

    useEffect(() => {
        const handleResize = () => setIsMobile(window.innerWidth < 768);
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    // 봇 필터링 (전체 탭 삭제됨)
    const filteredBots = useMemo(() => {
        if (activeTab === 'ai_trend') return bots.filter((b) => b.bot_type === 'ai_trend');
        if (activeTab === 'grid') return bots.filter((b) => b.bot_type === 'grid');
        return bots;
    }, [bots, activeTab]);

    // AI 봇과 그리드 봇 카운트
    const botCounts = useMemo(() => {
        const aiCount = bots.filter((b) => b.bot_type === 'ai_trend').length;
        const gridCount = bots.filter((b) => b.bot_type === 'grid').length;
        const aiRunning = bots.filter((b) => b.bot_type === 'ai_trend' && b.is_running).length;
        const gridRunning = bots.filter((b) => b.bot_type === 'grid' && b.is_running).length;
        return { aiCount, gridCount, aiRunning, gridRunning };
    }, [bots]);

    // 봇 목록 로드
    const loadBots = useCallback(async () => {
        setLoading(true);
        try {
            const response = await botInstancesAPI.list();
            setBots(response.bots || []);
            setTotalAllocation(response.total_allocation || 0);
            setAvailableAllocation(response.available_allocation || 100);
            setRunningCount(response.running_count || 0);
        } catch (err) {
            console.error('봇 목록 로드 실패:', err);
            message.error('봇 목록을 불러오지 못했습니다');
        } finally {
            setLoading(false);
        }
    }, []);

    // 통계 요약 로드 (멀티봇 API v2.0)
    const loadSummary = useCallback(async () => {
        try {
            const response = await multibotAPI.getSummary();
            // 멀티봇 API 응답을 기존 형식에 맞게 매핑
            setSummary({
                total_bots: response.active_bot_count,
                running_bots: response.bots?.filter(b => b.is_running).length || 0,
                total_pnl: response.total_pnl,
                total_pnl_percent: response.total_pnl_percent,
                overall_win_rate: response.bots?.length > 0
                    ? response.bots.reduce((sum, b) => sum + (b.win_rate || 0), 0) / response.bots.length
                    : 0,
                // 잔고 정보 추가 (v2.0)
                total_balance: response.total_balance,
                used_amount: response.used_amount,
                available_amount: response.available_amount,
                max_bot_count: response.max_bot_count,
            });
            // 사용 가능 잔고 업데이트
            setAvailableAllocation(response.available_amount || 0);
        } catch (err) {
            console.error('통계 요약 로드 실패:', err);
            // 폴백: 기존 API 시도
            try {
                const fallback = await botInstancesAPI.getSummary();
                setSummary(fallback);
            } catch {
                // 둘 다 실패
            }
        }
    }, []);

    // 초기 로드
    useEffect(() => {
        loadBots();
        loadSummary();
    }, [loadBots, loadSummary]);

    // 봇 생성
    const handleCreateBot = async (data) => {
        await botInstancesAPI.create(data);
        await loadBots();
    };

    // 봇 시작
    const handleStartBot = async (botId) => {
        const response = await botInstancesAPI.start(botId);
        message.success(response.message || '봇이 시작되었습니다');
        await loadBots();
    };

    // 봇 중지
    const handleStopBot = async (botId) => {
        const response = await botInstancesAPI.stop(botId);
        message.success(response.message || '봇이 중지되었습니다');
        await loadBots();
    };

    // 봇 수정
    const handleUpdateBot = async (botId, data) => {
        await botInstancesAPI.update(botId, data);
        await loadBots();
    };

    // 봇 삭제
    const handleDeleteBot = async (botId) => {
        await botInstancesAPI.delete(botId);
        await loadBots();
    };

    // 전체 시작
    const handleStartAll = async () => {
        setActionLoading(true);
        try {
            const response = await botInstancesAPI.startAll();
            message.success(response.message || '모든 봇이 시작되었습니다');
            await loadBots();
        } catch (err) {
            message.error(err.response?.data?.detail || '전체 시작 실패');
        } finally {
            setActionLoading(false);
        }
    };

    // 전체 중지
    const handleStopAll = async () => {
        setActionLoading(true);
        try {
            const response = await botInstancesAPI.stopAll();
            message.success(response.message || '모든 봇이 중지되었습니다');
            await loadBots();
        } catch (err) {
            message.error(err.response?.data?.detail || '전체 중지 실패');
        } finally {
            setActionLoading(false);
        }
    };

    // PNL 포맷
    const formatPnl = (value) => {
        if (!value || value === 0) return '$0';
        const formatted = Math.abs(value).toFixed(2);
        return value >= 0 ? `+$${formatted}` : `-$${formatted}`;
    };

    // 탭 아이템 (전략 선택 탭 숨김)
    const tabItems = [
        {
            key: 'ai_trend',
            label: (
                <Space>
                    <ThunderboltOutlined style={{ color: '#5856d6' }} />
                    AI 추세
                    <Badge
                        count={botCounts.aiCount}
                        style={{ backgroundColor: '#5856d6' }}
                    />
                </Space>
            ),
        },
        {
            key: 'grid',
            label: (
                <Space>
                    <LineChartOutlined style={{ color: '#34c759' }} />
                    그리드
                    <Badge
                        count={botCounts.gridCount}
                        style={{ backgroundColor: '#34c759' }}
                    />
                </Space>
            ),
        },
    ];

    // 봇 카드 렌더링
    const renderBotCard = (bot) => {
        if (bot.bot_type === 'grid') {
            return (
                <GridBotCard
                    key={bot.id}
                    bot={bot}
                    onStart={handleStartBot}
                    onStop={handleStopBot}
                    onEdit={(bot) => setGridBotModal({ open: true, bot })}
                    onDelete={handleDeleteBot}
                    onViewDetail={(botId) =>
                        setStatsModal({
                            open: true,
                            botId,
                            botName: bots.find((b) => b.id === botId)?.name,
                        })
                    }
                />
            );
        }

        return (
            <BotCard
                key={bot.id}
                bot={bot}
                onStart={handleStartBot}
                onStop={handleStopBot}
                onEdit={(bot) => setEditModal({ open: true, bot })}
                onDelete={handleDeleteBot}
                onViewStats={(botId) =>
                    setStatsModal({
                        open: true,
                        botId,
                        botName: bots.find((b) => b.id === botId)?.name,
                    })
                }
            />
        );
    };

    return (
        <div
            style={{
                maxWidth: 1400,
                margin: '0 auto',
                padding: isMobile ? '16px' : '24px 32px',
            }}
        >
            {/* Page Header */}
            <div
                style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    flexWrap: 'wrap',
                    gap: 16,
                    marginBottom: 24,
                }}
            >
                <div>
                    <Title
                        level={isMobile ? 3 : 2}
                        style={{
                            marginBottom: 4,
                            color: '#1d1d1f',
                            display: 'flex',
                            alignItems: 'center',
                            gap: 10,
                        }}
                    >
                        <RobotOutlined style={{ color: '#0071e3' }} />
                        봇 관리
                    </Title>
                    <Text style={{ color: '#86868b' }}>
                        AI 추세 봇과 그리드 봇을 생성하고 관리하세요
                    </Text>
                </div>

                {/* 전체 제어 버튼 */}
                <Space wrap>
                    <Button
                        icon={<ReloadOutlined />}
                        onClick={() => {
                            loadBots();
                            loadSummary();
                        }}
                        loading={loading}
                        style={{
                            borderRadius: 8,
                        }}
                    >
                        {!isMobile && '새로고침'}
                    </Button>
                    {runningCount > 0 ? (
                        <Button
                            danger
                            icon={<PauseCircleOutlined />}
                            onClick={handleStopAll}
                            loading={actionLoading}
                            style={{
                                borderRadius: 8,
                                fontWeight: 600,
                            }}
                        >
                            전체 중지
                        </Button>
                    ) : (
                        <Button
                            type="primary"
                            icon={<PlayCircleOutlined />}
                            onClick={handleStartAll}
                            loading={actionLoading}
                            disabled={bots.length === 0}
                            style={{
                                background: '#34c759',
                                border: 'none',
                                borderRadius: 8,
                                fontWeight: 600,
                            }}
                        >
                            전체 시작
                        </Button>
                    )}
                </Space>
            </div>

            {/* 통계 요약 카드 */}
            <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
                <Col xs={12} sm={6}>
                    <Card
                        style={{
                            background: '#ffffff',
                            border: '1px solid #f5f5f7',
                            borderRadius: 12,
                        }}
                        styles={{ body: { padding: '16px 20px' } }}
                    >
                        <Statistic
                            title={
                                <Text
                                    style={{
                                        color: '#86868b',
                                        fontSize: 12,
                                    }}
                                >
                                    총 봇
                                </Text>
                            }
                            value={summary?.total_bots || bots.length}
                            suffix={
                                <Text
                                    style={{
                                        color: '#86868b',
                                        fontSize: 12,
                                    }}
                                >
                                    개
                                </Text>
                            }
                            valueStyle={{ color: '#1d1d1f', fontSize: 24, fontWeight: 700 }}
                            prefix={
                                <DashboardOutlined
                                    style={{ color: '#0071e3', marginRight: 8 }}
                                />
                            }
                        />
                    </Card>
                </Col>
                <Col xs={12} sm={6}>
                    <Card
                        style={{
                            background: '#ffffff',
                            border: '1px solid #f5f5f7',
                            borderRadius: 12,
                        }}
                        styles={{ body: { padding: '16px 20px' } }}
                    >
                        <Statistic
                            title={
                                <Text
                                    style={{
                                        color: '#86868b',
                                        fontSize: 12,
                                    }}
                                >
                                    실행 중
                                </Text>
                            }
                            value={summary?.running_bots || runningCount}
                            suffix={
                                <Text
                                    style={{
                                        color: '#86868b',
                                        fontSize: 12,
                                    }}
                                >
                                    개
                                </Text>
                            }
                            valueStyle={{ color: '#34c759', fontSize: 24, fontWeight: 700 }}
                            prefix={
                                <ThunderboltOutlined
                                    style={{ color: '#34c759', marginRight: 8 }}
                                />
                            }
                        />
                    </Card>
                </Col>
                <Col xs={12} sm={6}>
                    <Card
                        style={{
                            background: '#ffffff',
                            border: '1px solid #f5f5f7',
                            borderRadius: 12,
                        }}
                        styles={{ body: { padding: '16px 20px' } }}
                    >
                        <Statistic
                            title={
                                <Text
                                    style={{
                                        color: '#86868b',
                                        fontSize: 12,
                                    }}
                                >
                                    총 손익
                                </Text>
                            }
                            value={formatPnl(summary?.total_pnl || 0)}
                            valueStyle={{
                                color:
                                    (summary?.total_pnl || 0) >= 0 ? '#34c759' : '#ff3b30',
                                fontSize: 24,
                                fontWeight: 700,
                            }}
                            prefix={
                                (summary?.total_pnl || 0) >= 0 ? (
                                    <RiseOutlined
                                        style={{ color: '#34c759', marginRight: 8 }}
                                    />
                                ) : (
                                    <FallOutlined
                                        style={{ color: '#ff3b30', marginRight: 8 }}
                                    />
                                )
                            }
                        />
                    </Card>
                </Col>
                <Col xs={12} sm={6}>
                    <Card
                        style={{
                            background: '#ffffff',
                            border: '1px solid #f5f5f7',
                            borderRadius: 12,
                        }}
                        styles={{ body: { padding: '16px 20px' } }}
                    >
                        <Statistic
                            title={
                                <Text
                                    style={{
                                        color: '#86868b',
                                        fontSize: 12,
                                    }}
                                >
                                    평균 승률
                                </Text>
                            }
                            value={summary?.overall_win_rate?.toFixed(1) || '0.0'}
                            suffix="%"
                            valueStyle={{
                                color:
                                    (summary?.overall_win_rate || 0) >= 50
                                        ? '#34c759'
                                        : '#ff3b30',
                                fontSize: 24,
                                fontWeight: 700,
                            }}
                            prefix={
                                <TrophyOutlined
                                    style={{ color: '#ff9500', marginRight: 8 }}
                                />
                            }
                        />
                    </Card>
                </Col>
            </Row>

            {/* 잔고 할당 시각화 - 숨김 (관리자 템플릿 컴셉 사용) */}
            {/* <AllocationBar bots={bots} totalAllocation={totalAllocation} /> */}

            {/* 탭 기반 봇 목록 */}
            <Tabs
                activeKey={activeTab}
                onChange={setActiveTab}
                items={tabItems}
                style={{ marginBottom: 16 }}
                tabBarStyle={{
                    borderBottom: '1px solid #f5f5f7',
                    marginBottom: 24,
                }}
                tabBarExtraContent={null}  // 수동 봇 추가 버튼 숨김 (템플릿 컴셉 사용)
            />

            {/* 봇 카드 그리드 */}
            <Spin spinning={loading}>
                {/* AI 추세 탭: AI 추천 템플릿 */}
                {activeTab === 'ai_trend' && (
                    <TrendBotTabs
                        availableBalance={availableAllocation}
                        onBotCreated={() => {
                            loadBots();
                            loadSummary();
                        }}
                    />
                )}
                {/* 그리드 탭 */}
                {activeTab === 'grid' && (
                    <GridBotTabs
                        gridBots={bots.filter(b => b.bot_type === 'grid')}
                        onStartBot={handleStartBot}
                        onStopBot={handleStopBot}
                        onEditBot={(bot) => setGridBotModal({ open: true, bot })}
                        onDeleteBot={handleDeleteBot}
                        onCreateBot={() => setGridBotModal({ open: true, bot: null })}
                        onViewDetail={(botId) =>
                            setStatsModal({
                                open: true,
                                botId,
                                botName: bots.find((b) => b.id === botId)?.name,
                            })
                        }
                        availableAllocation={availableAllocation}
                        onRefresh={loadBots}
                    />
                )}
            </Spin>

            {/* AI 봇 통계 모달 */}
            <BotStatsModal
                botId={statsModal.botId}
                botName={statsModal.botName}
                open={statsModal.open}
                onClose={() =>
                    setStatsModal({ open: false, botId: null, botName: null })
                }
            />

            {/* AI 봇 편집 모달 */}
            <EditBotModal
                bot={editModal.bot}
                strategies={[]}  // 템플릿 컴셉으로 사용 안함
                maxAllocation={availableAllocation}
                open={editModal.open}
                onClose={() => setEditModal({ open: false, bot: null })}
                onUpdate={handleUpdateBot}
            />

            {/* 그리드 봇 생성/편집 모달 */}
            <CreateGridBotModal
                open={gridBotModal.open}
                onClose={() => setGridBotModal({ open: false, bot: null })}
                onSuccess={() => {
                    loadBots();
                    loadSummary();
                }}
                maxAllocation={availableAllocation}
                editBot={gridBotModal.bot}
            />
        </div>
    );
}

/**
 * BotMarketplace - 봇 마켓플레이스 메인 컨테이너
 *
 * Bitget 스타일 다크 테마 봇 선택 페이지
 */
import { useEffect, useState } from 'react';
import { message, Spin, Empty, Alert } from 'antd';
import { RobotOutlined, SettingOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useBotMarketplace } from '../../hooks/useBotMarketplace';
import BotCardList from './BotCardList';
import BotFilters from './BotFilters';
import ActiveBotsBanner from './ActiveBotsBanner';
import BotDetailModal from './BotDetailModal';
import './styles/BotMarketplace.css';

const BotMarketplace = () => {
    const navigate = useNavigate();
    const {
        templates,
        summary,
        loading,
        error,
        availableSymbols,
        sortBy,
        setSortBy,
        filterSymbol,
        setFilterSymbol,
        selectedTemplate,
        detailModalOpen,
        loadTemplates,
        loadSummary,
        startBot,
        selectTemplate,
        closeDetailModal,
    } = useBotMarketplace();

    // API 키 미설정 상태
    const [apiKeyMissing, setApiKeyMissing] = useState(false);

    // 초기 데이터 로드
    useEffect(() => {
        const fetchData = async () => {
            // 템플릿은 필수, summary는 선택 (API 키 없어도 템플릿은 볼 수 있음)
            try {
                await loadTemplates();
            } catch (err) {
                message.error('템플릿을 불러오는데 실패했습니다.');
            }

            // Summary 로드 시도 (실패해도 페이지는 정상 표시)
            try {
                await loadSummary();
                setApiKeyMissing(false);
            } catch (err) {
                // API 키 미설정 시 400 에러
                if (err.response?.status === 400) {
                    setApiKeyMissing(true);
                    console.log('[BotMarketplace] API key not configured - summary skipped');
                }
            }
        };
        fetchData();
    }, [loadTemplates, loadSummary]);

    // 봇 시작 핸들러
    const handleStartBot = async (templateId, amount) => {
        try {
            const result = await startBot(templateId, amount);
            if (result.success) {
                message.success('봇이 시작되었습니다!');
                closeDetailModal();
                // 데이터 새로고침
                await loadSummary();
            } else {
                message.error(result.message || '봇 시작에 실패했습니다.');
            }
        } catch (err) {
            message.error(err.message || '봇 시작에 실패했습니다.');
        }
    };

    // 에러 상태
    if (error) {
        return (
            <div className="bot-marketplace error-state">
                <Empty
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                    description={error}
                />
            </div>
        );
    }

    return (
        <div className="bot-marketplace">
            {/* 헤더 */}
            <div className="marketplace-header">
                <div className="header-content">
                    <h1 className="page-title">
                        <RobotOutlined /> Bot Marketplace
                    </h1>
                    <p className="page-subtitle">
                        AI 전략 봇을 선택하고 자동 트레이딩을 시작하세요
                    </p>
                </div>
            </div>

            {/* API 키 미설정 안내 */}
            {apiKeyMissing && (
                <Alert
                    message="거래소 API 키가 설정되지 않았습니다"
                    description={
                        <span>
                            봇을 시작하려면 먼저{' '}
                            <a onClick={() => navigate('/settings')} style={{ color: '#5856d6', cursor: 'pointer' }}>
                                설정 페이지 <SettingOutlined />
                            </a>
                            에서 API 키를 등록해주세요.
                        </span>
                    }
                    type="warning"
                    showIcon
                    style={{ marginBottom: 16, background: '#2a2a2a', border: '1px solid #ff9500' }}
                />
            )}

            {/* 활성 봇 배너 */}
            {summary && !apiKeyMissing && (
                <ActiveBotsBanner
                    activeBotCount={summary.active_bot_count || 0}
                    totalPnl={summary.total_pnl || 0}
                    totalPnlPercent={summary.total_pnl_percent || 0}
                />
            )}

            {/* 필터 */}
            <BotFilters
                sortBy={sortBy}
                onSortChange={setSortBy}
                filterSymbol={filterSymbol}
                onFilterChange={setFilterSymbol}
                symbols={availableSymbols}
            />

            {/* 봇 카드 그리드 */}
            {loading ? (
                <div className="loading-container">
                    <Spin size="large" tip="템플릿 로딩 중..." />
                </div>
            ) : templates.length === 0 ? (
                <Empty
                    className="empty-state"
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                    description="사용 가능한 봇 템플릿이 없습니다"
                />
            ) : (
                <BotCardList
                    templates={templates}
                    onUseTemplate={selectTemplate}
                />
            )}

            {/* 상세 모달 */}
            <BotDetailModal
                open={detailModalOpen}
                template={selectedTemplate}
                onClose={closeDetailModal}
                onStart={handleStartBot}
                availableBalance={summary?.available_amount || 0}
            />
        </div>
    );
};

export default BotMarketplace;

/**
 * useBotMarketplace - 봇 마켓플레이스 상태 관리 훅
 *
 * 템플릿 목록 로드, 정렬, 필터링, 봇 시작 기능 제공
 */
import { useState, useCallback, useMemo } from 'react';
import multibotAPI from '../api/multibot';

export function useBotMarketplace() {
    // 데이터 상태
    const [templates, setTemplates] = useState([]);
    const [summary, setSummary] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    // UI 상태
    const [sortBy, setSortBy] = useState('roi');
    const [filterSymbol, setFilterSymbol] = useState(null);
    const [selectedTemplate, setSelectedTemplate] = useState(null);
    const [detailModalOpen, setDetailModalOpen] = useState(false);

    /**
     * 템플릿 목록 로드
     */
    const loadTemplates = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await multibotAPI.getTemplates();
            setTemplates(response.templates || []);
            return response;
        } catch (err) {
            console.error('[useBotMarketplace] Failed to load templates:', err);
            setError(err.message || 'Failed to load templates');
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    /**
     * 잔고 요약 로드
     */
    const loadSummary = useCallback(async () => {
        try {
            const response = await multibotAPI.getSummary();
            setSummary(response);
            return response;
        } catch (err) {
            console.error('[useBotMarketplace] Failed to load summary:', err);
            throw err;
        }
    }, []);

    /**
     * 봇 시작
     * @param {number} templateId - 템플릿 ID
     * @param {number} amount - 투자 금액 (USDT)
     * @param {string} [name] - 봇 이름 (선택)
     */
    const startBot = useCallback(async (templateId, amount, name) => {
        try {
            const data = { template_id: templateId, amount };
            if (name) {
                data.name = name;
            }
            const response = await multibotAPI.startBot(data);
            // 성공 시 잔고 요약 갱신
            await loadSummary();
            return response;
        } catch (err) {
            console.error('[useBotMarketplace] Failed to start bot:', err);
            throw err;
        }
    }, [loadSummary]);

    /**
     * 정렬된 템플릿 (useMemo)
     * - featured 템플릿은 항상 상단에 표시
     * - 정렬: roi(높은순), users(많은순), new(최신순)
     */
    const sortedTemplates = useMemo(() => {
        let filtered = [...templates];

        // 심볼 필터링
        if (filterSymbol) {
            filtered = filtered.filter(t => t.symbol === filterSymbol);
        }

        // featured와 일반 분리
        const featured = filtered.filter(t => t.is_featured);
        const regular = filtered.filter(t => !t.is_featured);

        // 정렬 함수
        const sortFn = (a, b) => {
            switch (sortBy) {
                case 'roi':
                    // 높은 ROI 순
                    return (b.backtest_roi_30d || 0) - (a.backtest_roi_30d || 0);
                case 'users':
                    // 많은 사용자 순
                    return (b.active_users || 0) - (a.active_users || 0);
                case 'new':
                    // 최신 순 (ID가 큰 것이 최신)
                    return (b.id || 0) - (a.id || 0);
                default:
                    return 0;
            }
        };

        // 각 그룹 내에서 정렬
        featured.sort(sortFn);
        regular.sort(sortFn);

        // featured를 상단에 배치
        return [...featured, ...regular];
    }, [templates, sortBy, filterSymbol]);

    /**
     * 사용 가능한 심볼 목록
     */
    const availableSymbols = useMemo(() => {
        const symbolSet = new Set(templates.map(t => t.symbol));
        return Array.from(symbolSet).sort();
    }, [templates]);

    /**
     * 템플릿 선택 (모달 열기)
     */
    const selectTemplate = useCallback((template) => {
        setSelectedTemplate(template);
        setDetailModalOpen(true);
    }, []);

    /**
     * 모달 닫기
     */
    const closeDetailModal = useCallback(() => {
        setDetailModalOpen(false);
        setSelectedTemplate(null);
    }, []);

    return {
        // 데이터
        templates: sortedTemplates,
        summary,
        loading,
        error,
        availableSymbols,

        // 정렬/필터
        sortBy,
        setSortBy,
        filterSymbol,
        setFilterSymbol,

        // 모달 상태
        selectedTemplate,
        detailModalOpen,

        // 액션
        loadTemplates,
        loadSummary,
        startBot,
        selectTemplate,
        closeDetailModal,
    };
}

export default useBotMarketplace;

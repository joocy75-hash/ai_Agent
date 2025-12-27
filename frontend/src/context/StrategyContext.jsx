/**
 * 전략 관리 Context
 * 전략 목록 상태를 전역으로 관리하여 전략관리 페이지와 트레이딩 페이지 간의 연동을 처리
 */

import { createContext, useContext, useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { strategyAPI } from '../api/strategy';
import apiClient from '../api/client';

const StrategyContext = createContext();

// 캐시 TTL: 60초 - 불필요한 API 호출 방지
const CACHE_TTL = 60000;

export function StrategyProvider({ children }) {
    const [strategies, setStrategies] = useState([]);
    const [loading, setLoading] = useState(false);
    const [lastUpdated, setLastUpdated] = useState(null);
    const lastUpdatedRef = useRef(null);

    // strategies 길이를 ref로 추적하여 순환 의존성 방지
    const strategiesLengthRef = useRef(0);
    strategiesLengthRef.current = strategies.length;

    /**
     * 전략 목록 로드 (백엔드에서 가져오기)
     * @param {boolean} force - true면 캐시 무시하고 강제 로드
     * Note: 순환 의존성 방지를 위해 strategies를 의존성 배열에서 제거
     */
    const loadStrategies = useCallback(async (force = false) => {
        // 캐시가 유효하면 API 호출 스킵 (ref 사용으로 의존성 제거)
        const now = Date.now();
        if (!force && strategiesLengthRef.current > 0 && lastUpdatedRef.current && (now - lastUpdatedRef.current < CACHE_TTL)) {
            console.log('[StrategyContext] Using cached strategies (TTL not expired)');
            return; // void 반환 - 캐시된 상태 사용
        }

        setLoading(true);
        try {
            const token = localStorage.getItem('token');
            if (!token) {
                console.log('[StrategyContext] No token, skipping strategy load');
                setStrategies([]);
                setLoading(false);
                return;
            }

            const data = await strategyAPI.getAIStrategies();
            const allStrategies = data.strategies || [];

            setStrategies(allStrategies);
            const updateTime = Date.now();
            setLastUpdated(updateTime);
            lastUpdatedRef.current = updateTime;
            console.log(`[StrategyContext] Loaded ${allStrategies.length} strategies`);
        } catch (error) {
            console.error('[StrategyContext] Error loading strategies:', error);
            // 에러 시 기존 데이터 유지
        } finally {
            setLoading(false);
        }
    }, []); // 의존성 제거 - ref 사용으로 최신 값 참조

    /**
     * 활성화된 전략만 가져오기 (트레이딩 페이지용)
     */
    const getActiveStrategies = useCallback(() => {
        return strategies.filter(s => s.is_active === true);
    }, [strategies]);

    /**
     * 전략 삭제 후 목록 새로고침
     * Note: apiClient has baseURL='/api/v1', so this calls /api/v1/ai/strategies/{id}
     */
    const deleteStrategy = useCallback(async (strategyId) => {
        try {
            await apiClient.delete(`/ai/strategies/${strategyId}`);

            // 즉시 로컬 상태에서 제거
            setStrategies(prev => prev.filter(s => s.id !== strategyId));
            const updateTime = Date.now();
            setLastUpdated(updateTime);
            lastUpdatedRef.current = updateTime;

            console.log(`[StrategyContext] Strategy ${strategyId} deleted`);
            return true;
        } catch (error) {
            console.error('[StrategyContext] Error deleting strategy:', error);
            throw error;
        }
    }, []);

    /**
     * 전략 활성/비활성 토글 후 목록 업데이트
     * Note: apiClient has baseURL='/api/v1', so this calls /api/v1/strategy/{id}/toggle
     */
    const toggleStrategy = useCallback(async (strategyId) => {
        try {
            const response = await apiClient.patch(`/strategy/${strategyId}/toggle`);
            const newActiveStatus = response.data.is_active;

            // 즉시 로컬 상태 업데이트
            setStrategies(prev => prev.map(s =>
                s.id === strategyId ? { ...s, is_active: newActiveStatus } : s
            ));
            const updateTime = Date.now();
            setLastUpdated(updateTime);
            lastUpdatedRef.current = updateTime;

            console.log(`[StrategyContext] Strategy ${strategyId} toggled to ${newActiveStatus ? 'active' : 'inactive'}`);
            return newActiveStatus;
        } catch (error) {
            console.error('[StrategyContext] Error toggling strategy:', error);
            throw error;
        }
    }, []);

    /**
     * 전략 목록 강제 새로고침 트리거
     */
    const refreshStrategies = useCallback(() => {
        return loadStrategies(true); // 강제 새로고침
    }, [loadStrategies]);

    // 초기 로드
    useEffect(() => {
        const token = localStorage.getItem('token');
        if (token) {
            loadStrategies();
        }
    }, [loadStrategies]);

    // Memoize context value to prevent unnecessary re-renders of consumers
    const value = useMemo(() => ({
        strategies,
        loading,
        lastUpdated,
        loadStrategies,
        getActiveStrategies,
        deleteStrategy,
        toggleStrategy,
        refreshStrategies,
    }), [
        strategies,
        loading,
        lastUpdated,
        loadStrategies,
        getActiveStrategies,
        deleteStrategy,
        toggleStrategy,
        refreshStrategies,
    ]);

    return (
        <StrategyContext.Provider value={value}>
            {children}
        </StrategyContext.Provider>
    );
}

export function useStrategies() {
    const context = useContext(StrategyContext);
    if (!context) {
        throw new Error('useStrategies must be used within a StrategyProvider');
    }
    return context;
}

export default StrategyContext;

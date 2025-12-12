/**
 * 다중 봇 인스턴스 API 클라이언트
 * 
 * 백엔드 엔드포인트: /bot-instances
 * 관련 문서: docs/MULTI_BOT_03_IMPLEMENTATION.md
 */

import apiClient from './client';

export const botInstancesAPI = {
    /**
     * 봇 목록 조회
     * @returns {Promise<{bots: Array, total_allocation: number, available_allocation: number, running_count: number, total_count: number}>}
     */
    list: () => apiClient.get('/bot-instances/list').then(r => r.data),

    /**
     * 새 봇 생성
     * @param {Object} data - 봇 생성 데이터
     * @param {string} data.name - 봇 이름
     * @param {string} data.bot_type - 봇 타입 ('ai_trend' | 'grid')
     * @param {number} [data.strategy_id] - 전략 ID (AI 봇만)
     * @param {string} data.symbol - 거래 심볼
     * @param {number} data.allocation_percent - 할당 비율 (0-100)
     * @param {number} [data.max_leverage] - 최대 레버리지
     * @param {number} [data.max_positions] - 최대 포지션 수
     * @param {number} [data.stop_loss_percent] - 손절 %
     * @param {number} [data.take_profit_percent] - 익절 %
     * @param {boolean} [data.telegram_notify] - 텔레그램 알림
     * @returns {Promise<{success: boolean, bot_id: number, message: string}>}
     */
    create: (data) => apiClient.post('/bot-instances/create', data).then(r => r.data),

    /**
     * 봇 상세 조회
     * @param {number} botId - 봇 ID
     * @returns {Promise<Object>} 봇 상세 정보
     */
    get: (botId) => apiClient.get(`/bot-instances/${botId}`).then(r => r.data),

    /**
     * 봇 설정 수정
     * @param {number} botId - 봇 ID
     * @param {Object} data - 수정할 필드
     * @returns {Promise<{success: boolean, message: string}>}
     */
    update: (botId, data) => apiClient.patch(`/bot-instances/${botId}`, data).then(r => r.data),

    /**
     * 봇 삭제 (소프트 삭제)
     * @param {number} botId - 봇 ID
     * @returns {Promise<{success: boolean, message: string}>}
     */
    delete: (botId) => apiClient.delete(`/bot-instances/${botId}`).then(r => r.data),

    /**
     * 특정 봇 시작
     * @param {number} botId - 봇 ID
     * @returns {Promise<{success: boolean, message: string}>}
     */
    start: (botId) => apiClient.post(`/bot-instances/${botId}/start`).then(r => r.data),

    /**
     * 특정 봇 중지
     * @param {number} botId - 봇 ID
     * @returns {Promise<{success: boolean, message: string}>}
     */
    stop: (botId) => apiClient.post(`/bot-instances/${botId}/stop`).then(r => r.data),

    /**
     * 모든 봇 시작
     * @returns {Promise<{success: boolean, message: string}>}
     */
    startAll: () => apiClient.post('/bot-instances/start-all').then(r => r.data),

    /**
     * 모든 봇 중지
     * @returns {Promise<{success: boolean, message: string}>}
     */
    stopAll: () => apiClient.post('/bot-instances/stop-all').then(r => r.data),

    /**
     * 봇별 상세 통계
     * @param {number} botId - 봇 ID
     * @returns {Promise<Object>} 봇 통계
     */
    getStats: (botId) => apiClient.get(`/bot-instances/${botId}/stats`).then(r => r.data),

    /**
     * 전체 봇 통계 요약
     * @returns {Promise<Object>} 전체 통계
     */
    getSummary: () => apiClient.get('/bot-instances/stats/summary').then(r => r.data),
};

export default botInstancesAPI;

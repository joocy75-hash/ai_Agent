/**
 * 그리드 봇 전용 API 클라이언트
 *
 * 백엔드 엔드포인트: /grid-bot
 * 관련 문서: docs/MULTI_BOT_02_DATABASE.md
 */

import apiClient from './client';

export const gridBotAPI = {
    /**
     * 그리드 봇 설정 조회
     * @param {number} botId - 봇 인스턴스 ID
     * @returns {Promise<Object>} 그리드 설정 + 주문 상태
     */
    getConfig: (botId) => apiClient.get(`/grid-bot/${botId}/config`).then(r => r.data),

    /**
     * 그리드 봇 설정 생성/수정
     * @param {number} botId - 봇 인스턴스 ID
     * @param {Object} config - 그리드 설정
     * @param {number} config.lower_price - 하한가
     * @param {number} config.upper_price - 상한가
     * @param {number} config.grid_count - 그리드 개수 (2-100)
     * @param {string} [config.grid_mode] - 'arithmetic' | 'geometric'
     * @param {number} config.total_investment - 총 투자금 (USDT)
     * @param {number} [config.trigger_price] - 시작 트리거 가격
     * @param {number} [config.stop_upper] - 상한 스탑
     * @param {number} [config.stop_lower] - 하한 스탑
     * @returns {Promise<{success: boolean, config_id: number, message: string}>}
     */
    saveConfig: (botId, config) => apiClient.post(`/grid-bot/${botId}/config`, config).then(r => r.data),

    /**
     * 그리드 주문 목록 조회
     * @param {number} botId - 봇 인스턴스 ID
     * @returns {Promise<{orders: Array, summary: Object}>}
     */
    getOrders: (botId) => apiClient.get(`/grid-bot/${botId}/orders`).then(r => r.data),

    /**
     * 그리드 봇 시작 (주문 배치)
     * @param {number} botId - 봇 인스턴스 ID
     * @returns {Promise<{success: boolean, placed_orders: number, message: string}>}
     */
    start: (botId) => apiClient.post(`/grid-bot/${botId}/start`).then(r => r.data),

    /**
     * 그리드 봇 중지 (주문 취소)
     * @param {number} botId - 봇 인스턴스 ID
     * @param {boolean} [closePositions=false] - 포지션도 청산할지 여부
     * @returns {Promise<{success: boolean, cancelled_orders: number, message: string}>}
     */
    stop: (botId, closePositions = false) =>
        apiClient.post(`/grid-bot/${botId}/stop`, { close_positions: closePositions }).then(r => r.data),

    /**
     * 그리드 봇 통계 조회
     * @param {number} botId - 봇 인스턴스 ID
     * @returns {Promise<Object>} 수익, 거래 횟수, 그리드별 상태 등
     */
    getStats: (botId) => apiClient.get(`/grid-bot/${botId}/stats`).then(r => r.data),

    /**
     * 그리드 미리보기 계산
     * 실제 주문 없이 그리드 라인과 예상 수익 계산
     * @param {Object} params - 계산 파라미터
     * @param {number} params.lower_price - 하한가
     * @param {number} params.upper_price - 상한가
     * @param {number} params.grid_count - 그리드 개수
     * @param {string} [params.grid_mode] - 'arithmetic' | 'geometric'
     * @param {number} params.total_investment - 총 투자금
     * @param {number} params.current_price - 현재가
     * @returns {Promise<{grids: Array, expected_profit_per_grid: number, ...}>}
     */
    preview: (params) => apiClient.post('/grid-bot/preview', params).then(r => r.data),

    /**
     * 현재 시장 가격 조회 (그리드 설정용)
     * @param {string} symbol - 심볼 (예: 'BTCUSDT')
     * @returns {Promise<{price: number, high_24h: number, low_24h: number}>}
     */
    getMarketPrice: (symbol) => apiClient.get(`/grid-bot/market/${symbol}`).then(r => r.data),
};

export default gridBotAPI;

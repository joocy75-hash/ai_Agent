/**
 * Trend Template API Client
 * - AI 추세 봇 템플릿 목록/상세 조회
 * - 템플릿으로 봇 생성
 */
import apiClient from './client';

export const trendTemplateAPI = {
    /**
     * 공개 템플릿 목록 조회
     * @param {Object} params - { symbol?, limit?, offset? }
     * @returns {Promise<{success, data, total}>}
     */
    async list(params = {}) {
        const response = await apiClient.get('/trend-templates', { params });
        return response.data;
    },

    /**
     * 템플릿 상세 조회
     * @param {number} templateId
     * @returns {Promise<{success, data}>}
     */
    async getDetail(templateId) {
        const response = await apiClient.get(`/trend-templates/${templateId}`);
        return response.data;
    },

    /**
     * 템플릿으로 AI 추세 봇 생성 (Use 버튼)
     * @param {number} templateId
     * @param {Object} data - { investment_amount, leverage? }
     * @returns {Promise<{bot_instance_id, message}>}
     */
    async useTemplate(templateId, data) {
        const response = await apiClient.post(`/trend-templates/${templateId}/use`, data);
        return response.data;
    },

    /**
     * 인기 템플릿 목록 조회
     * @param {number} limit
     * @returns {Promise<{success, data}>}
     */
    async getFeatured(limit = 5) {
        const response = await apiClient.get('/trend-templates', {
            params: { limit, is_featured: true }
        });
        return response.data;
    }
};

export default trendTemplateAPI;

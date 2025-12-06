import axios from 'axios';

const API_URL = 'http://localhost:8000';

// Analytics API 클라이언트
export const analyticsAPI = {
    /**
     * 자산 곡선 데이터 가져오기
     * @param {string} period - 기간 (1d, 1w, 1m, 3m, 1y, all)
     * @returns {Promise} 자산 곡선 데이터
     */
    getEquityCurve: async (period = '1m') => {
        try {
            const token = localStorage.getItem('token');
            const response = await axios.get(`${API_URL}/analytics/equity-curve`, {
                params: { period },
                headers: token ? { Authorization: `Bearer ${token}` } : {},
            });
            return response.data;
        } catch (error) {
            console.error('[Analytics API] Equity curve error:', error);
            throw error;
        }
    },

    /**
     * 리스크 지표 가져오기
     * @returns {Promise} 리스크 지표 데이터
     */
    getRiskMetrics: async () => {
        try {
            const token = localStorage.getItem('token');
            const response = await axios.get(`${API_URL}/analytics/risk-metrics`, {
                headers: token ? { Authorization: `Bearer ${token}` } : {},
            });
            return response.data;
        } catch (error) {
            console.error('[Analytics API] Risk metrics error:', error);
            throw error;
        }
    },

    /**
     * 성과 지표 가져오기
     * @param {string} period - 기간
     * @returns {Promise} 성과 지표 데이터
     */
    getPerformanceMetrics: async (period = '1m') => {
        try {
            const token = localStorage.getItem('token');
            const response = await axios.get(`${API_URL}/analytics/performance`, {
                params: { period },
                headers: token ? { Authorization: `Bearer ${token}` } : {},
            });
            return response.data;
        } catch (error) {
            console.error('[Analytics API] Performance metrics error:', error);
            throw error;
        }
    },

    /**
     * 기간별 보고서 가져오기
     * @param {string} reportType - 보고서 타입 (daily, weekly, monthly, quarterly, yearly)
     * @param {string} startDate - 시작일 (YYYY-MM-DD)
     * @param {string} endDate - 종료일 (YYYY-MM-DD)
     * @returns {Promise} 보고서 데이터
     */
    getReport: async (reportType = 'monthly', startDate, endDate) => {
        try {
            const token = localStorage.getItem('token');
            const response = await axios.get(`${API_URL}/analytics/report`, {
                params: {
                    type: reportType,
                    start_date: startDate,
                    end_date: endDate,
                },
                headers: token ? { Authorization: `Bearer ${token}` } : {},
            });
            return response.data;
        } catch (error) {
            console.error('[Analytics API] Report error:', error);
            throw error;
        }
    },
};

// 편의 함수 exports
export const getEquityCurve = analyticsAPI.getEquityCurve;
export const getPerformance = analyticsAPI.getPerformanceMetrics;
export const getRiskMetrics = analyticsAPI.getRiskMetrics;

export default analyticsAPI;

import apiClient from './client';

export const alertsAPI = {
  // 긴급 알림 조회
  getUrgent: async () => {
    const response = await apiClient.get('/alerts/urgent');
    return response.data;
  },

  // 전체 알림 조회
  getAll: async (limit = 100, offset = 0) => {
    const response = await apiClient.get('/alerts/all', {
      params: { limit, offset }
    });
    return response.data;
  },

  // 알림 읽음 처리
  resolve: async (alertId) => {
    const response = await apiClient.post(`/alerts/resolve/${alertId}`);
    return response.data;
  },

  // 전체 알림 읽음 처리
  resolveAll: async () => {
    const response = await apiClient.post('/alerts/resolve-all');
    return response.data;
  },

  // 알림 통계
  getStatistics: async () => {
    const response = await apiClient.get('/alerts/statistics');
    return response.data;
  },

  // 읽은 알림 삭제
  clearResolved: async () => {
    const response = await apiClient.delete('/alerts/clear-resolved');
    return response.data;
  }
};

export default alertsAPI;

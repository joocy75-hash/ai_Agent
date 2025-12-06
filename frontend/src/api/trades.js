import apiClient from './client';

export const tradesAPI = {
  // 거래 포지션 조회 (차트용)
  getPositions: async (limit = 100) => {
    const response = await apiClient.get('/trades/positions', {
      params: { limit }
    });
    return response.data;
  },

  // 최근 거래 내역 조회
  getRecentTrades: async (limit = 50) => {
    const response = await apiClient.get('/trades/recent-trades', {
      params: { limit }
    });
    return response.data;
  }
};

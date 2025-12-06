import apiClient from './client';

export const botAPI = {
  // 봇 시작
  start: async (config) => {
    const response = await apiClient.post('/bot/start', config);
    return response.data;
  },

  // 봇 중지
  stop: async () => {
    const response = await apiClient.post('/bot/stop');
    return response.data;
  },

  // 봇 상태 조회
  getStatus: async () => {
    const response = await apiClient.get('/bot/status');
    return response.data;
  },

  // Legacy aliases for backward compatibility
  startBot: async (strategyId) => {
    const response = await apiClient.post('/bot/start', {
      strategy_id: strategyId
    });
    return response.data;
  },

  stopBot: async () => {
    const response = await apiClient.post('/bot/stop');
    return response.data;
  },

  getBotStatus: async () => {
    const response = await apiClient.get('/bot/status');
    return response.data;
  }
};

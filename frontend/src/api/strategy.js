import apiClient from './client';

export const strategyAPI = {
  // 간단 전략 생성
  createStrategy: async (strategyData) => {
    const response = await apiClient.post('/strategy/create', strategyData);
    return response.data;
  },

  // AI 전략 생성
  generateAIStrategies: async () => {
    const response = await apiClient.post('/ai/strategies/generate', {
      count: 3
    });
    return response.data;
  },

  // 사용자의 AI 전략 목록 조회
  getAIStrategies: async () => {
    const response = await apiClient.get('/ai/strategies/list');
    return response.data;
  },

  // 전략 삭제
  deleteStrategy: async (strategyId) => {
    const response = await apiClient.delete(`/ai/strategies/${strategyId}`);
    return response.data;
  },

  // 공개 전략 목록 조회
  getPublicStrategies: async () => {
    const response = await apiClient.get('/strategy/list');
    return response.data;
  },

  // 전략 선택 (봇 실행용)
  selectStrategy: async (strategyId) => {
    const response = await apiClient.post('/strategy/select', {
      strategy_id: strategyId
    });
    return response.data;
  },

  // AI 상태 확인
  getAIStatus: async () => {
    const response = await apiClient.get('/ai/status');
    return response.data;
  },

  // 전략 활성화/비활성화 토글
  toggleStrategy: async (strategyId) => {
    const response = await apiClient.patch(`/strategy/${strategyId}/toggle`);
    return response.data;
  }
};

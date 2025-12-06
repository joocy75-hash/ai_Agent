import apiClient from './client';

// Rate Limiting 상태 관리
const API_KEY_VIEW_LIMIT = {
  count: 0,
  resetTime: null,
  maxRequests: 3,
  windowMs: 3600000 // 1 hour
};

export const accountAPI = {
  // 잔고 조회
  getBalance: async () => {
    const response = await apiClient.get('/account/balance');
    return response.data;
  },

  // 포지션 조회
  getPositions: async () => {
    const response = await apiClient.get('/account/positions');
    return response.data;
  },

  // API 키 저장
  saveApiKeys: async (apiKey, secretKey, passphrase = '') => {
    const response = await apiClient.post('/account/save_keys', {
      api_key: apiKey,
      secret_key: secretKey,
      passphrase: passphrase
    });
    return response.data;
  },

  // 내 API 키 조회 (Rate Limited)
  getMyKeys: async () => {
    // 클라이언트 측 rate limit 확인
    const now = Date.now();

    if (API_KEY_VIEW_LIMIT.resetTime && now < API_KEY_VIEW_LIMIT.resetTime) {
      if (API_KEY_VIEW_LIMIT.count >= API_KEY_VIEW_LIMIT.maxRequests) {
        const remainingMs = API_KEY_VIEW_LIMIT.resetTime - now;
        const remainingMinutes = Math.ceil(remainingMs / 60000);
        throw new Error(
          `API 키 조회 한도 초과. ${remainingMinutes}분 후에 다시 시도하세요.`
        );
      }
    } else {
      // Reset window
      API_KEY_VIEW_LIMIT.count = 0;
      API_KEY_VIEW_LIMIT.resetTime = now + API_KEY_VIEW_LIMIT.windowMs;
    }

    try {
      const response = await apiClient.get('/account/my_keys');
      API_KEY_VIEW_LIMIT.count++;
      const remainingMinutes = Math.ceil((API_KEY_VIEW_LIMIT.resetTime - Date.now()) / 60000);
      console.log(`[Account API] API 키 조회 ${API_KEY_VIEW_LIMIT.count}/${API_KEY_VIEW_LIMIT.maxRequests} (${remainingMinutes}분 내)`);
      return response.data;
    } catch (error) {
      if (error.response?.status === 429) {
        // 백엔드에서 rate limit 초과
        const retryAfter = error.response.headers['retry-after'];
        throw new Error(
          `요청 한도 초과. ${retryAfter ? `${retryAfter}초` : '잠시'} 후에 다시 시도하세요.`
        );
      }
      throw error;
    }
  },

  // 리스크 설정 조회
  getRiskSettings: async () => {
    const response = await apiClient.get('/account/risk-settings');
    return response.data;
  },

  // 리스크 설정 저장
  saveRiskSettings: async (dailyLossLimit, maxLeverage, maxPositions) => {
    const response = await apiClient.post('/account/risk-settings', {
      daily_loss_limit: dailyLossLimit,
      max_leverage: maxLeverage,
      max_positions: maxPositions,
    });
    return response.data;
  }
};

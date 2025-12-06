import apiClient from './client';

export const chartAPI = {
  // 캔들 데이터 조회
  getCandles: async (symbol, limit = 200, includeCurrent = true, timeframe = '1m') => {
    const response = await apiClient.get(`/chart/candles/${symbol}`, {
      params: { limit, include_current: includeCurrent, timeframe }
    });
    return response.data;
  },

  // 포지션 마커 조회
  getPositionMarkers: async (symbol, daysBack = 7) => {
    const response = await apiClient.get(`/chart/positions/${symbol}`, {
      params: { days_back: daysBack }
    });
    return response.data;
  },

  // 현재 포지션 조회
  getCurrentPositions: async (symbol) => {
    const response = await apiClient.get(`/chart/positions/current/${symbol}`);
    return response.data;
  },

  // 차트 상태 조회
  getChartStatus: async () => {
    const response = await apiClient.get('/chart/status');
    return response.data;
  }
};

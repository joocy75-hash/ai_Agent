import apiClient from './client';

export const backtestAPI = {
  // 백테스트 실행 (NEW)
  runBacktest: async (data) => {
    const response = await apiClient.post('/backtest/start', {
      strategy_id: data.strategy_id,
      initial_balance: data.initial_balance,
      start_date: data.start_date,
      end_date: data.end_date,
      symbol: data.symbol,
      timeframe: data.timeframe,
      csv_path: data.csv_path || null
    });
    return response.data;
  },

  // 백테스트 시작 (기존 - 호환성 유지)
  start: async (data) => {
    const response = await apiClient.post('/backtest/start', data);
    return response.data;
  },

  // 백테스트 결과 조회
  getResult: async (resultId) => {
    const response = await apiClient.get(`/backtest/result/${resultId}`);
    return response.data;
  },

  // 백테스트 결과 삭제
  deleteResult: async (resultId) => {
    const response = await apiClient.delete(`/backtest_history/results/${resultId}`);
    return response.data;
  },

  // 백테스트 이력 조회 (내역 - 사용자별)
  getHistory: async (limit = 50) => {
    const response = await apiClient.get('/backtest_history/results', {
      params: { limit }
    });
    return response.data;
  },

  // 모든 백테스트 조회 (결과 목록 - 사용자별)
  getAllBacktests: async () => {
    try {
      const response = await apiClient.get('/backtest_history/results');
      // API 응답 형식에 맞게 변환
      const results = response.data.results || [];
      return {
        backtests: results.map(bt => ({
          id: bt.id,
          name: `백테스트 #${bt.id}`,
          config: {
            symbol: bt.pair || bt.symbol || 'N/A',
            timeframe: bt.timeframe || '1h',
            strategy_type: bt.strategy_id ? `Strategy ${bt.strategy_id}` : 'N/A',
          },
          metrics: {
            total_return: bt.total_return || (bt.metrics?.total_return) || 0,
            sharpe_ratio: bt.sharpe_ratio || (bt.metrics?.sharpe_ratio) || 0,
            max_drawdown: bt.max_drawdown || (bt.metrics?.max_drawdown) || 0,
            win_rate: bt.win_rate || (bt.metrics?.win_rate) || 0,
            total_trades: bt.total_trades || (bt.metrics?.total_trades) || 0,
            profit_factor: bt.profit_factor || (bt.metrics?.profit_factor) || 0,
          },
          status: bt.status || 'completed',
          initial_balance: bt.initial_balance,
          final_balance: bt.final_balance,
          created_at: bt.created_at,
        }))
      };
    } catch (error) {
      console.error('[BacktestAPI] getAllBacktests error:', error);
      return { backtests: [] };
    }
  },

  // 백테스트 결과 상세 조회
  getBacktestResult: async (id) => {
    const response = await apiClient.get(`/backtest/result/${id}`);
    return response.data;
  },

  // 캐시 정보 조회 (사용 가능한 데이터 범위)
  getCacheInfo: async () => {
    try {
      const response = await apiClient.get('/backtest/cache/info');
      return response.data;
    } catch (error) {
      console.error('[BacktestAPI] getCacheInfo error:', error);
      return {
        mode: 'offline',
        cache_only: true,
        total_files: 0,
        available_data: []
      };
    }
  },

  // 사용 가능한 심볼/타임프레임 목록 조회
  getAvailableSymbols: async () => {
    try {
      const response = await apiClient.get('/backtest/cache/symbols');
      return response.data;
    } catch (error) {
      console.error('[BacktestAPI] getAvailableSymbols error:', error);
      return {
        symbols: ['BTCUSDT', 'ETHUSDT'],
        timeframes: ['1h', '4h', '1d']
      };
    }
  }
};

export default backtestAPI;

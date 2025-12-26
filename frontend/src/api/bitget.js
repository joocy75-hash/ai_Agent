/**
 * Bitget API Client
 * Bitget 거래소 전용 API 호출 함수
 */
import apiClient from './client';

export const bitgetAPI = {
  /**
   * 현재가 조회
   * @param {string} symbol - 거래쌍 (예: BTCUSDT)
   */
  async getTicker(symbol) {
    try {
      const response = await apiClient.get(`/bitget/ticker/${symbol}`);
      return response.data;
    } catch (error) {
      console.error('[BitgetAPI] getTicker error:', error);
      throw error;
    }
  },

  /**
   * 호가 조회
   * @param {string} symbol - 거래쌍
   * @param {number} limit - 호가 개수 (기본: 20, 최대: 100)
   */
  async getOrderbook(symbol, limit = 20) {
    try {
      const response = await apiClient.get(`/bitget/orderbook/${symbol}`, {
        params: { limit }
      });
      return response.data;
    } catch (error) {
      console.error('[BitgetAPI] getOrderbook error:', error);
      throw error;
    }
  },

  /**
   * 포지션 조회
   * @param {string} symbol - 거래쌍 (선택사항, 없으면 전체 조회)
   */
  async getPositions(symbol = null) {
    try {
      const params = symbol ? { symbol } : {};
      const response = await apiClient.get('/bitget/positions', { params });
      return response.data;
    } catch (error) {
      console.error('[BitgetAPI] getPositions error:', error);
      throw error;
    }
  },

  /**
   * 계좌 정보 조회 (잔고 및 마진)
   */
  async getAccount() {
    try {
      const response = await apiClient.get('/bitget/account');
      return response.data;
    } catch (error) {
      // API 키가 없으면 404 또는 500 에러 발생 - 조용히 처리
      if (error.response?.status === 404 || error.response?.status === 500) {
        console.log('[BitgetAPI] ℹ️ Account API not available (API key not configured)');
      } else {
        console.error('[BitgetAPI] getAccount error:', error);
      }
      throw error;
    }
  },

  /**
   * 미체결 주문 조회
   * @param {string} symbol - 거래쌍 (선택사항)
   */
  async getOpenOrders(symbol = null) {
    try {
      const params = symbol ? { symbol } : {};
      const response = await apiClient.get('/bitget/orders/open', { params });
      return response.data;
    } catch (error) {
      console.error('[BitgetAPI] getOpenOrders error:', error);
      throw error;
    }
  },

  /**
   * 시장가 주문 실행
   * @param {string} symbol - 거래쌍 (예: BTCUSDT)
   * @param {string} side - 주문 방향 ("buy" / "sell")
   * @param {number} size - 주문 수량
   * @param {boolean} reduceOnly - 포지션 감소 전용 (청산 시 true)
   */
  async placeMarketOrder(symbol, side, size, reduceOnly = false) {
    try {
      const response = await apiClient.post('/bitget/orders/market', {
        symbol,
        side,
        size,
        reduce_only: reduceOnly
      });
      return response.data;
    } catch (error) {
      console.error('[BitgetAPI] placeMarketOrder error:', error);
      throw error;
    }
  },

  /**
   * 지정가 주문 실행
   * @param {string} symbol - 거래쌍
   * @param {string} side - 주문 방향 ("buy" / "sell")
   * @param {number} size - 주문 수량
   * @param {number} price - 지정가
   * @param {boolean} reduceOnly - 포지션 감소 전용
   */
  async placeLimitOrder(symbol, side, size, price, reduceOnly = false) {
    try {
      const response = await apiClient.post('/bitget/orders/limit', {
        symbol,
        side,
        size,
        price,
        reduce_only: reduceOnly
      });
      return response.data;
    } catch (error) {
      console.error('[BitgetAPI] placeLimitOrder error:', error);
      throw error;
    }
  },

  /**
   * 주문 취소
   * @param {string} orderId - 주문 ID
   * @param {string} symbol - 거래쌍
   */
  async cancelOrder(orderId, symbol) {
    try {
      const response = await apiClient.delete(`/bitget/orders/${orderId}`, {
        params: { symbol }
      });
      return response.data;
    } catch (error) {
      console.error('[BitgetAPI] cancelOrder error:', error);
      throw error;
    }
  },

  /**
   * 포지션 청산
   * @param {string} symbol - 거래쌍
   * @param {string} side - 포지션 방향 ("long" / "short")
   * @param {number} size - 청산 수량 (null이면 전체 청산)
   */
  async closePosition(symbol, side, size = null) {
    try {
      const data = { symbol, side };
      if (size !== null) {
        data.size = size;
      }
      const response = await apiClient.post('/bitget/positions/close', data);
      return response.data;
    } catch (error) {
      console.error('[BitgetAPI] closePosition error:', error);
      throw error;
    }
  },

  /**
   * 레버리지 설정
   * @param {string} symbol - 거래쌍
   * @param {number} leverage - 레버리지 배수 (1-125)
   */
  async setLeverage(symbol, leverage) {
    try {
      if (leverage < 1 || leverage > 125) {
        throw new Error('Leverage must be between 1 and 125');
      }
      const response = await apiClient.post('/bitget/leverage', {
        symbol,
        leverage
      });
      return response.data;
    } catch (error) {
      console.error('[BitgetAPI] setLeverage error:', error);
      throw error;
    }
  },

  /**
   * 캔들 데이터 조회
   * @param {string} symbol - 거래쌍 (예: BTCUSDT)
   * @param {string} timeframe - 타임프레임 (1m, 5m, 15m, 1h, 4h, 1d)
   * @param {number} limit - 캔들 개수 (기본: 100, 최대: 500)
   */
  async getCandles(symbol, timeframe = '15m', limit = 100) {
    try {
      const response = await apiClient.get(`/chart/candles/${symbol}`, {
        params: {
          timeframe,
          limit,
          include_current: true
        }
      });
      return response.data;
    } catch (error) {
      console.error('[BitgetAPI] getCandles error:', error);
      throw error;
    }
  }
};

export default bitgetAPI;

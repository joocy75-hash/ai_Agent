import apiClient from './client';

export const orderAPI = {
  // 주문 제출
  submitOrder: async (symbol, side, qty, leverage = 10, priceType = 'market', limitPrice = null) => {
    const response = await apiClient.post('/order/submit', {
      symbol,
      side,
      qty,
      leverage,
      price_type: priceType,
      limit_price: limitPrice
    });
    return response.data;
  },

  // 포지션 청산
  closePosition: async (positionId, symbol, side) => {
    const response = await apiClient.post('/order/close_position', {
      position_id: positionId,
      symbol,
      side
    });
    return response.data;
  },

  // 미체결 주문 조회
  getOpenOrders: async () => {
    const response = await apiClient.get('/order/open');
    return response.data;
  },

  // 주문 내역 조회
  getOrderHistory: async (limit = 50, offset = 0) => {
    const response = await apiClient.get('/order/history', {
      params: { limit, offset }
    });
    return response.data;
  },

  // 자산 변화 내역 조회
  getEquityHistory: async (limit = 100, offset = 0) => {
    const response = await apiClient.get('/order/equity_history', {
      params: { limit, offset }
    });
    return response.data;
  }
};

// 편의 함수 export
export const getOrders = async ({ limit = 50, offset = 0 } = {}) => {
  const response = await orderAPI.getOrderHistory(limit, offset);
  return { orders: response.trades || [] };
};

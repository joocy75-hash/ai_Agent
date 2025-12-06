import apiClient from './client';

export const authAPI = {
  /**
   * 로그인 (2FA 지원)
   * @param {string} email 
   * @param {string} password 
   * @param {string|null} totpCode - 2FA 코드 (선택적)
   * @returns {Promise<{access_token?: string, requires_2fa?: boolean, user_id?: number}>}
   */
  login: async (email, password, totpCode = null) => {
    const payload = { email, password };
    if (totpCode) {
      payload.totp_code = totpCode;
    }
    const response = await apiClient.post('/auth/login', payload);
    return response.data;
  },

  register: async (email, password, passwordConfirm, name, phone) => {
    const response = await apiClient.post('/auth/register', {
      email,
      password,
      password_confirm: passwordConfirm,
      name,
      phone
    });
    return response.data;
  },

  getCurrentUser: async () => {
    const response = await apiClient.get('/auth/me');
    return response.data;
  },

  changePassword: async (currentPassword, newPassword) => {
    const response = await apiClient.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
    return response.data;
  },
};

// 2FA API
export const twoFactorAPI = {
  /**
   * 2FA 상태 조회
   */
  getStatus: async () => {
    const response = await apiClient.get('/auth/2fa/status');
    return response.data;
  },

  /**
   * 2FA 설정 시작 (QR코드 및 시크릿 발급)
   */
  setup: async () => {
    const response = await apiClient.post('/auth/2fa/setup');
    return response.data;
  },

  /**
   * 2FA 코드 검증 및 활성화
   * @param {string} code - 6자리 TOTP 코드
   */
  verify: async (code) => {
    const response = await apiClient.post('/auth/2fa/verify', { code });
    return response.data;
  },

  /**
   * 2FA 비활성화
   * @param {string} code - 6자리 TOTP 코드
   * @param {string} password - 현재 비밀번호
   */
  disable: async (code, password) => {
    const response = await apiClient.post('/auth/2fa/disable', { code, password });
    return response.data;
  },

  /**
   * 2FA 코드 유효성 검사 (민감한 작업 전)
   * @param {string} code - 6자리 TOTP 코드
   */
  validate: async (code) => {
    const response = await apiClient.post('/auth/2fa/validate', { code });
    return response.data;
  },
};

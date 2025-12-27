import { createContext, useState, useContext, useEffect, useCallback, useMemo } from 'react';
import { authAPI } from '../api/auth';

const AuthContext = createContext(null);

// Decode JWT token to extract user_id
const decodeToken = (token) => {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch (error) {
    console.error('[Auth] Failed to decode token:', error);
    return null;
  }
};

// Check if token is expired or will expire soon (5 minutes buffer)
const isTokenExpiringSoon = (token) => {
  const payload = decodeToken(token);
  if (!payload || !payload.exp) return true;

  const expirationTime = payload.exp * 1000; // Convert to milliseconds
  const currentTime = Date.now();
  const bufferTime = 5 * 60 * 1000; // 5 minutes

  return currentTime > (expirationTime - bufferTime);
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [refreshToken, setRefreshToken] = useState(null);
  const [loading, setLoading] = useState(true);

  // Token refresh function
  const refreshAccessToken = useCallback(async () => {
    const storedRefreshToken = localStorage.getItem('refreshToken');
    if (!storedRefreshToken) {
      console.log('[Auth] No refresh token available');
      return null;
    }

    try {
      console.log('[Auth] Attempting to refresh access token...');
      const response = await authAPI.refreshToken(storedRefreshToken);

      if (response.access_token) {
        localStorage.setItem('token', response.access_token);
        setToken(response.access_token);

        // Update refresh token if a new one is provided
        if (response.refresh_token) {
          localStorage.setItem('refreshToken', response.refresh_token);
          setRefreshToken(response.refresh_token);
        }

        console.log('[Auth] Access token refreshed successfully');
        return response.access_token;
      }
    } catch (error) {
      console.error('[Auth] Failed to refresh token:', error);
      // If refresh fails, logout the user
      logout();
      return null;
    }
  }, []);

  // Initialize auth state from localStorage
  useEffect(() => {
    const storedToken = localStorage.getItem('token');
    const storedRefreshToken = localStorage.getItem('refreshToken');
    const userEmail = localStorage.getItem('userEmail');
    const userId = localStorage.getItem('userId');
    const userRole = localStorage.getItem('userRole');

    if (storedToken && userEmail) {
      // Check if access token is expired
      if (isTokenExpiringSoon(storedToken) && storedRefreshToken) {
        // Token is expired, try to refresh
        refreshAccessToken();
      }

      // Extract user_id and role from token if not in localStorage
      let id = userId;
      let role = userRole;

      if (!id || !role) {
        const payload = decodeToken(storedToken);
        if (payload) {
          if (payload.user_id) {
            id = payload.user_id;
            localStorage.setItem('userId', id);
          }
          if (payload.role) {
            role = payload.role;
            localStorage.setItem('userRole', role);
          }
        }
      }

      const userData = {
        id: parseInt(id),
        email: userEmail,
        role: role || 'user'
      };

      console.log('[AuthContext] Initial user data loaded:', userData);

      setUser(userData);
      setToken(storedToken);
      setRefreshToken(storedRefreshToken);
      setLoading(false);
    } else {
      setLoading(false);
    }
  }, [refreshAccessToken]);

  // Auto-refresh token before expiration
  useEffect(() => {
    if (!token) return;

    const checkAndRefresh = async () => {
      if (isTokenExpiringSoon(token)) {
        await refreshAccessToken();
      }
    };

    // Check every 4 minutes
    const interval = setInterval(checkAndRefresh, 4 * 60 * 1000);

    return () => clearInterval(interval);
  }, [token, refreshAccessToken]);

  /**
   * 로그인 함수
   * @param {string} email 
   * @param {string} password 
   * @param {string} totpCode - 2FA 코드 (선택적)
   * @returns 로그인 결과 또는 2FA 필요 여부
   */
  const login = async (email, password, totpCode = null) => {
    const data = await authAPI.login(email, password, totpCode);

    // 2FA가 필요한 경우
    if (data.requires_2fa) {
      return {
        requires_2fa: true,
        user_id: data.user_id
      };
    }

    const newToken = data.access_token;
    const newRefreshToken = data.refresh_token;

    // Decode token to get user_id and role
    const payload = decodeToken(newToken);
    const userId = payload?.user_id;
    const userRole = payload?.role;

    console.log('[Auth] Login successful, user_id:', userId, 'role:', userRole);

    // Store tokens
    localStorage.setItem('token', newToken);
    localStorage.setItem('userEmail', email);
    localStorage.setItem('userId', userId);

    // Store refresh token if provided
    if (newRefreshToken) {
      localStorage.setItem('refreshToken', newRefreshToken);
      setRefreshToken(newRefreshToken);
    }

    // Store role if available
    if (userRole) {
      localStorage.setItem('userRole', userRole);
    }

    const userData = {
      id: parseInt(userId),
      email,
      role: userRole || 'user'
    };
    setUser(userData);
    setToken(newToken);
    return userData;
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('userEmail');
    localStorage.removeItem('userId');
    localStorage.removeItem('userRole');
    setUser(null);
    setToken(null);
    setRefreshToken(null);
  };

  // Memoize context value to prevent unnecessary re-renders of consumers
  const value = useMemo(() => ({
    user,
    token,
    refreshToken,
    login,
    logout,
    loading,
    isAuthenticated: !!user,
    refreshAccessToken,
  }), [user, token, refreshToken, login, logout, loading, refreshAccessToken]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};


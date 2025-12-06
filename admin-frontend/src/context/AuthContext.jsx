import { createContext, useState, useContext, useEffect } from 'react';
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

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const storedToken = localStorage.getItem('token');
    const userEmail = localStorage.getItem('userEmail');
    const userId = localStorage.getItem('userId');
    const userRole = localStorage.getItem('userRole');

    if (storedToken && userEmail) {
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
          // Try to extract role from token (if backend includes it)
          if (payload.role) {
            role = payload.role;
            localStorage.setItem('userRole', role);
          }
        }
      }

      const userData = {
        id: parseInt(id),
        email: userEmail,
        role: role || 'user' // Default to 'user' if role not found
      };

      console.log('[AuthContext] Initial user data loaded:', userData);

      setUser(userData);
      setToken(storedToken);
      setLoading(false);
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email, password) => {
    const data = await authAPI.login(email, password);
    const newToken = data.access_token;

    // Decode token to get user_id and role
    const payload = decodeToken(newToken);
    const userId = payload?.user_id;
    const userRole = payload?.role;

    console.log('[Auth] Login successful, user_id:', userId, 'role:', userRole);

    localStorage.setItem('token', newToken);
    localStorage.setItem('userEmail', email);
    localStorage.setItem('userId', userId);

    // Store role if available in token, otherwise fetch from backend
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
    localStorage.removeItem('userEmail');
    localStorage.removeItem('userId');
    localStorage.removeItem('userRole');
    setUser(null);
    setToken(null);
  };

  const value = {
    user,
    token,
    login,
    logout,
    loading,
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

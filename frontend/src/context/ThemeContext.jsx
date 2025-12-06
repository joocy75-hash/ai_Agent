import { createContext, useContext, useState, useEffect } from 'react';

const ThemeContext = createContext();

export function ThemeProvider({ children }) {
  const [isDarkMode, setIsDarkMode] = useState(() => {
    // Load theme preference from localStorage
    const saved = localStorage.getItem('darkMode');
    return saved === 'true';
  });

  useEffect(() => {
    // Save theme preference
    localStorage.setItem('darkMode', isDarkMode);

    // Apply theme to document
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDarkMode]);

  const toggleDarkMode = () => {
    setIsDarkMode(prev => !prev);
  };

  const theme = {
    isDarkMode,
    toggleDarkMode,
    colors: isDarkMode ? {
      // Dark mode colors
      background: '#1a1a1a',
      surface: '#2d2d2d',
      surfaceHover: '#3d3d3d',
      text: '#ffffff',
      textSecondary: '#b0b0b0',
      border: '#404040',
      primary: '#667eea',
      success: '#4caf50',
      error: '#f44336',
      warning: '#ff9800',
      info: '#2196f3'
    } : {
      // Light mode colors
      background: '#f5f5f5',
      surface: '#ffffff',
      surfaceHover: '#f9f9f9',
      text: '#333333',
      textSecondary: '#666666',
      border: '#dddddd',
      primary: '#667eea',
      success: '#4caf50',
      error: '#f44336',
      warning: '#ff9800',
      info: '#2196f3'
    }
  };

  return (
    <ThemeContext.Provider value={theme}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
}

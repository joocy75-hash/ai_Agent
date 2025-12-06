import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import AdminLayout from './components/layout/AdminLayout';
import Login from './pages/Login';
import AdminDashboard from './pages/AdminDashboard';

// Admin Protected Route Component
function AdminProtectedRoute({ children }) {
  const { isAuthenticated, loading, user } = useAuth();

  console.log('[Admin-Frontend] AdminProtectedRoute Debug:', {
    loading,
    isAuthenticated,
    user,
    userRole: user?.role,
    isAdmin: user?.role === 'admin'
  });

  if (loading) {
    return <div style={{ padding: '2rem', textAlign: 'center' }}>Loading...</div>;
  }

  if (!isAuthenticated) {
    console.log('[Admin-Frontend] Not authenticated, redirecting to login');
    return <Navigate to="/login" />;
  }

  // Check if user is admin
  if (user?.role !== 'admin') {
    console.log('[Admin-Frontend] Access Denied - User is not admin, role:', user?.role);
    return (
      <div style={{
        padding: '2rem',
        textAlign: 'center',
        maxWidth: '600px',
        margin: '100px auto',
        background: '#fee',
        borderRadius: '8px',
        border: '2px solid #c00'
      }}>
        <h1 style={{ color: '#c00' }}>🚫 Access Denied</h1>
        <p>This page is for administrators only.</p>
        <p>Your role: <strong>{user?.role || 'user'}</strong></p>
        <p>Required role: <strong>admin</strong></p>
      </div>
    );
  }

  console.log('[Admin-Frontend] User is admin, rendering AdminLayout');
  return <AdminLayout>{children}</AdminLayout>;
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <AdminProtectedRoute>
                <AdminDashboard />
              </AdminProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;

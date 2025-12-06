import { Component } from 'react';
import { Result, Button } from 'antd';

/**
 * Error Boundary Component
 * React 애플리케이션의 에러를 catch하고 fallback UI를 표시합니다.
 *
 * Features:
 * - 컴포넌트 트리의 에러 catch
 * - 에러 로깅
 * - 사용자 친화적인 에러 메시지
 * - 페이지 새로고침 옵션
 */
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // Log error to console (in production, send to error tracking service)
    console.error('[ErrorBoundary] Caught error:', error, errorInfo);

    this.setState({
      error,
      errorInfo,
    });

    // Send error to logging service (if available)
    if (typeof window !== 'undefined' && window.errorLogger) {
      window.errorLogger.log({
        error: error.toString(),
        componentStack: errorInfo.componentStack,
        timestamp: new Date().toISOString(),
      });
    }
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
    // Optionally reload the page
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '100vh',
            padding: '2rem',
          }}
        >
          <Result
            status="error"
            title="문제가 발생했습니다"
            subTitle="애플리케이션에서 예기치 않은 오류가 발생했습니다. 페이지를 새로고침하거나 잠시 후 다시 시도해주세요."
            extra={[
              <Button type="primary" key="reload" onClick={this.handleReset}>
                페이지 새로고침
              </Button>,
              <Button key="home" onClick={() => window.location.href = '/dashboard'}>
                대시보드로 이동
              </Button>,
            ]}
          >
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <div
                style={{
                  marginTop: '2rem',
                  padding: '1rem',
                  background: '#f5f5f5',
                  borderRadius: '4px',
                  textAlign: 'left',
                }}
              >
                <h4>개발 모드 에러 정보:</h4>
                <pre style={{ fontSize: '12px', overflow: 'auto' }}>
                  <strong>Error:</strong> {this.state.error.toString()}
                  {'\n\n'}
                  <strong>Component Stack:</strong>
                  {this.state.errorInfo?.componentStack}
                </pre>
              </div>
            )}
          </Result>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;

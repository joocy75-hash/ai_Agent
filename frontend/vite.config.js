import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,  // User-only port
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  },
  build: {
    // 청크 사이즈 경고 임계값 조정
    chunkSizeWarningLimit: 700,
    rollupOptions: {
      output: {
        // 라이브러리별로 청크 분리하여 캐싱 효율 극대화
        manualChunks: {
          // React 코어
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          // Ant Design UI
          'vendor-antd': ['antd', '@ant-design/icons'],
          // 차트 라이브러리
          'vendor-charts': ['recharts', 'lightweight-charts'],
        }
      }
    }
  }
})

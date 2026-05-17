import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Vite 配置
// Vite 是一个前端构建工具，比 webpack 快很多
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // 代理：把 /api 开头的请求转发到后端
    // 这样前端开发时不用配 CORS
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})

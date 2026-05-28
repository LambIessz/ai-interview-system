import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://192.168.137.128:8006',
        changeOrigin: true
      },
      '/uploads': {
        target: 'http://192.168.137.128:8006',
        changeOrigin: true
      }
    }
  }
})

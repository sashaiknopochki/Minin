import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      // Proxy API requests to Flask backend
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      },
      '/auth': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      },
    },
  },
})

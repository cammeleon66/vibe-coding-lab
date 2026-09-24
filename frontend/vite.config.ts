import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.{ts,tsx}'],
    setupFiles: './src/setupTests.ts',
  },
  server: {
    host: '127.0.0.1',
    proxy: {
      '/api': 'http://127.0.0.1:8100',
    },
  },
})

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // shared/constants.json lives one level up
    fs: { allow: ['..'] },
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})

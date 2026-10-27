import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const htmlBypass = (req: any) => {
  if (req.headers.accept?.includes('text/html')) {
    return '/index.html'
  }
}

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/auth': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/analyze': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/graph': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        bypass: htmlBypass,
      },
      '/ingest': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        bypass: htmlBypass,
      },
      '/jobs': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'http://127.0.0.1:8000',
        ws: true,
        changeOrigin: true,
      },
      '/reports': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        bypass: htmlBypass,
      },
    },
  },
})

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    // The platform ingress proxies the preview domain to this dev server;
    // allow its host header.
    allowedHosts: true,
    proxy: {
      '/auth': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/conversations': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/videos': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/questions': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});

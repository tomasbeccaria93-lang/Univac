import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/auth': 'http://localhost:8000',
      '/reportes': 'http://localhost:8000'
    }
  },
  build: {
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-vue': ['vue', 'vue-router'],
          'vendor-charts': ['chart.js', 'vue-chartjs'],
          'vendor-xlsx': ['xlsx']
        }
      }
    }
  }
})

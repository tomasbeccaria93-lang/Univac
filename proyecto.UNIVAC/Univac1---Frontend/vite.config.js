import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

function cspConnectSrc(mode) {
  const env = loadEnv(mode, process.cwd(), '')
  const apiUrl = (process.env.VITE_API_URL || env.VITE_API_URL || '').trim()
  const origenes = ["'self'"]

  if (apiUrl) {
    try {
      origenes.push(new URL(apiUrl).origin)
      if (mode === 'production' && /localhost|127\.0\.0\.1/.test(apiUrl)) {
        console.warn(
          '[vite] ATENCIÓN: el build de producción apunta a ' + apiUrl +
            '. Definí VITE_API_URL con la URL HTTPS real antes de desplegar.'
        )
      }
    } catch {
      console.warn('[vite] VITE_API_URL no es una URL válida:', apiUrl)
    }
  }

  if (mode !== 'production') {
    origenes.push(
      'http://localhost:8000',
      'http://127.0.0.1:8000',
      'ws://localhost:5173',
      'ws://127.0.0.1:5173'
    )
  }

  return [...new Set(origenes)].join(' ')
}

function cspPlugin(mode) {
  const directivas = [
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data:",
    "font-src 'self' data:",
    `connect-src ${cspConnectSrc(mode)}`,
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'"
  ]

  if (mode === 'production') {
    directivas.push('upgrade-insecure-requests')
  }

  const csp = directivas.join('; ')

  return {
    name: 'univac-csp-meta',
    transformIndexHtml(html) {
      return html.replace(
        '</head>',
        `  <meta http-equiv="Content-Security-Policy" content="${csp}">\n  </head>`
      )
    }
  }
}

export default defineConfig(({ mode }) => ({
  plugins: [vue(), cspPlugin(mode)],
  server: {
    proxy: {
      '/auth': 'http://localhost:8000',
      '/reportes': 'http://localhost:8000',
      '/usuario': 'http://localhost:8000',
      '/empresa': 'http://localhost:8000',
      '/archivos': 'http://localhost:8000'
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
}))

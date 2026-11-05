import axios from 'axios'
import { limpiarSesion, obtenerCsrf } from './utils/sesion'

// La URL del backend se inyecta en tiempo de build desde la variable de
// entorno VITE_API_URL. Si viene vacia se usan rutas relativas al origen.
const API_URL = (import.meta.env.VITE_API_URL || '').trim().replace(/\/+$/, '')

if (!API_URL) {
  console.warn(
    '[api] VITE_API_URL no esta definida: las peticiones se haran al mismo origen. ' +
      'Definala en .env / .env.production (ver .env.example) o como variable de entorno en Vercel.'
  )
}

const api = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json'
  }
})

const METODOS_SEGUROS = new Set(['get', 'head', 'options'])

api.interceptors.request.use((config) => {
  const metodo = String(config.method || 'get').toLowerCase()
  if (!METODOS_SEGUROS.has(metodo)) {
    const csrf = obtenerCsrf()
    if (csrf) {
      config.headers['X-CSRF-Token'] = csrf
    }
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const url = err.config?.url || ''
    const esLogin = url.includes('/auth/login')
    const esSeleccion = url.includes('/auth/seleccionar-empresa')
    if (err.response && err.response.status === 401 && !esLogin && !esSeleccion) {
      limpiarSesion()
      if (window.location.pathname !== '/') {
        window.location.href = '/'
      }
    }
    const detalle = String(err.response?.data?.detail || '').toLowerCase()
    const sesionInvalida =
      err.response &&
      err.response.status === 403 &&
      (detalle.includes('no autorizado') || detalle.includes('csrf'))
    if (sesionInvalida) {
      limpiarSesion()
      if (window.location.pathname !== '/') {
        window.location.href = '/'
      }
    }
    return Promise.reject(err)
  }
)

export default api

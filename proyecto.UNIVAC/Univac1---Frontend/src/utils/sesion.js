export const CLAVES_SESION = [
  'sesion_activa',
  'usuario_id',
  'empresa_id',
  'ultima_empresa',
  'nombre',
  'usuario_nombre',
  'empresa_nombre',
  'empresa_activa',
  'visualiza_totales',
  'venta_rapida',
  'modifica_precio_venta',
  'scanner',
  'nivel_clave',
  'ordenamiento_articulos'
]

const CSRF_KEY = 'univac_csrf'
const CLAVES_OBSOLETAS = ['token', 'token_expiry']

export function guardarCsrf(token) {
  try {
    if (token) sessionStorage.setItem(CSRF_KEY, token)
  } catch {
  }
}

export function obtenerCsrf() {
  try {
    return sessionStorage.getItem(CSRF_KEY) || ''
  } catch {
    return ''
  }
}

export function limpiarSesion() {
  CLAVES_SESION.forEach((k) => localStorage.removeItem(k))
  CLAVES_OBSOLETAS.forEach((k) => localStorage.removeItem(k))
  try {
    sessionStorage.removeItem(CSRF_KEY)
  } catch {
  }
}

export function estaLogueado() {
  return (
    localStorage.getItem('sesion_activa') === '1' &&
    localStorage.getItem('nivel_clave') === '2'
  )
}

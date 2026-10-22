export const CLAVES_SESION = [
  'token',
  'token_expiry',
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

export function limpiarSesion() {
  CLAVES_SESION.forEach((k) => localStorage.removeItem(k))
}

import comprasAcumuladas from './comprasAcumuladas'
import { comprasProvincias, ventasProvincias, ventasZonas, ventasVendedor } from './porDimension'
import comprasProveedores from './comprasProveedores'
import comprasInsumos from './comprasInsumos'
import ventasTotales from './ventasTotales'
import ventasClientes from './ventasClientes'
import ventasProductos from './ventasProductos'
import comprasVentasArticulos from './comprasVentasArticulos'
import ventasComprobante from './ventasComprobante'
import gastos from './gastos'
import vendedoresRubros from './vendedoresRubros'
import vendedores from './vendedores'
import resultados from './resultados'

export const informes = [
  comprasAcumuladas,
  comprasProvincias,
  comprasProveedores,
  comprasInsumos,
  ventasTotales,
  ventasProvincias,
  ventasZonas,
  ventasVendedor,
  ventasClientes,
  ventasProductos,
  comprasVentasArticulos,
  ventasComprobante,
  gastos,
  vendedoresRubros,
  vendedores,
  resultados
]

export const porId = (id) => informes.find((i) => i.id === id)

export const config = (id) => {
  const cfg = porId(id)
  if (!cfg) throw new Error(`Informe desconocido: ${id}`)
  return cfg
}

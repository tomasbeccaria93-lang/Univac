export const grupos = [
  {
    key: 'compras',
    label: 'Compras',
    icon: 'fa-cart-shopping',
    items: [
      { to: '/dashboard/compras/acumuladas', label: 'Compras acumuladas', icon: 'fa-layer-group' },
      { to: '/dashboard/compras/provincias', label: 'Compras por Provincias', icon: 'fa-map-location-dot' },
      { to: '/dashboard/compras/proveedores', label: 'Compras a Proveedores en Pesos', icon: 'fa-truck' },
      { to: '/dashboard/compras/insumos?segundo=1', label: 'Compras por Artículos (Agrupado)', icon: 'fa-chart-pie' },
      { to: '/dashboard/compras/insumos?segundo=2', label: 'Compras por Artículos (Desagregado)', icon: 'fa-chart-simple' },
      { to: '/dashboard/compras/gastos', label: 'Gastos', icon: 'fa-receipt' }
    ]
  },
  {
    key: 'ventas',
    label: 'Ventas',
    icon: 'fa-file-invoice-dollar',
    items: [
      { to: '/dashboard/ventas/totales', label: 'Totales de Ventas', icon: 'fa-calculator' },
      { to: '/dashboard/ventas/provincias', label: 'Ventas por Provincias', icon: 'fa-map-location-dot' },
      { to: '/dashboard/ventas/zonas', label: 'Ventas por Zonas', icon: 'fa-map-marked-alt' },
      { to: '/dashboard/ventas/vendedor', label: 'Ventas por Vendedor en Pesos', icon: 'fa-user-tie' },
      { to: '/dashboard/ventas/vendedores', label: 'Ventas por Vendedor Agrupados por Rubros', icon: 'fa-money-bill-wave' },
      { to: '/dashboard/ventas/vendedores-rubros?segundo=1', label: 'Ventas por Vendedor por Rubros y Artículos (Agrupado)', icon: 'fa-bars' },
      { to: '/dashboard/ventas/vendedores-rubros?segundo=2', label: 'Ventas por Vendedor por Rubros y Artículos (Desagregado)', icon: 'fa-list' },
      { to: '/dashboard/ventas/clientes', label: 'Ventas a Clientes en Pesos', icon: 'fa-users' },
      { to: '/dashboard/ventas/productos?segundo=1', label: 'Ventas por Artículos (Agrupado)', icon: 'fa-box-open' },
      { to: '/dashboard/ventas/productos?segundo=2', label: 'Ventas por Artículos y Cliente', icon: 'fa-chart-simple' },
      { to: '/dashboard/ventas/comprobante', label: 'Ventas por Comprobante', icon: 'fa-file-invoice' }
    ]
  },
  {
    key: 'movimientos',
    label: 'Movimientos',
    icon: 'fa-arrows-rotate',
    items: [
      { to: '/dashboard/movimientos/compras-ventas', label: 'Compras y Ventas por Artículos', icon: 'fa-right-left' }
    ]
  },
  {
    key: 'resultados',
    label: 'Resultados',
    icon: 'fa-scale-balanced',
    items: [
      { to: '/dashboard/resultados/ventas?segundo=1', label: 'Resultado de Ventas (Agrupado, P.Costo)', icon: 'fa-chart-pie' },
      { to: '/dashboard/resultados/ventas?segundo=2', label: 'Resultado de Ventas (Desagregado, P.Costo)', icon: 'fa-chart-simple' },
      { to: '/dashboard/resultados/ventas?segundo=3', label: 'Resultado de Ventas (Agrupado, P.Última Compra)', icon: 'fa-chart-column' },
      { to: '/dashboard/resultados/ventas?segundo=4', label: 'Resultado de Ventas (Desagregado, P.Última Compra)', icon: 'fa-list' }
    ]
  }
]

export const itemsNoOriginal = [
  { to: '/dashboard/compras/iva', label: 'Posición Mensual de IVA', icon: 'fa-percent' },
  { to: '/dashboard/ventas/acumuladas', label: 'Ventas acumuladas', icon: 'fa-layer-group' },
  { to: '/dashboard/herramientas/comparativos', label: 'Comparativos', icon: 'fa-chart-column' },
  { to: '/dashboard/herramientas/cuenta', label: 'Cuentas Corrientes', icon: 'fa-money-check-dollar' },
  { to: '/dashboard/herramientas/facturacion', label: 'Facturación', icon: 'fa-file-invoice-dollar' },
  { to: '/dashboard/herramientas/indicadores', label: 'Indicadores', icon: 'fa-gauge-high' }
]

export function prefijoRuta(to) {
  return String(to).split('?')[0]
}

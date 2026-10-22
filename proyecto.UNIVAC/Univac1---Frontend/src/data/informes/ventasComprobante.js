import {
  colText, colDate, colMoney,
  sumCol, kpi, ranking, serieTemporal, colorVentas,
  graficoEvolucion, graficoRanking
} from './_helpers'

export default {
  id: 'ventas-comprobante',
  ques: 12,
  area: 'Ventas',
  titulo: 'Ventas por comprobante',
  descripcion: 'Cada comprobante de venta con su cliente, CUIT y totales.',
  endpoint: '/reportes/ventas/insumos-comprobante',
  excel: 'Ventas_Comprobante',
  mrad: true,
  mradInicial: 1,
  extract: (d) => d?.detalle || [],
  filtros: [{ key: 'cliente', label: 'Cliente', tipo: 'text', placeholder: 'Nombre de cliente' }],

  columnas: () => [
    colDate('fecha', 'Fecha'),
    colText('compro', 'Comprobante'),
    colText('nombre_cliente', 'Cliente'),
    colText('cuit', 'CUIT'),
    colMoney('ng', 'Neto Gravado'),
    colMoney('iv', 'IVA'),
    colMoney('otros', 'Otros'),
    colMoney('tot', 'T.Comprob.'),
    colText('id', '', { align: 'right', searchable: false }),
    colMoney('totus', 'USD')
  ],

  kpis: (f) => [
    kpi('Comprobantes', new Set(f.map((x) => String(x.compro ?? ''))).size, 'entero'),
    kpi('Clientes', new Set(f.map((x) => String(x.nombre_cliente ?? 'Sin informar'))).size, 'entero'),
    kpi('Neto gravado', sumCol(f, 'ng')),
    kpi('IVA', sumCol(f, 'iv')),
    kpi('Total', sumCol(f, 'tot'))
  ],

  graficos: (f, ctx) => {
    const charts = []
    const serie = serieTemporal(f, { fechaKey: 'fecha', valorKey: 'tot', granularidad: ctx.granularidad })
    if (serie.length) {
      charts.push(graficoEvolucion({
        titulo: 'Total de ventas por fecha',
        subtitulo: ctx.subtitulo,
        serie,
        color: colorVentas()
      }))
    }
    const rank = ranking(f, 'nombre_cliente', 'tot', { limite: 12 })
    if (rank.length) {
      charts.push(graficoRanking({
        titulo: `Top ${Math.min(10, rank.length)} clientes por total`,
        subtitulo: ctx.subtitulo,
        items: rank,
        color: colorVentas(),
        limite: 10
      }))
    }
    return charts
  }
}

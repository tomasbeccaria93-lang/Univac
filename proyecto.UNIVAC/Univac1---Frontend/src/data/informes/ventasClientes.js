import {
  colText, colDate, colMoney, colPercent,
  sumCol, kpi, ranking, serieTemporal, seriePorMesAno, colorVentas,
  graficoEvolucion, graficoRanking
} from './_helpers'

export default {
  id: 'ventas-clientes',
  ques: 9,
  area: 'Ventas',
  titulo: 'Ventas a clientes en pesos',
  descripcion: 'Ventas por cliente con zona, esporádico y participación porcentual. El original no excluye anulados.',
  endpoint: '/reportes/ventas/clientes_totales',
  excel: 'Ventas_Clientes',
  mrad: true,
  mradInicial: 1,
  extract: (d) => (Array.isArray(d) ? d : d?.detalle || []),
  filtros: [{ key: 'cliente', label: 'Cliente', tipo: 'text', placeholder: 'Nombre de cliente' }],

  columnas: (mrad) => [
    ...(mrad === 1
      ? [colText('mes_imputacion', 'Mes'), colText('ano_imputacion', 'Año')]
      : [colDate('fecha', 'Fecha')]),
    colText('cliente', 'Cliente'),
    colText('espo', 'Esporádico'),
    colMoney('ng', 'Neto Gravado'),
    colMoney('iv', 'IVA'),
    colMoney('otros', 'Otros'),
    colMoney('tot', 'Total'),
    // El original oculta la columna 10 en mRAD 1 y 2 (lHide := .T.).
    ...(mrad === 3 || mrad === 4 ? [colPercent('porcentaje', 'Part.', { total: false })] : []),
    colText('zona', 'Zona')
  ],

  kpis: (f) => [
    kpi('Clientes', new Set(f.map((x) => String(x.cliente ?? 'Sin informar'))).size, 'entero'),
    kpi('Neto gravado', sumCol(f, 'ng')),
    kpi('IVA', sumCol(f, 'iv')),
    kpi('Otros', sumCol(f, 'otros')),
    kpi('Total', sumCol(f, 'tot'))
  ],

  graficos: (f, ctx) => {
    const charts = []

    const serie = ctx.mrad !== 1
      ? serieTemporal(f, { fechaKey: 'fecha', valorKey: 'tot', granularidad: ctx.granularidad })
      : seriePorMesAno(f, 'tot')
    if (serie.length > 1) {
      charts.push(graficoEvolucion({
        titulo: 'Ventas por período',
        subtitulo: ctx.subtitulo,
        serie,
        color: colorVentas()
      }))
    }

    const rank = ranking(f, 'cliente', 'tot', { limite: 12 })
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

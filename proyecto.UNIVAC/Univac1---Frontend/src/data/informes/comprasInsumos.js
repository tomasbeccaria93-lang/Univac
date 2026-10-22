import {
  colText, colDate, colNumber, colMoney,
  sumCol, countCol, kpi, ranking, participacion, serieTemporal, colorCompras
} from './_helpers'

export default {
  id: 'compras-insumos',
  ques: 4,
  area: 'Compras',
  titulo: 'Compras por insumos, artículos o productos',
  descripcion: 'Compras y notas de crédito por artículo, con rubro, unidad de medida, precio, bonificación y total.',
  endpoint: '/reportes/compras/insumos',
  excel: 'Compras_Insumos',
  mrad: true,
  mradInicial: 1,
  segundoInicial: 1,
  labelVariante: 'Agrupación',
  variantes: [
    { value: 1, desc: 'Agrupado', titulo: 'Agrupado por artículo y unidad de medida' },
    { value: 2, desc: 'Desagregado', titulo: 'Una fila por movimiento' }
  ],
  filtros: [
    { key: 'insumo', label: 'Artículo', tipo: 'text', placeholder: 'Descripción o código' },
    { key: 'rubro', label: 'Rubro', tipo: 'text', placeholder: 'Nombre del rubro' }
  ],
  extract: (d) => (Array.isArray(d) ? d : d?.detalle || []),

  columnas: (mrad, segundo) => {
    // El original (QUES=4) imprime c.precio_real cuando SEGUNDO=1 y el importe
    // de la linea round(cantidad*precio*(100-bonif)/100,2) cuando SEGUNDO=2.
    const desagregado = segundo === 2 && (mrad === 1 || mrad === 2)
    const colImporteReal = desagregado
      ? { key: 'precio_total', label: 'Importe' }
      : { key: 'precio_real', label: 'Precio real' }
    return [
      colText('ide', 'Tipo'),
      colText('codigo_de_barras', 'Código de barras'),
      colText('nom', 'Artículo'),
      colText('tip', 'Tipo art.'),
      colText('rub', 'Rubro'),
      colDate('fecha', 'Fecha'),
      colNumber('cant', 'Cantidad'),
      colMoney('precio', 'Precio'),
      colNumber('bonificacion', 'Bonif. %'),
      colMoney(colImporteReal.key, colImporteReal.label),
      colText('uni', 'Unidad'),
      colText('ali', 'Alícuota'),
      colText('pro', 'Proveedor'),
      colText('espo', 'Esporádico'),
      colText('comprobante', 'Comprobante'),
      colMoney('tot', 'Total')
    ]
  },

  kpis: (f) => [
    kpi('Artículos', new Set(f.map((x) => String(x.nom ?? 'Sin informar'))).size, 'entero'),
    kpi('Cantidad total', countCol(f, 'cant'), 'numero'),
    kpi('Total comprado', sumCol(f, 'tot'))
  ],

  graficos: (f, ctx) => {
    const charts = []

    const serie = serieTemporal(f, { fechaKey: 'fecha', valorKey: 'tot', granularidad: ctx.granularidad })
    if (serie.length > 1) {
      charts.push({
        titulo: 'Compra por período',
        subtitulo: ctx.subtitulo,
        tipo: 'line',
        labels: serie.map((s) => s.etiqueta),
        datasets: [{ label: 'Total', data: serie.map((s) => s.valor), color: colorCompras() }]
      })
    }

    const rank = ranking(f, 'nom', 'tot', { limite: 10 })
    if (rank.length) {
      charts.push({
        titulo: `Top ${Math.min(10, rank.length)} artículos por monto`,
        subtitulo: ctx.subtitulo,
        tipo: 'barHorizontal',
        orientacion: 'h',
        alto: Math.max(200, Math.min(rank.length, 10) * 26 + 60),
        labels: rank.map((r) => r.label),
        datasets: [{ label: 'Total', data: rank.map((r) => r.valor), color: colorCompras() }]
      })
    }
    const porRubro = participacion(f, 'rub', 'tot').filter((p) => p.valor > 0)
    if (porRubro.length > 1) {
      charts.push({
        titulo: 'Participación por rubro',
        subtitulo: ctx.subtitulo,
        tipo: 'doughnut',
        labels: porRubro.map((p) => p.label),
        datasets: [{ label: 'Total', data: porRubro.map((p) => p.valor) }]
      })
    }
    return charts
  }
}

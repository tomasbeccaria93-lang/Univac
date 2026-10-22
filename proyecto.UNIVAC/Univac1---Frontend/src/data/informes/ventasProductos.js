import {
  colText, colDate, colNumber, colMoney,
  sumCol, countCol, kpi, ranking, comparativo, serieTemporal, colorSerie, colorVentas,
  graficoEvolucion, graficoRanking
} from './_helpers'

export default {
  id: 'ventas-productos',
  ques: 10,
  area: 'Ventas',
  titulo: 'Ventas por insumos, artículos o productos',
  descripcion: 'Ventas por artículo con cantidad, costo, precio, bonificación y utilidad calculada por el original.',
  endpoint: '/reportes/ventas/insumos',
  excel: 'Ventas_Productos',
  mrad: true,
  mradInicial: 1,
  segundoInicial: 1,
  labelVariante: 'Agrupación',
  variantes: [
    { value: 1, desc: 'Por artículo', titulo: 'Agrupado por artículo y unidad de medida' },
    { value: 2, desc: 'Por cliente', titulo: 'Desagregado por artículo y cliente' }
  ],
  filtros: [{ key: 'rubro', label: 'Rubro', tipo: 'text', placeholder: 'Nombre del rubro' }],
  extract: (d) => (Array.isArray(d) ? d : d?.detalle || []),

  columnas: () => [
    colText('ide', 'Tipo'),
    colText('codigo_de_barras', 'Código de barras'),
    colText('nom', 'Artículo'),
    colText('tip', 'Tipo art.'),
    colText('rub', 'Rubro'),
    colDate('fecha_movimiento', 'Fecha'),
    colMoney('precio_costo', 'Costo'),
    colNumber('cant', 'Cantidad'),
    colMoney('precio', 'Precio'),
    colNumber('bonificacion', 'Bonif. %'),
    colMoney('precio_real', 'Precio real'),
    colText('uni', 'Unidad'),
    colText('ali', 'Alícuota'),
    colText('pro', 'Cliente'),
    colText('espo', 'Esporádico'),
    colText('comprobante', 'Comprobante'),
    colMoney('tot', 'Venta'),
    colMoney('utilidad', 'Utilidad'),
    colNumber('tipo_cambio', 'Tipo Cambio')
  ],

  kpis: (f) => [
    kpi('Artículos', new Set(f.map((x) => String(x.nom ?? 'Sin informar'))).size, 'entero'),
    kpi('Cantidad total', countCol(f, 'cant'), 'numero'),
    kpi('Venta total', sumCol(f, 'tot')),
    kpi('Utilidad total', sumCol(f, 'utilidad'))
  ],

  graficos: (f, ctx) => {
    const charts = []

    const serie = serieTemporal(f, {
      fechaKey: 'fecha_movimiento',
      valorKey: 'tot',
      granularidad: ctx.granularidad
    })
    if (serie.length > 1) {
      charts.push(graficoEvolucion({
        titulo: 'Venta por período',
        subtitulo: ctx.subtitulo,
        serie,
        color: colorVentas(),
        labelTotal: 'Venta'
      }))
    }

    const rank = ranking(f, 'nom', 'tot', { limite: 21 })
    if (rank.length) {
      charts.push(graficoRanking({
        titulo: `Top ${Math.min(10, rank.length)} artículos por venta`,
        subtitulo: ctx.subtitulo,
        items: rank,
        color: colorVentas(),
        label: 'Venta',
        limite: 10
      }))
    }

    const porUtilidad = ranking(f, 'nom', 'utilidad', { limite: 21 }).filter((r) => r.valor !== 0)
    if (porUtilidad.length) {
      charts.push(graficoRanking({
        titulo: 'Top artículos por utilidad',
        subtitulo: ctx.subtitulo,
        items: porUtilidad,
        color: colorSerie(0),
        label: 'Utilidad',
        limite: 10
      }))
    }

    const cmp = comparativo(f, 'nom', [
      { key: 'precio_costo', label: 'Costo' },
      { key: 'precio', label: 'Precio de venta' }
    ])
    const top10 = cmp.labels.slice(0, 10)
    if (top10.length) {
      charts.push({
        titulo: 'Costo contra precio de venta (Top 10 artículos)',
        subtitulo: ctx.subtitulo,
        tipo: 'bar',
        labels: top10,
        datasets: [
          { label: 'Costo', data: cmp.out.slice(0, 10).map((o) => o.valores.precio_costo || 0), color: colorSerie(1) },
          { label: 'Precio de venta', data: cmp.out.slice(0, 10).map((o) => o.valores.precio || 0), color: colorVentas() }
        ]
      })
    }

    return charts.slice(0, 4)
  }
}

import {
  colText, colDate, colNumber, colMoney,
  sumCol, countCol, kpi, comparativo, serieTemporalMultivalor, colorSerie, colorVentas
} from './_helpers'

export default {
  id: 'resultados',
  ques: 16,
  area: 'Resultados',
  titulo: 'Resultado de ventas',
  descripcion: 'Venta menos costo o menos precio de última compra, por artículo.',
  endpoint: '/reportes/resultados/ventas',
  excel: 'Resultado_de_Ventas',
  mrad: true,
  mradInicial: 1,
  segundoInicial: 1,
  conSucursal: false,
  labelVariante: 'Criterio',
  variantes: [
    { value: 1, desc: 'Agrupado, P. Costo', titulo: 'Agrupado por artículo, venta menos precio de costo' },
    { value: 2, desc: 'Desagregado, P. Costo', titulo: 'Desagregado, venta menos precio de costo' },
    { value: 3, desc: 'Agrupado, P. Última compra', titulo: 'Agrupado por artículo, venta menos última compra' },
    { value: 4, desc: 'Desagregado, P. Última compra', titulo: 'Desagregado, venta menos última compra' }
  ],
  filtros: [
    {
      key: 'estado',
      label: 'Estado',
      tipo: 'select',
      placeholder: 'Original',
      soloSi: (mrad, segundo) => segundo === 3 || segundo === 4,
      opciones: [
        { value: '0', label: 'Precio de última compra' },
        { value: '1', label: 'Precio de última compra (valor > 0)' }
      ]
    }
  ],
  extract: (d) => d?.detalle || [],

  columnas: () => [
    colDate('fecha', 'Fecha'),
    colNumber('cant', 'Cantidad'),
    colText('codigo_de_barras', 'Código de barras'),
    colText('nom', 'Artículo'),
    colMoney('prc', 'Precio de costo'),
    colMoney('precio', 'Precio de venta'),
    colMoney('tot1', 'Venta'),
    colMoney('tot2', 'Resultado')
  ],

  kpis: (f) => {
    const venta = sumCol(f, 'tot1')
    const resultado = sumCol(f, 'tot2')
    return [
      kpi('Artículos', new Set(f.map((x) => String(x.nom ?? 'Sin informar'))).size, 'entero'),
      kpi('Cantidad total', countCol(f, 'cant'), 'numero'),
      kpi('Venta total', venta),
      kpi('Resultado', resultado),
      kpi('Margen', venta ? (resultado / venta) * 100 : 0, 'porcentaje')
    ]
  },

  graficos: (f, ctx) => {
    const charts = []

    const porPeriodo = serieTemporalMultivalor(f, {
      fechaKey: 'fecha',
      granularidad: ctx.granularidad,
      claves: ['tot1', 'tot2'],
      labels: { tot1: 'Venta', tot2: 'Resultado' }
    })

    if (porPeriodo.labels.length) {
      charts.push({
        titulo: 'Venta contra resultado por período',
        subtitulo: ctx.subtitulo,
        tipo: 'bar',
        labels: porPeriodo.labels,
        datasets: [
          { label: 'Venta', data: porPeriodo.series[0].data, color: colorVentas(), render: 'bar' },
          { label: 'Resultado', data: porPeriodo.series[1].data, color: colorSerie(0) }
        ]
      })
    }

    const porArticulo = comparativo(f, 'nom', [
      { key: 'tot1', label: 'Venta' },
      { key: 'tot2', label: 'Resultado' }
    ])
    const topArt = porArticulo.labels.slice(0, 10)
    if (topArt.length) {
      const idx = porArticulo.labels.map((l, i) => ({ l, i }))
        .filter((o) => topArt.includes(o.l))
        .map((o) => o.i)
      charts.push({
        titulo: 'Venta contra resultado por artículo (Top 10)',
        subtitulo: ctx.subtitulo,
        tipo: 'bar',
        labels: topArt,
        datasets: [
          {
            label: 'Venta',
            data: idx.map((i) => porArticulo.out[i].valores.tot1 || 0),
            color: colorVentas()
          },
          {
            label: 'Resultado',
            data: idx.map((i) => porArticulo.out[i].valores.tot2 || 0),
            color: colorSerie(0)
          }
        ]
      })
    }

    const porMargen = f
      .map((r) => ({
        label: String(r.nom ?? 'Sin informar'),
        venta: Number(r.tot1) || 0,
        resultado: Number(r.tot2) || 0
      }))
      .filter((r) => r.venta > 0)
      .reduce((acc, r) => {
        const p = acc.get(r.label) || { label: r.label, venta: 0, resultado: 0 }
        p.venta += r.venta
        p.resultado += r.resultado
        acc.set(r.label, p)
        return acc
      }, new Map())

    const conMargen = [...porMargen.values()]
      .map((r) => ({ ...r, margen: (r.resultado / r.venta) * 100 }))
      .sort((a, b) => b.margen - a.margen)

    const topMargen = conMargen.slice(0, 10)
    const bottomMargen = conMargen.slice(-10).reverse()
    const margenGrafico = [...topMargen, ...bottomMargen.filter((b) => !topMargen.includes(b))]

    if (margenGrafico.length) {
      charts.push({
        titulo: `Margen por artículo (Top ${Math.min(10, topMargen.length)} y Bottom ${Math.min(10, bottomMargen.length)})`,
        subtitulo: `${ctx.subtitulo} — resultado sobre venta`,
        tipo: 'barHorizontal',
        orientacion: 'h',
        unidad: 'porcentaje',
        alto: Math.max(200, margenGrafico.length * 22 + 60),
        labels: margenGrafico.map((r) => r.label),
        datasets: [
          {
            label: 'Margen',
            data: margenGrafico.map((r) => Number(r.margen.toFixed(2))),
            color: colorSerie(3)
          }
        ]
      })
    }

    return charts
  }
}

import {
  colText, colDate, colNumber, colMoney,
  sumCol, kpi, ranking, serieTemporalMultivalor, colorVentas, colorCompras,
  graficoRanking
} from './_helpers'

export default {
  id: 'compras-ventas-articulos',
  ques: 11,
  area: 'Movimientos',
  titulo: 'Compras y ventas por insumos, artículos o productos',
  descripcion: 'Compras y ventas de cada artículo en un mismo listado, con el signo según identificación.',
  endpoint: '/reportes/insumos/compras-ventas',
  excel: 'Compras_Ventas_Articulos',
  mrad: true,
  mradInicial: 1,
  filtros: [
    { key: 'rubro', label: 'Rubro', tipo: 'text', placeholder: 'Nombre del rubro' },
    {
      key: 'estado',
      label: 'Estado',
      tipo: 'select',
      placeholder: 'Original',
      opciones: [
        { value: '0', label: 'Precio de última compra' },
        { value: '1', label: 'Precio de última compra (valor > 0)' }
      ]
    }
  ],

  extract: (d) => (Array.isArray(d) ? d : d?.detalle || []),

  columnas: () => [
    colText('ide', 'Tipo'),
    colText('codigo_de_barras', 'Código de barras'),
    colText('nom', 'Artículo'),
    colText('tip', 'Tipo art.'),
    colText('rub', 'Rubro'),
    colDate('fecha', 'Fecha'),
    colNumber('cant', 'Cantidad'),
    colMoney('precio', 'Precio'),
    colNumber('bonificacion', 'Bonif. %'),
    colMoney('precio_real', 'Precio real'),
    colText('uni', 'Unidad'),
    colText('ali', 'Alícuota'),
    colText('pro', 'Proveedor'),
    colText('espo', 'Esporádico'),
    colText('comprobante', 'Comprobante'),
    colMoney('tot', 'Total')
  ],

  kpis: (f) => [
    kpi('Artículos', new Set(f.map((x) => String(x.nom ?? 'Sin informar'))).size, 'entero'),
    kpi('Renglones', f.length, 'entero'),
    kpi('Monto total', sumCol(f, 'tot'))
  ],

  graficos: (f, ctx) => {
    const charts = []

    const serie = serieTemporalMultivalor(
      f.map((r) => ({
        fecha: r.fecha,
        compra: r.ide === 'Compra' ? Number(r.tot) || 0 : 0,
        venta: r.ide === 'Compra' ? 0 : Number(r.tot) || 0
      })),
      {
        fechaKey: 'fecha',
        granularidad: ctx.granularidad,
        claves: ['compra', 'venta'],
        labels: { compra: 'Compras', venta: 'Ventas' }
      }
    )

    if (serie.labels.length > 1) {
      charts.push({
        titulo: 'Compras y ventas por período',
        subtitulo: ctx.subtitulo,
        tipo: 'bar',
        labels: serie.labels,
        datasets: [
          { label: 'Compras', data: serie.series[0].data, color: colorCompras() },
          { label: 'Ventas', data: serie.series[1].data, color: colorVentas() }
        ]
      })
    }

    const porArticulo = new Map()
    for (const r of f) {
      const nom = String(r.nom ?? 'Sin informar')
      if (!porArticulo.has(nom)) porArticulo.set(nom, { label: nom, compra: 0, venta: 0 })
      const o = porArticulo.get(nom)
      if (r.ide === 'Compra') o.compra += Number(r.tot) || 0
      else o.venta += Number(r.tot) || 0
    }
    const top = [...porArticulo.values()]
      .sort((a, b) => Math.max(b.compra, b.venta) - Math.max(a.compra, a.venta))
      .slice(0, 10)

    if (top.length) {
      charts.push({
        titulo: 'Compra contra venta por artículo (Top 10)',
        subtitulo: ctx.subtitulo,
        tipo: 'bar',
        labels: top.map((t) => t.label),
        datasets: [
          { label: 'Compra', data: top.map((t) => t.compra), color: colorCompras() },
          { label: 'Venta', data: top.map((t) => t.venta), color: colorVentas() }
        ]
      })
    }

    const porTipo = ranking(f, 'ide', 'tot', { limite: 10 }).filter((r) => r.valor !== 0)
    if (porTipo.length) {
      charts.push(graficoRanking({
        titulo: 'Participación por tipo de movimiento',
        subtitulo: ctx.subtitulo,
        items: porTipo,
        color: colorVentas(),
        limite: 10
      }))
    }

    return charts
  }
}

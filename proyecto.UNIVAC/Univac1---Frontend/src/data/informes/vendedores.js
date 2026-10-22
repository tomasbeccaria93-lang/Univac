import {
  colText, colDate, colMoney,
  sumCol, kpi, ranking, serieTemporal, apiladoPor, colorSerie, colorVentas,
  graficoEvolucion, graficoRanking
} from './_helpers'

export default {
  id: 'vendedores',
  ques: 14,
  area: 'Resultados',
  titulo: 'Ventas por vendedores',
  descripcion: 'Ventas por vendedor y rubro, con neto gravado, IVA, otros impuestos y total. Al filtrar por rubro el original recalcula desde el detalle de comprobantes y fija Otros en 0.',
  endpoint: '/reportes/ventas/vendedores',
  excel: 'Ventas_Vendedores',
  mrad: true,
  mradInicial: 1,
  conSucursal: false,
  extract: (d) => d?.detalle || [],
  filtros: [{ key: 'rubro', label: 'Rubro', tipo: 'text', placeholder: 'Todos los rubros' }],

  columnas: (mrad) => [
    ...(mrad === 1
      ? [colText('mes_imputacion', 'Mes'), colText('ano_imputacion', 'Año')]
      : [colDate('fecha', 'Fecha')]),
    colText('vendedor', 'Vendedor'),
    colText('rubro', 'Rubro'),
    colMoney('ng', 'Neto Gravado'),
    colMoney('iv', 'IVA'),
    colMoney('otros', 'Otros'),
    colMoney('tot', 'Total')
  ],

  kpis: (f) => [
    kpi('Vendedores', new Set(f.map((x) => String(x.vendedor ?? 'Sin informar'))).size, 'entero'),
    kpi('Rubros', new Set(f.map((x) => String(x.rubro ?? 'Todos los rubros'))).size, 'entero'),
    kpi('Neto gravado', sumCol(f, 'ng')),
    kpi('Otros impuestos', sumCol(f, 'otros')),
    kpi('Total', sumCol(f, 'tot'))
  ],

  graficos: (f, ctx) => {
    const charts = []

    const rank = ranking(f, 'vendedor', 'tot', { limite: 21 })
    if (rank.length) {
      charts.push(graficoRanking({
        titulo: `Top ${Math.min(10, rank.length)} vendedores por total`,
        subtitulo: ctx.subtitulo,
        items: rank,
        color: colorVentas(),
        limite: 10
      }))
    }

    const agg = new Map()
    for (const r of f) {
      const rub = String(r.rubro ?? 'Todos los rubros')
      if (!agg.has(rub)) agg.set(rub, { label: rub, valor: 0 })
      agg.get(rub).valor += Number(r.tot) || 0
    }
    const porRubro = [...agg.values()].filter((x) => x.valor > 0).sort((a, b) => b.valor - a.valor)
    if (porRubro.length > 1) {
      charts.push(graficoRanking({
        titulo: 'Participación por rubro',
        subtitulo: ctx.subtitulo,
        items: porRubro,
        color: colorVentas(),
        limite: 10
      }))
    }

    const serie = serieTemporal(f, { fechaKey: 'fecha', valorKey: 'tot', granularidad: ctx.granularidad })
    if (serie.length > 1) {
      charts.push(graficoEvolucion({
        titulo: 'Total de ventas por período',
        subtitulo: ctx.subtitulo,
        serie,
        color: colorVentas()
      }))
    }

    const matriz = apiladoPor(f, 'vendedor', 'rubro', 'tot', { limiteFila: 5 })
    if (matriz.labels.length > 1 && matriz.series.length > 1) {
      const conTotal = matriz.series
        .map((s) => ({ ...s, suma: s.data.reduce((a, b) => a + b, 0) }))
        .sort((a, b) => b.suma - a.suma)
      const topRubros = conTotal.slice(0, 6)
      const resto = conTotal.slice(6)
      const sumaResto = matriz.labels.map((_, i) =>
        resto.reduce((a, s) => a + (s.data[i] || 0), 0)
      )
      const series = topRubros.map((s, i) => ({ label: s.label, data: s.data, color: colorSerie(i) }))
      if (resto.length && sumaResto.some((v) => v !== 0)) {
        series.push({ label: 'Otros rubros', data: sumaResto, color: colorSerie(6) })
      }
      charts.push({
        titulo: 'Rubros por vendedor (Top 5 vendedores)',
        subtitulo: ctx.subtitulo,
        tipo: 'bar',
        apilado: true,
        labels: matriz.labels,
        datasets: series
      })
    }

    return charts
  }
}

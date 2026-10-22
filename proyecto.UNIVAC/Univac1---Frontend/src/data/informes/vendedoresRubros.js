import {
  colText, colNumber, colMoney,
  sumCol, countCol, kpi, ranking, apiladoPor, colorSerie, colorVentas,
  graficoRanking
} from './_helpers'
import { fmtNum, fmtMoney } from '../../utils/format'

export default {
  id: 'vendedores-rubros',
  ques: 15,
  area: 'Resultados',
  titulo: 'Ventas por vendedores por rubros y artículos',
  descripcion: 'Detalle de ventas por vendedor, rubro y artículo, con unidad de medida y total.',
  endpoint: '/reportes/ventas/vendedores-rubros',
  excel: 'Ventas_Vendedores_Rubros',
  mrad: true,
  mradInicial: 1,
  segundoInicial: 1,
  conSucursal: false,
  labelVariante: 'Agrupación',
  variantes: [
    { value: 1, desc: 'Agrupado', titulo: 'Agrupado por artículo y unidad de medida' },
    { value: 2, desc: 'Desagregado', titulo: 'Una fila por movimiento' }
  ],
  filtros: [{ key: 'vendedor', label: 'Vendedor', tipo: 'text', placeholder: 'Todos los vendedores' }],
  extract: (d) => d?.detalle || [],

  columnas: () => [
    colText('vend', 'Vendedor'),
    colText('rub', 'Rubro'),
    colText('codigo_de_barras', 'Código de barras'),
    colText('nom', 'Artículo'),
    colText('uni', 'Unidad'),
    colNumber('cant', 'Cantidad', { render: (f) => (f.filaSubtotal ? '' : fmtNum(f.cant)) }),
    colMoney('precio', 'Precio', { render: (f) => (f.filaSubtotal ? '' : fmtMoney(f.precio)) }),
    colNumber('bonificacion', 'Bonif. %', { render: (f) => (f.filaSubtotal ? '' : fmtNum(f.bonificacion)) }),
    colMoney('tot', 'Total', { render: (f) => (f.filaSubtotal && f.tot == null ? '' : fmtMoney(f.tot)) })
  ],

  kpis: (filas) => {
    const f = filas.filter((x) => !x.filaSubtotal)
    return [
      kpi('Vendedores', new Set(f.map((x) => String(x.vend ?? 'Sin informar'))).size, 'entero'),
      kpi('Artículos', new Set(f.map((x) => String(x.nom ?? 'Sin informar'))).size, 'entero'),
      kpi('Cantidad total', countCol(f, 'cant'), 'numero'),
      kpi('Total vendido', sumCol(f, 'tot'))
    ]
  },

  graficos: (filas, ctx) => {
    const f = filas.filter((x) => !x.filaSubtotal)
    const charts = []

    const porRubro = ranking(f, 'rub', 'tot', {}).filter((p) => p.valor > 0)
    if (porRubro.length > 1) {
      charts.push(graficoRanking({
        titulo: 'Participación por rubro',
        subtitulo: ctx.subtitulo,
        items: porRubro,
        color: colorVentas(),
        limite: 10
      }))
    }

    const matriz = apiladoPor(f, 'vend', 'rub', 'tot', { limiteFila: 5 })
    if (matriz.labels.length > 1 && matriz.series.length > 1) {
      const conTotal = matriz.series
        .map((s) => ({ ...s, suma: s.data.reduce((a, b) => a + b, 0) }))
        .sort((a, b) => b.suma - a.suma)
      const topRubros = conTotal.slice(0, 6)
      const resto = conTotal.slice(6)
      const sumaResto = matriz.labels.map((_, i) =>
        resto.reduce((a, s) => a + (s.data[i] || 0), 0)
      )
      const series = topRubros.map((s) => ({ label: s.label, data: s.data }))
      if (resto.length && sumaResto.some((v) => v !== 0)) {
        series.push({ label: 'Otros rubros', data: sumaResto })
      }
      charts.push({
        titulo: 'Rubros por vendedor (Top 5 vendedores)',
        subtitulo: ctx.subtitulo,
        tipo: 'bar',
        apilado: true,
        labels: matriz.labels,
        datasets: series.map((s, i) => ({ label: s.label, data: s.data, color: colorSerie(i) }))
      })
    }

    const rank = ranking(f, 'vend', 'tot', { limite: 21 })
    if (rank.length) {
      charts.push(graficoRanking({
        titulo: `Top ${Math.min(10, rank.length)} vendedores por total`,
        subtitulo: ctx.subtitulo,
        items: rank,
        color: colorVentas(),
        limite: 10
      }))
    }

    const porArticulo = ranking(f, 'nom', 'tot', { limite: 21 })
    if (porArticulo.length) {
      charts.push(graficoRanking({
        titulo: `Top ${Math.min(10, porArticulo.length)} artículos por total`,
        subtitulo: ctx.subtitulo,
        items: porArticulo,
        color: colorSerie(2),
        limite: 10
      }))
    }

    return charts
  }
}

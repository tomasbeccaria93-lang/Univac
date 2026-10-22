import {
  colText, colDate, colMoney,
  sumCol, kpi, ranking, serieTemporal, colorCompras,
  graficoEvolucion, graficoRanking
} from './_helpers'

export default {
  id: 'gastos',
  ques: 13,
  area: 'Compras',
  titulo: 'Gastos',
  descripcion: 'Gastos por cuenta contable, combinando compras y otros egresos.',
  endpoint: '/reportes/gastos/detalle',
  excel: 'Gastos',
  mrad: true,
  mradInicial: 1,
  extract: (d) => d?.detalle || [],

  columnas: () => [
    colText('mes', 'Mes'),
    colText('ano', 'Año'),
    colDate('fecha', 'Fecha'),
    colText('cuenta', 'Cuenta'),
    colMoney('importe', 'Importe'),
    colText('tipo', 'Origen')
  ],

  kpis: (f) => [
    kpi('Cuentas', new Set(f.map((x) => String(x.cuenta ?? 'Sin informar'))).size, 'entero'),
    kpi('Renglones', f.length, 'entero'),
    kpi('Total gastos', sumCol(f, 'importe'))
  ],

  graficos: (f, ctx) => {
    const charts = []
    const rank = ranking(f, 'cuenta', 'importe', { limite: 12 })
    if (rank.length) {
      charts.push(graficoRanking({
        titulo: `Top ${Math.min(10, rank.length)} cuentas por importe`,
        subtitulo: ctx.subtitulo,
        items: rank,
        color: colorCompras(),
        label: 'Importe',
        limite: 10
      }))
    }
    const serie = serieTemporal(f, { fechaKey: 'fecha', valorKey: 'importe', granularidad: ctx.granularidad })
    if (serie.length) {
      charts.push(graficoEvolucion({
        titulo: 'Gasto por período',
        subtitulo: ctx.subtitulo,
        serie,
        color: colorCompras(),
        labelTotal: 'Importe'
      }))
    }
    return charts
  }
}

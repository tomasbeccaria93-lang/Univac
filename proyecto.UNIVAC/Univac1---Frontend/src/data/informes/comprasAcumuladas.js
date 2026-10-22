import {
  colText, colDate, colMoney, colInt,
  sumCol, countCol, kpi,
  serieTemporal, serieTemporalMultivalor,
  seriePorMesAno, apiladoPorMesAno,
  colorSerie, colorCompras, graficoEvolucion
} from './_helpers'

const ETIQUETAS = {
  ng: 'Neto Gravado', iv: 'IVA', piva: 'Perc. IVA', pib: 'Perc. IIBB',
  pex: 'Exento', cng: 'C. No Grav.', imp: 'Imp. Internos', rg: 'Ret. Ganancias',
  otros: 'Otros', tot: 'Total'
}

const PERIODOS = ['ng', 'iv', 'piva', 'pib', 'pex', 'cng']

export default {
  id: 'compras-acumuladas',
  ques: 1,
  area: 'Compras',
  titulo: 'Compras acumuladas',
  descripcion: 'Neto gravado, IVA, percepciones, exento y total de compras agrupados por período o en detalle.',
  endpoint: '/reportes/compras/acumuladas',
  excel: 'Compras_Acumuladas',
  mrad: true,
  mradInicial: 1,
  extract: (d) => (Array.isArray(d) ? d : d?.detalle || []),

  columnas: (mrad) => [
    ...(mrad === 1
      ? [colText('mes_imputacion', 'Mes'), colText('ano_imputacion', 'Año')]
      : [colDate('fecha', 'Fecha')]),
    colInt('cantidad', 'Mov.'),
    colMoney('ng', ETIQUETAS.ng),
    colMoney('iv', ETIQUETAS.iv),
    colMoney('piva', ETIQUETAS.piva),
    colMoney('pib', ETIQUETAS.pib),
    colMoney('pex', ETIQUETAS.pex),
    colMoney('cng', ETIQUETAS.cng),
    colMoney('tot', ETIQUETAS.tot)
  ],

  kpis: (f) => [
    kpi('Movimientos', countCol(f, 'cantidad'), 'entero'),
    kpi('Neto gravado', sumCol(f, 'ng')),
    kpi('IVA', sumCol(f, 'iv')),
    kpi('Percepciones', sumCol(f, 'piva') + sumCol(f, 'pib')),
    kpi('Total', sumCol(f, 'tot'))
  ],

  graficos: (f, ctx) => {
    const porFecha = ctx.mrad !== 1
    const serie = porFecha
      ? serieTemporal(f, { fechaKey: 'fecha', valorKey: 'tot', granularidad: ctx.granularidad })
      : seriePorMesAno(f, 'tot')
    if (!serie.length) return []

    const apilado = porFecha
      ? serieTemporalMultivalor(f, {
          fechaKey: 'fecha',
          granularidad: ctx.granularidad,
          claves: PERIODOS,
          labels: ETIQUETAS
        })
      : apiladoPorMesAno(f, PERIODOS, ETIQUETAS)

    return [
      graficoEvolucion({
        titulo: 'Total de compras por período',
        subtitulo: ctx.subtitulo,
        serie,
        color: colorCompras()
      }),
      {
        titulo: 'Composición del total por período',
        subtitulo: ctx.subtitulo,
        tipo: 'bar',
        apilado: true,
        labels: apilado.labels,
        datasets: apilado.series.map((s, i) => ({ label: s.label, data: s.data, color: colorSerie(i + 1) }))
      }
    ]
  }
}

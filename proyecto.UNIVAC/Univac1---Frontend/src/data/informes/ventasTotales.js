import {
  colText, colDate, colInt, colMoney,
  sumCol, countCol, kpi,
  serieTemporal, serieTemporalMultivalor, seriePorMesAno, apiladoPorMesAno,
  colorSerie, colorVentas, graficoEvolucion
} from './_helpers'

const ETIQUETAS = {
  ng: 'Neto Gravado', iv: 'IVA', piva: 'Perc. IVA', rg: 'Ret. Ganancias',
  pib: 'Perc. IIBB', pex: 'Exento', imp: 'Imp. Internos', tot: 'Total'
}

const PERIODOS = ['ng', 'iv', 'piva', 'rg', 'pib', 'pex', 'imp']

export default {
  id: 'ventas-totales',
  ques: 5,
  area: 'Ventas',
  titulo: 'Totales de ventas',
  descripcion: 'Neto gravado, IVA, percepciones, impuestos internos, retención de ganancias y total de ventas.',
  endpoint: '/reportes/ventas/totales',
  excel: 'Ventas_Totales',
  mrad: true,
  mradInicial: 1,
  extract: (d) => (Array.isArray(d) ? d : d?.detalle || []),

  columnas: (mrad) => [
    ...(mrad === 1
      ? [colText('mes_imputacion', 'Mes'), colText('ano_imputacion', 'Año')]
      : [colDate('fecha', 'Fecha')]),
    colInt('cantidad', 'Comprob.'),
    colMoney('ng', ETIQUETAS.ng),
    colMoney('iv', ETIQUETAS.iv),
    colMoney('piva', ETIQUETAS.piva),
    colMoney('rg', ETIQUETAS.rg),
    colMoney('pib', ETIQUETAS.pib),
    colMoney('pex', ETIQUETAS.pex),
    colMoney('imp', ETIQUETAS.imp),
    colMoney('tot', ETIQUETAS.tot)
  ],

  kpis: (f) => [
    kpi('Comprobantes', countCol(f, 'cantidad'), 'entero'),
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
        titulo: 'Total de ventas por período',
        subtitulo: ctx.subtitulo,
        serie,
        color: colorVentas()
      }),
      {
        titulo: 'Composición del total por período',
        subtitulo: ctx.subtitulo,
        tipo: 'bar',
        apilado: true,
        labels: apilado.labels,
        datasets: apilado.series.map((s, i) => ({ label: s.label, data: s.data, color: colorSerie(i) }))
      }
    ]
  }
}

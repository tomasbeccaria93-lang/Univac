import {
  colText, colDate, colMoney, colPercent,
  sumCol, kpi, ranking, serieTemporal, seriePorMesAno, colorCompras,
  graficoEvolucion, graficoRanking
} from './_helpers'

const ETIQUETAS = {
  ng: 'Neto Gravado', iv: 'IVA', piva: 'Perc. IVA', pib: 'Perc. IIBB',
  pex: 'Exento', cng: 'C. No Grav.', imp: 'Imp. Internos', rg: 'Ret. Ganancias',
  otros: 'Otros', tot: 'Total'
}

export default {
  id: 'compras-proveedores',
  ques: 3,
  area: 'Compras',
  titulo: 'Compras a proveedores en pesos',
  descripcion: 'Compras por proveedor, con esporádico. La participación porcentual se muestra en mRAD 3 y 4, igual que el original.',
  endpoint: '/reportes/compras/proveedores',
  excel: 'Compras_Proveedores',
  mrad: true,
  mradInicial: 1,
  extract: (d) => (Array.isArray(d) ? d : d?.detalle || []),

  columnas: (mrad) => [
    ...(mrad === 1
      ? [colText('mes_imputacion', 'Mes'), colText('ano_imputacion', 'Año')]
      : [colDate('fecha', 'Fecha')]),
    colText('proveedor', 'Proveedor'),
    colText('espo', 'Esporádico'),
    colMoney('ng', ETIQUETAS.ng),
    colMoney('iv', ETIQUETAS.iv),
    colMoney('otros', ETIQUETAS.otros),
    colMoney('tot', ETIQUETAS.tot),
    // El original oculta la columna 10 en mRAD 1 y 2 (lHide := .T.).
    ...(mrad === 3 || mrad === 4 ? [colPercent('porcentaje', 'Part.', { total: false })] : [])
  ],

  kpis: (f) => [
    kpi('Proveedores', new Set(f.map((x) => String(x.proveedor ?? 'Sin informar'))).size, 'entero'),
    kpi('Neto gravado', sumCol(f, 'ng')),
    kpi('IVA', sumCol(f, 'iv')),
    kpi('Otros', sumCol(f, 'otros')),
    kpi('Total', sumCol(f, 'tot'))
  ],

  graficos: (f, ctx) => {
    const charts = []
    const rank = ranking(f, 'proveedor', 'tot', { limite: 12 })
    if (rank.length) {
      charts.push(graficoRanking({
        titulo: `Top ${Math.min(10, rank.length)} proveedores por total`,
        subtitulo: ctx.subtitulo,
        items: rank,
        color: colorCompras(),
        limite: 10
      }))
    }

    const conEspo = new Set(f.map((x) => String(x.espo ?? '').trim()).filter(Boolean))
    if (conEspo.size > 1) {
      const porEspo = ranking(f, 'espo', 'tot', { limite: 10 }).filter((p) => p.valor > 0)
      if (porEspo.length > 1) {
        charts.push(graficoRanking({
          titulo: 'Participación por esporádico',
          subtitulo: ctx.subtitulo,
          items: porEspo,
          color: colorCompras(),
          limite: 10
        }))
      }
    }

    const serie = ctx.mrad !== 1
      ? serieTemporal(f, { fechaKey: 'fecha', valorKey: 'tot', granularidad: ctx.granularidad })
      : seriePorMesAno(f, 'tot')
    if (serie.length > 1) {
      charts.push(graficoEvolucion({
        titulo: 'Total de compras por período',
        subtitulo: ctx.subtitulo,
        serie,
        color: colorCompras()
      }))
    }

    return charts
  }
}

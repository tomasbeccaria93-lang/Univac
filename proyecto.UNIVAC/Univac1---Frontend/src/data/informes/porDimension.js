import {
  colText, colDate, colMoney,
  sumCol, kpi, ranking,
  serieTemporal, seriePorMesAno, colorVentas, colorCompras,
  graficoEvolucion, graficoRanking
} from './_helpers'

export function reportePorDimension({
  id, ques, area, titulo, descripcion, endpoint, excel, dim, dimLabel, color
}) {
  return {
    id, ques, area, titulo, descripcion, endpoint, excel,
    mrad: true,
    mradInicial: 1,
    extract: (d) => (Array.isArray(d) ? d : d?.detalle || []),

    columnas: (mrad) => [
      ...(mrad === 1
        ? [colText('mes_imputacion', 'Mes'), colText('ano_imputacion', 'Año')]
        : [colDate('fecha', 'Fecha')]),
      colText(dim, dimLabel),
      colMoney('ng', 'Neto Gravado'),
      colMoney('iv', 'IVA'),
      colMoney('otros', 'Otros'),
      colMoney('tot', 'Total')
    ],

    kpis: (f) => [
      kpi(dimLabel === 'Vendedor' ? 'Vendedores' : dimLabel + 's', new Set(f.map((x) => String(x[dim] ?? 'Sin informar'))).size, 'entero'),
      kpi('Neto gravado', sumCol(f, 'ng')),
      kpi('IVA', sumCol(f, 'iv')),
      kpi('Otros', sumCol(f, 'otros')),
      kpi('Total', sumCol(f, 'tot'))
    ],

    graficos: (f, ctx) => {
      const porFecha = ctx.mrad !== 1
      const serie = porFecha
        ? serieTemporal(f, { fechaKey: 'fecha', valorKey: 'tot', granularidad: ctx.granularidad })
        : seriePorMesAno(f, 'tot')

      const charts = []
      if (serie.length > 1) {
        charts.push(graficoEvolucion({
          titulo: 'Total por período',
          subtitulo: ctx.subtitulo,
          serie,
          color
        }))
      }

      const rank = ranking(f, dim, 'tot', { limite: 12 })
      if (rank.length) {
        charts.push(graficoRanking({
          titulo: `Top ${Math.min(10, rank.length)} de ${dimLabel.toLowerCase()}`,
          subtitulo: ctx.subtitulo,
          items: rank,
          color,
          limite: 10
        }))
      }

      return charts
    }
  }
}

export const comprasProvincias = reportePorDimension({
  id: 'compras-provincias',
  ques: 2,
  area: 'Compras',
  titulo: 'Compras por provincias',
  descripcion: 'Totales de compra agrupados por provincia del proveedor.',
  endpoint: '/reportes/compras/provincias',
  excel: 'Compras_Provincias',
  dim: 'provincia',
  dimLabel: 'Provincia',
  color: colorCompras()
})

export const ventasProvincias = reportePorDimension({
  id: 'ventas-provincias',
  ques: 6,
  area: 'Ventas',
  titulo: 'Ventas por provincias',
  descripcion: 'Totales de venta agrupados por provincia del cliente.',
  endpoint: '/reportes/ventas/provincias',
  excel: 'Ventas_Provincias',
  dim: 'provincia',
  dimLabel: 'Provincia',
  color: colorVentas()
})

export const ventasZonas = reportePorDimension({
  id: 'ventas-zonas',
  ques: 7,
  area: 'Ventas',
  titulo: 'Ventas por zonas',
  descripcion: 'Totales de venta agrupados por zona. El informe original no excluye comprobantes anulados.',
  endpoint: '/reportes/ventas/zonas',
  excel: 'Ventas_Zonas',
  dim: 'zona',
  dimLabel: 'Zona',
  color: colorVentas()
})

export const ventasVendedor = reportePorDimension({
  id: 'ventas-vendedor',
  ques: 8,
  area: 'Ventas',
  titulo: 'Ventas por vendedor',
  descripcion: 'Totales de venta agrupados por vendedor.',
  endpoint: '/reportes/ventas/vendedor',
  excel: 'Ventas_Vendedor',
  dim: 'vendedor',
  dimLabel: 'Vendedor',
  color: colorVentas()
})

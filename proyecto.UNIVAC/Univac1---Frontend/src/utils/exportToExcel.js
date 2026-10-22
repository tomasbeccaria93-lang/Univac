import * as XLSX from 'xlsx'
import { parseFecha } from './format'

const FORMATOS_NUMERICOS = {
  moneda: '#,##0.00',
  numero: '#,##0.00',
  entero: '#,##0',
  porcentaje: '#,##0.00'
}

const numeroReal = (v) => {
  if (v === null || v === undefined || v === '') return ''
  const n = typeof v === 'number' ? v : Number(v)
  return Number.isFinite(n) ? n : ''
}

const serialExcel = (fecha) => {
  const f = fecha instanceof Date ? fecha : parseFecha(fecha)
  if (!f || Number.isNaN(f.getTime())) return null
  return (Date.UTC(f.getFullYear(), f.getMonth(), f.getDate()) - Date.UTC(1899, 11, 30)) / 86400000
}

export function exportToExcel(rows, columns, opts = {}) {
  if (!rows || !rows.length) return

  let config = opts
  if (typeof opts === 'string') {
    config = { filename: opts }
  }

  const {
    filename = 'Informe',
    sheet = 'Datos',
    titulo,
    subtotulos = [],
    totales
  } = config

  const head = columns.map((c) => c.label)

  const prepare = (c, v) => {
    if (c.tipo === 'fecha') {
      const serial = serialExcel(v)
      return serial === null ? (v === null || v === undefined ? '' : v) : serial
    }
    if (c.tipo === 'numero') return numeroReal(v)
    return v === null || v === undefined ? '' : v
  }

const body = rows.map((r) => columns.map((c) => prepare(c, r[c.key])))
const filaTotales = Array.isArray(totales) && totales.length
  ? columns.map((c, i) => prepare(c, totales[i]))
  : null

  const aoa = []
  if (titulo) {
    aoa.push([titulo])
    for (const s of subtotulos) aoa.push([s])
    aoa.push([])
  }
  aoa.push(head)
  for (const r of body) aoa.push(r)
  if (filaTotales) aoa.push(filaTotales)

  const ws = XLSX.utils.aoa_to_sheet(aoa)
  const headerRow = titulo ? subtotulos.length + 2 : 0
  const lastCol = columns.length - 1
  const lastDataRow = headerRow + body.length
  const totalRow = lastDataRow + 1

  ws['!cols'] = columns.map((c) => ({ wch: c.ancho || Math.max(11, Math.min(38, c.label.length * 1.15 + 4)) }))

  if (titulo) {
    ws['!merges'] = []
    if (lastCol > 0) ws['!merges'].push({ s: { r: 0, c: 0 }, e: { r: 0, c: lastCol } })
    subtotulos.forEach((s, i) => {
      if (s && lastCol > 0) ws['!merges'].push({ s: { r: 1 + i, c: 0 }, e: { r: 1 + i, c: lastCol } })
    })
  }

  const aplicaFormato = (c) => {
    if (c.tipo === 'fecha') return 'dd/mm/yyyy'
    if (c.tipo === 'numero') return FORMATOS_NUMERICOS[c.formatoTotal || c.formato || 'numero']
    return null
  }

  for (let r = headerRow + 1; r <= (filaTotales ? totalRow : lastDataRow); r++) {
    for (let c = 0; c <= lastCol; c++) {
      const cell = ws[XLSX.utils.encode_cell({ r, c })]
      if (!cell) continue
      const z = aplicaFormato(columns[c])
      if (z) cell.z = z
    }
  }

  if (filaTotales) {
    ws['!autofilter'] = {
      ref: XLSX.utils.encode_range({ s: { r: headerRow, c: 0 }, e: { r: lastDataRow, c: lastCol } })
    }
  }

  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, String(sheet).slice(0, 31))
  XLSX.writeFile(wb, filename.endsWith('.xlsx') ? filename : `${filename}.xlsx`)
}
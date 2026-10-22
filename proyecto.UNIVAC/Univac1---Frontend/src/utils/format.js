
const nf2 = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const nf0 = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 0 })
const nf2dec = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const nfPct = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const nfDate = new Intl.DateTimeFormat('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric' })
const nfMonth = new Intl.DateTimeFormat('es-AR', { month: '2-digit', year: 'numeric' })

export const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

export function toNum(v) {
  if (v === null || v === undefined || v === '') return 0
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}

export const fmtInt = (v) => nf0.format(Math.round(toNum(v)))

export const fmtNum = (v) => {
  const n = toNum(v)
  return Number.isInteger(n) ? nf0.format(n) : nf2dec.format(n)
}

export const fmtMoney = (v) => nf2.format(toNum(v))

export const fmtCurrency = (v) =>
  new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(toNum(v))

export const fmtAxisMoney = (v) => {
  const n = toNum(v)
  const abs = Math.abs(n)
  const sign = n < 0 ? '-' : ''
  if (abs >= 1e9) return sign + '$ ' + nfNum(abs / 1e9, 1) + ' MM'
  if (abs >= 1e6) return sign + '$ ' + nfNum(abs / 1e6, 1) + ' M'
  if (abs >= 1e3) return sign + '$ ' + nfNum(abs / 1e3, 0) + ' mil'
  return sign + '$ ' + nf0.format(abs)
}

function nfNum(n, d) {
  return new Intl.NumberFormat('es-AR', {
    minimumFractionDigits: d,
    maximumFractionDigits: d
  }).format(n)
}

export const fmtPercent = (v) => nfPct.format(toNum(v)) + ' %'

export function fmtFecha(v) {
  if (v === null || v === undefined || v === '') return ''
  if (v instanceof Date) return nfDate.format(v)

  const s = String(v).trim()
  let y
  let m
  let d

  const iso = /^(\d{4})-(\d{1,2})-(\d{1,2})/.exec(s)
  const compacto = /^(\d{4})(\d{2})(\d{2})$/.exec(s)
  const barra = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(s)

  if (iso) {
    y = iso[1]; m = iso[2]; d = iso[3]
  } else if (compacto) {
    y = compacto[1]; m = compacto[2]; d = compacto[3]
  } else if (barra) {
    return `${barra[1].padStart(2, '0')}/${barra[2].padStart(2, '0')}/${barra[3]}`
  } else {
    return s
  }

  return `${d.padStart(2, '0')}/${m.padStart(2, '0')}/${y}`
}

export function parseFecha(v) {
  if (!v) return null
  if (v instanceof Date) return v
  const s = String(v).trim()
  const iso = /^(\d{4})-(\d{1,2})(?:-(\d{1,2}))?/.exec(s)
  if (iso) return new Date(Number(iso[1]), Number(iso[2]) - 1, iso[3] ? Number(iso[3]) : 1)
  const compacto = /^(\d{4})(\d{2})(\d{2})$/.exec(s)
  if (compacto) return new Date(Number(compacto[1]), Number(compacto[2]) - 1, Number(compacto[3]))
  const d = new Date(s)
  return Number.isNaN(d.getTime()) ? null : d
}

export function etiquetaPeriodo(clave, granularidad) {
  if (!clave) return ''
  const d = parseFecha(clave)
  if (!d) return String(clave)
  if (granularidad === 'mes') return `${MESES[d.getMonth()]} ${String(d.getFullYear()).slice(2)}`
  if (granularidad === 'anio') return String(d.getFullYear())
  if (granularidad === 'trimestre') return `${Math.floor(d.getMonth() / 3) + 1}º ${String(d.getFullYear()).slice(2)}`
  const p = String(d.getFullYear()).slice(2)
  return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${p}`
}

export function etiquetaRango(desde, hasta, granularidad) {
  const a = parseFecha(desde)
  const b = parseFecha(hasta)
  const fmt = granularidad === 'mes' || !b ? nfMonth : nfDate
  if (a && b) return `${fmt.format(a)} a ${fmt.format(b)}`
  if (a) return `Desde ${fmt.format(a)}`
  if (b) return `Hasta ${fmt.format(b)}`
  return 'Sin rango de fechas'
}

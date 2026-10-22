import {
  fmtMoney,
  fmtNum,
  fmtInt,
  fmtFecha,
  fmtPercent,
  toNum,
  parseFecha,
  etiquetaPeriodo,
  MESES
} from '../../utils/format'
import {
  colorSerie as tokenColorSerie,
  colorVentas as tokenColorVentas,
  colorCompras as tokenColorCompras,
  colorAcumulado as tokenColorAcumulado
} from '../../utils/chartTokens'

const SEPARADOR_CLAVE = '\u0000'

export const colText = (key, label, extra = {}) => ({
  key, label, tipo: 'texto', align: 'left', searchable: true, ...extra
})

export const colDate = (key, label, extra = {}) => ({
  key, label, tipo: 'fecha', align: 'center',
  render: (f) => fmtFecha(f[key]),
  crudo: (f) => f[key],
  ...extra
})

export const colMoney = (key, label, extra = {}) => ({
  key, label, tipo: 'numero', align: 'right', signo: true,
  render: (f) => fmtMoney(f[key]),
  formatoTotal: 'moneda',
  total: true,
  ...extra
})

export const colNumber = (key, label, extra = {}) => ({
  key, label, tipo: 'numero', align: 'right',
  render: (f) => fmtNum(f[key]),
  formatoTotal: 'numero',
  total: true,
  ...extra
})

export const colInt = (key, label, extra = {}) => ({
  key, label, tipo: 'numero', align: 'right',
  render: (f) => fmtInt(f[key]),
  formatoTotal: 'entero',
  total: true,
  ...extra
})

export const colPercent = (key, label, extra = {}) => ({
  key, label, tipo: 'numero', align: 'right',
  formato: 'porcentaje',
  render: (f) => (f[key] === null || f[key] === undefined ? '' : fmtPercent(f[key])),
  ...extra
})


export const sumCol = (filas, key) => filas.reduce((a, f) => a + toNum(f[key]), 0)

export const countCol = (filas, key) => filas.reduce((a, f) => a + toNum(f[key]), 0)

export function filaTotales(filas, columnas) {
  const out = {}
  for (const c of columnas) {
    if (!c.total) continue
    const s = sumCol(filas, c.key)
    if (c.formatoTotal === 'entero') out[c.key] = fmtInt(s)
    else if (c.formatoTotal === 'numero') out[c.key] = fmtNum(s)
    else out[c.key] = fmtMoney(s)
  }
  return out
}


export const kpi = (label, value, format = 'moneda', nota = '') => ({ label, value, format, nota })


const claveBucket = (d, g) => {
  if (!d) return null
  if (g === 'mes') return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
  if (g === 'anio') return `${d.getFullYear()}`
  if (g === 'trimestre') {
    return `${d.getFullYear()}-T${Math.floor(d.getMonth() / 3) + 1}`
  }
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export function serieTemporal(filas, { fechaKey, valorKey, granularidad }) {
  const acc = new Map()
  for (const f of filas) {
    const d = parseFecha(fechaKey ? f[fechaKey] : f.fecha)
    if (!d) continue
    const k = claveBucket(d, granularidad)
    if (!acc.has(k)) acc.set(k, { clave: k, valor: 0, n: 0 })
    const e = acc.get(k)
    e.valor += toNum(f[valorKey])
    e.n += 1
  }
  const claves = [...acc.keys()].sort()
  return claves.map((k) => ({
    clave: k,
    etiqueta: granularidad === 'anio' ? k : etiquetaPeriodo(k, granularidad),
    valor: acc.get(k).valor
  }))
}

export function serieTemporalMultivalor(filas, { fechaKey, claves, granularidad, labels }) {
  const acc = new Map()
  for (const f of filas) {
    const d = parseFecha(f[fechaKey])
    if (!d) continue
    const k = claveBucket(d, granularidad)
    if (!acc.has(k)) {
      acc.set(k, { clave: k, etiqueta: etiquetaPeriodo(k, granularidad), valores: {} })
    }
    const e = acc.get(k)
    for (const ck of claves) e.valores[ck] = (e.valores[ck] || 0) + toNum(f[ck])
  }
  const orden = [...acc.keys()].sort()
  return {
    labels: orden.map((k) => acc.get(k).etiqueta),
    series: claves.map((ck) => ({
      key: ck,
      label: labels[ck] || ck,
      data: orden.map((k) => acc.get(k).valores[ck] || 0)
    }))
  }
}


const sinVacio = (v, alt) => {
  const s = v === null || v === undefined ? '' : String(v).trim()
  return s === '' ? (alt || 'Sin informar') : s
}

export function ranking(filas, dimKey, valorKey, { limite = 0, alt } = {}) {
  const acc = new Map()
  for (const f of filas) {
    const d = sinVacio(f[dimKey], alt)
    acc.set(d, (acc.get(d) || 0) + toNum(f[valorKey]))
  }
  let out = [...acc.entries()].map(([label, valor]) => ({ label, valor }))
  out.sort((a, b) => b.valor - a.valor)
  if (limite) out = out.slice(0, limite)
  return out
}

export function participacion(filas, dimKey, valorKey, { alt } = {}) {
  const r = ranking(filas, dimKey, valorKey, { alt })
  const total = r.reduce((a, b) => a + b.valor, 0)
  return r.map((x) => ({ ...x, pct: total ? (x.valor / total) * 100 : 0 }))
}

export function apiladoPor(filas, filaKey, colKey, valorKey, { limiteFila = 0 } = {}) {
  const filasSet = new Set()
  const colsSet = new Set()
  const acc = new Map()
  for (const f of filas) {
    const a = sinVacio(f[filaKey])
    const b = sinVacio(f[colKey])
    filasSet.add(a)
    colsSet.add(b)
    const k = a + SEPARADOR_CLAVE + b
    acc.set(k, (acc.get(k) || 0) + toNum(f[valorKey]))
  }
  const catFilas = [...filasSet]
  const catCols = [...colsSet]
  if (limiteFila) {
    const totalDe = (fila) =>
      catCols.reduce((suma, c) => suma + (acc.get(fila + SEPARADOR_CLAVE + c) || 0), 0)
    catFilas.sort((a, b) => totalDe(b) - totalDe(a))
    catFilas.splice(limiteFila)
  }
  return {
    labels: catFilas,
    series: catCols.map((c) => ({
      key: c,
      label: c,
      data: catFilas.map((a) => acc.get(a + SEPARADOR_CLAVE + c) || 0)
    }))
  }
}

export function comparativo(filas, catKey, medidas, { alt } = {}) {
  const acc = new Map()
  for (const f of filas) {
    const c = sinVacio(f[catKey], alt)
    if (!acc.has(c)) acc.set(c, { label: c, valores: {} })
    for (const m of medidas) {
      const e = acc.get(c)
      e.valores[m.key] = (e.valores[m.key] || 0) + toNum(f[m.key])
    }
  }
  const out = [...acc.values()]
  out.sort((a, b) => toNum(b.valores[medidas[0].key]) - toNum(a.valores[medidas[0].key]))
  return { labels: out.map((o) => o.label), out, medidas }
}


export const nombreMes = (m) => MESES[Number(m) - 1] || String(m ?? '')

export function etiquetaMesAno(f) {
  const m = Number(f.mes_imputacion)
  const y = f.ano_imputacion
  if (!m || !y) return ''
  return `${nombreMes(m)}/${String(y).slice(-2)}`
}


export const colorSerie = (i) => tokenColorSerie(i)

export const colorVentas = () => tokenColorVentas()
export const colorCompras = () => tokenColorCompras()
export const colorAcumulado = () => tokenColorAcumulado()

export const acumular = (vals) => {
  let a = 0
  return vals.map((v) => (a += toNum(v)))
}

const ordenCronologico = (a, b) => a.ano - b.ano || a.mes - b.mes

export function seriePorMesAno(filas, valorKey) {
  const acc = new Map()
  for (const f of filas) {
    const e = etiquetaMesAno(f)
    if (!e) continue
    const previo = acc.get(e)
    if (previo) {
      previo.valor += toNum(f[valorKey])
    } else {
      acc.set(e, { etiqueta: e, ano: Number(f.ano_imputacion) || 0, mes: Number(f.mes_imputacion) || 0, valor: toNum(f[valorKey]) })
    }
  }
  return [...acc.values()].sort(ordenCronologico)
}

export function apiladoPorMesAno(filas, claves, labels) {
  const acc = new Map()
  for (const f of filas) {
    const e = etiquetaMesAno(f)
    if (!e) continue
    if (!acc.has(e)) {
      acc.set(e, {
        etiqueta: e,
        ano: Number(f.ano_imputacion) || 0,
        mes: Number(f.mes_imputacion) || 0,
        v: {}
      })
    }
    const o = acc.get(e)
    for (const c of claves) o.v[c] = (o.v[c] || 0) + toNum(f[c])
  }
  const todos = [...acc.values()].sort(ordenCronologico)
  return {
    labels: todos.map((o) => o.etiqueta),
    series: claves.map((c) => ({
      key: c,
      label: (labels && labels[c]) || c,
      data: todos.map((o) => o.v[c] || 0)
    }))
  }
}


export function graficoEvolucion({ titulo, subtitulo, serie, color, labelTotal = 'Total', labelAcumulado = 'Acumulado' }) {
  const valores = serie.map((s) => s.valor)
  return {
    titulo,
    subtitulo,
    tipo: 'bar',
    area: true,
    labels: serie.map((s) => s.etiqueta),
    datasets: [
      { label: labelTotal, data: valores, color },
      { label: labelAcumulado, data: acumular(valores), color: colorAcumulado(), render: 'line', eje: 'der' }
    ]
  }
}

export function graficoRanking({ titulo, subtitulo, items, color, label = 'Total', limite = 10, unit }) {
  const top = items.slice(0, limite)
  return {
    titulo,
    subtitulo,
    tipo: 'bar',
    orientacion: 'h',
    unidad: unit || 'moneda',
    alto: Math.max(200, top.length * 26 + 60),
    labels: top.map((r) => r.label),
    datasets: [{ label, data: top.map((r) => r.valor), color }]
  }
}


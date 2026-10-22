const FALLBACK = {
  ventas: '#1F6F8B',
  compras: '#A9744F',
  acumulado: '#33414C',
  serie: ['#3F7D58', '#6B5B95', '#A88A2E', '#4A7C8C', '#8C5A6B', '#5F6B76'],
  otros: '#C2CDD6',
  ink: {
    line: '#C2CDD6',
    lineFaint: '#EAEEF2',
    grid: '#EDF1F4',
    gridStrong: '#DCE3E9',
    tick: '#94A3AE',
    label: '#6B7A86',
    labelInside: '#FFFFFF'
  }
}

let cache = null

function resolve() {
  if (cache) return cache
  const cs = getComputedStyle(document.documentElement)
  const v = (name, fb) => (cs.getPropertyValue(name) || '').trim() || fb
  cache = {
    ventas: v('--chart-ventas', FALLBACK.ventas),
    compras: v('--chart-compras', FALLBACK.compras),
    acumulado: v('--chart-acumulado', FALLBACK.acumulado),
    serie: FALLBACK.serie.map((c, i) => v(`--chart-${i + 1}`, c)),
    otros: v('--chart-otros', FALLBACK.otros)
  }
  return cache
}

export function colorVentas() {
  return resolve().ventas
}

export function colorCompras() {
  return resolve().compras
}

export function colorAcumulado() {
  return resolve().acumulado
}

export function colorSerie(i) {
  const s = resolve().serie
  const n = Number(i)
  return s[(Number.isFinite(n) && n > 0 ? Math.floor(n) : 0) % s.length]
}

export function colorFor(kind) {
  if (kind === 'ventas') return colorVentas()
  if (kind === 'compras') return colorCompras()
  if (kind === 'acumulado') return colorAcumulado()
  return colorSerie(kind)
}

export function rgba(hex, alpha) {
  const h = String(hex).replace('#', '')
  const p = h.length === 3 ? h.split('').map((c) => c + c).join('') : h
  const v = parseInt(p, 16)
  if (Number.isNaN(v)) return `rgba(0,0,0,${alpha})`
  return `rgba(${(v >> 16) & 255}, ${(v >> 8) & 255}, ${v & 255}, ${alpha})`
}

export const INK = FALLBACK.ink
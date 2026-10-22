<template>
  <div class="serie-chart">
    <div class="serie-head">
      <div class="serie-head-l">
        <div class="serie-ttl-row">
          <span class="serie-ttl">{{ titulo }}</span>
          <span v-if="totalTxt" class="serie-total">{{ totalTxt }}</span>
        </div>
        <div class="serie-meta">
          {{ granTxt }} &middot; {{ filas.length }} {{ plural }} &middot; promedio {{ promTxt }}
        </div>
      </div>
      <div class="serie-head-r">
        <button class="serie-expt" @click="exportar" title="Exportar a Excel">
          <i class="fas fa-file-excel"></i>
        </button>
        <div class="serie-types" role="group" aria-label="Tipo de gráfico">
          <button
            v-for="t in TIPOS"
            :key="t.k"
            type="button"
            class="st-btn"
            :class="{ act: modo === t.k }"
            :title="t.t"
            @click="setTipo(t.k)"
          >
            <i :class="t.i"></i>{{ t.l }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="legs.length > 1" class="serie-legend">
      <div v-for="l in legs" :key="l.label" class="leg">
        <span class="leg-sw" :class="'sw-' + formaLeyenda" :style="{ backgroundColor: l.color }"></span>
        <span class="leg-lb">{{ l.label }}</span>
        <span class="leg-tot">{{ l.tot }}</span>
      </div>
    </div>

    <div class="serie-body">
      <Bar v-if="filas.length && !todoCero" :data="chartData" :options="chartOptions" />
      <div v-else class="serie-nodata">
        <i class="fas fa-chart-simple"></i>
        <span>Sin movimientos en este período</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Bar } from 'vue-chartjs'
import { colorSerie, rgba, INK } from '../utils/chartTokens'
import { fmtAxisMoney, fmtCurrency } from '../utils/format'

const props = defineProps({
  titulo: { type: String, required: true },
  fechas: { type: Array, default: () => [] },
  series: { type: Array, default: () => [] },
  total: { type: String, default: '' },
  tipoInicial: { type: String, default: 'bar' },
  alto: { type: Number, default: 320 }
})

const TIPOS = [
  { k: 'bar', l: 'Barras', i: 'fas fa-chart-column', t: 'Ver como barras' },
  { k: 'line', l: 'Línea', i: 'fas fa-chart-line', t: 'Ver como línea' },
  { k: 'area', l: 'Área', i: 'fas fa-chart-area', t: 'Ver como área' }
]

const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

const n = (v) => {
  if (v == null || v === '') return 0
  const x = Number(v)
  return isNaN(x) ? 0 : x
}

const parseISO = (s) => {
  const m = /^(\d{4})-(\d{1,2})-(\d{1,2})/.exec(String(s || ''))
  return m ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])) : null
}

const iso = (d) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

const claveBucket = (d, g) => {
  if (g === 'dia') return iso(d)
  if (g === 'semana') {
    const m = new Date(d.getTime())
    m.setDate(m.getDate() - ((m.getDay() + 6) % 7))
    return iso(m)
  }
  if (g === 'mes') return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
  return `${d.getFullYear()}-T${Math.floor(d.getMonth() / 3) + 1}`
}

const nombreGran = {
  dia: 'Total por día',
  semana: 'Total por semana',
  mes: 'Total por mes',
  trimestre: 'Total por trimestre'
}

const rango = computed(() => {
  let min = null
  let max = null
  for (const f of props.fechas) {
    const d = parseISO(f)
    if (!d) continue
    if (!min || d < min) min = d
    if (!max || d > max) max = d
  }
  if (!min) return null
  return {
    min,
    max,
    dias: Math.round((max - min) / 86400000) + 1,
    multiAnio: min.getFullYear() !== max.getFullYear()
  }
})

const gran = computed(() => {
  const d = rango.value ? rango.value.dias : 0
  if (d <= 62) return 'dia'
  if (d <= 400) return 'semana'
  if (d <= 2200) return 'mes'
  return 'trimestre'
})

const granTxt = computed(() => nombreGran[gran.value])

const claves = computed(() => {
  const r = rango.value
  if (!r) return []
  const g = gran.value
  const d = new Date(r.min.getFullYear(), r.min.getMonth(), r.min.getDate())
  if (g === 'semana') d.setDate(d.getDate() - ((d.getDay() + 6) % 7))
  if (g === 'mes' || g === 'trimestre') d.setDate(1)
  if (g === 'trimestre') d.setMonth(Math.floor(d.getMonth() / 3) * 3)
  const ultima = claveBucket(r.max, g)
  const out = []
  for (let guard = 0; guard < 2000; guard++) {
    const k = claveBucket(d, g)
    out.push(k)
    if (k >= ultima) break
    if (g === 'dia') d.setDate(d.getDate() + 1)
    else if (g === 'semana') d.setDate(d.getDate() + 7)
    else if (g === 'mes') d.setMonth(d.getMonth() + 1)
    else d.setMonth(d.getMonth() + 3)
  }
  return out
})

const colores = computed(() =>
  props.series.map((s, i) => s.color || colorSerie(i))
)

const filas = computed(() => {
  const cols = claves.value
  if (!cols.length) return []
  const colIdx = new Map()
  cols.forEach((k, i) => colIdx.set(k, i))
  const acc = cols.map(() => props.series.map(() => 0))
  props.fechas.forEach((f, i) => {
    const d = parseISO(f)
    if (!d) return
    const ci = colIdx.get(claveBucket(d, gran.value))
    if (ci === undefined) return
    for (let s = 0; s < props.series.length; s++) {
      const arr = props.series[s].data || []
      acc[ci][s] += n(arr[i])
    }
  })
  const multiAnio = rango.value ? rango.value.multiAnio : false
  return cols.map((k, i) => ({
    clave: k,
    label: etiquetaBucket(k, multiAnio),
    data: acc[i]
  }))
})

const etiquetaBucket = (k, multiAnio) => {
  if (k.indexOf('-T') > 0) {
    const [y, t] = k.split('-T')
    return `${t}º ${y.slice(2)}`
  }
  const p = k.split('-')
  if (p.length === 2) return `${MESES[Number(p[1]) - 1]} ${p[0].slice(2)}`
  return multiAnio ? `${p[2]}/${p[1]}/${p[0].slice(2)}` : `${p[2]}/${p[1]}`
}

const filasLimpias = computed(() =>
  filas.value.map((f) => ({
    ...f,
    data: f.data.map((v) => (Math.abs(v) < 0.005 ? 0 : v))
  }))
)

const modo = ref(props.tipoInicial)
const manual = ref(false)

watch(
  () => filas.value.length,
  (cnt) => {
    if (manual.value) return
    modo.value = cnt > 24 && props.tipoInicial === 'bar' ? 'line' : props.tipoInicial
  },
  { immediate: true }
)

watch(
  () => props.tipoInicial,
  (v) => {
    if (!manual.value) modo.value = v
  }
)

const setTipo = (k) => {
  modo.value = k
  manual.value = true
}

const esBarras = computed(() => modo.value === 'bar')
const esArea = computed(() => modo.value === 'area')
const simple = computed(() => props.series.length <= 1)
const formaLeyenda = computed(() => (esBarras.value ? 'barra' : 'linea'))
const rellena = computed(() => esArea.value && simple.value)

const totalTxt = computed(() => props.total)
const fmtMoney = (v) => fmtCurrency(n(v))
const shortMoney = (v) => fmtAxisMoney(v)

const legs = computed(() =>
  props.series.map((s, i) => ({
    label: s.label || `Serie ${i + 1}`,
    color: colores.value[i],
    tot: fmtMoney(filasLimpias.value.reduce((a, f) => a + f.data[i], 0))
  }))
)

const todoCero = computed(() =>
  filasLimpias.value.length > 0 && filasLimpias.value.every((f) => f.data.every((v) => !v))
)

const plural = computed(() => (filas.value.length === 1 ? 'período' : 'períodos'))

const promTxt = computed(() => {
  const s = filasLimpias.value
  if (!s.length) return '-'
  const cs = colores.value.length
  const tot = new Array(cs).fill(0)
  s.forEach((f) => f.data.forEach((v, i) => { tot[i] += v }))
  const txt = tot.map((t) => shortMoney(t / s.length))
  return simple.value ? txt[0] : txt.join(' / ')
})

function gradiente(ctx, color, alphaTop) {
  const { chart } = ctx
  const area = chart.chartArea
  if (!area) return rgba(color, 0.12)
  const g = chart.ctx.createLinearGradient(0, area.top, 0, area.bottom)
  g.addColorStop(0, rgba(color, alphaTop))
  g.addColorStop(0.65, rgba(color, alphaTop * 0.35))
  g.addColorStop(1, rgba(color, 0.01))
  return g
}

const chartData = computed(() => {
  const cs = colores.value
  return {
    labels: filasLimpias.value.map((f) => f.label),
    datasets: cs.map((color, i) => ({
      label: legs.value[i] ? legs.value[i].label : `Serie ${i + 1}`,
      type: esBarras.value ? 'bar' : 'line',
      data: filasLimpias.value.map((f) => f.data[i]),
      backgroundColor: esBarras.value
        ? color
        : (c) => gradiente(c, color, rellena.value ? 0.3 : 0.06),
      hoverBackgroundColor: esBarras.value ? rgba(color, 0.82) : undefined,
      borderColor: color,
      borderWidth: esBarras.value ? 0 : 2,
      borderRadius: esBarras.value ? { topLeft: 3, topRight: 3 } : 0,
      borderSkipped: false,
      fill: rellena.value ? 'origin' : false,
      tension: 0.28,
      pointRadius: !esBarras.value && simple.value && filasLimpias.value.length <= 24 ? 2.5 : 0,
      pointHoverRadius: 5,
      pointBackgroundColor: color,
      pointBorderColor: '#FFFFFF',
      pointBorderWidth: 2,
      maxBarThickness: 26,
      categoryPercentage: 0.72,
      barPercentage: 0.88
    }))
  }
})

const conEtiquetas = computed(() => esBarras.value && simple.value && filas.value.length <= 14)

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  animation: { duration: filas.value.length > 90 ? 0 : 280, easing: 'easeOutCubic' },
  interaction: { mode: 'index', intersect: false },
  layout: { padding: { top: conEtiquetas.value ? 20 : 8, right: 8, bottom: 0, left: 0 } },
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        title: (items) => (items.length ? items[0].label : ''),
        label: (c) => ` ${c.dataset.label}: ${fmtMoney(c.parsed.y)}`
      }
    },
    excelValueLabels: {
      enabled: conEtiquetas.value,
      maxLabels: 14,
      color: INK.label,
      colorInside: INK.labelInside,
      font: '600 10px IBM Plex Sans, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      formatter: (v) => shortMoney(v)
    }
  },
  scales: {
    x: {
      grid: { display: false },
      border: { display: false },
      ticks: {
        color: INK.tick,
        font: { size: 10, weight: '500' },
        maxRotation: 0,
        minRotation: 0,
        autoSkip: true,
        autoSkipPadding: 14,
        padding: 6
      }
    },
    y: {
      beginAtZero: true,
      grace: '10%',
      border: { display: false },
      grid: { color: INK.grid, lineWidth: 1, drawTicks: false },
      ticks: {
        color: INK.tick,
        font: { size: 10, weight: '500' },
        callback: (v) => shortMoney(v),
        maxTicksLimit: 6,
        padding: 10
      }
    }
  }
}))

const hoy = () => {
  const d = new Date()
  const p = (x) => String(x).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

const exportar = async () => {
  const XLSX = await import('xlsx')
  const cs = colores.value
  if (!filasLimpias.value.length) return
  const rows = filasLimpias.value.map((f) => {
    const o = { Periodo: f.label, Clave: f.clave }
    cs.forEach((_, i) => { o[legs.value[i].label] = f.data[i] })
    return o
  })
  const wb = XLSX.utils.book_new()
  const ws = XLSX.utils.json_to_sheet(rows)
  ws['!cols'] = [{ wch: 14 }, { wch: 12 }, ...cs.map(() => ({ wch: 20 }))]
  XLSX.utils.book_append_sheet(wb, ws, 'Evolucion')
  XLSX.writeFile(wb, `evolucion_${hoy()}.xlsx`)
}
</script>

<style scoped>
.serie-chart {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-width: 0;
}

.serie-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
  flex-wrap: wrap;
  padding: var(--s-4) var(--s-4) 0;
}

.serie-head-l { min-width: 0; }

.serie-ttl-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.serie-ttl {
  font-size: var(--fs-3);
  font-weight: var(--fw-semi);
  color: var(--ink);
}

.serie-total {
  font-size: var(--fs-2);
  font-weight: var(--fw-semi);
  color: var(--brand);
  background: var(--brand-soft);
  border-radius: 4px;
  padding: 1px 8px;
  font-family: var(--font);
  font-variant-numeric: tabular-nums;
}

.serie-meta {
  margin-top: 3px;
  font-size: var(--fs-1);
  font-weight: var(--fw-normal);
  color: var(--ink-3);
}

.serie-head-r {
  display: flex;
  align-items: center;
  gap: var(--s-2);
  flex-shrink: 0;
}

.serie-expt {
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: var(--bw) solid var(--line);
  border-radius: var(--r-sm);
  background: var(--surface);
  color: var(--ink-3);
  cursor: pointer;
  transition: all 0.15s;
}
.serie-expt:hover { border-color: var(--ink-4); color: var(--ink-2); }
.serie-expt i { font-size: 13px; }

.serie-types {
  display: flex;
  align-items: center;
  gap: 2px;
  background: var(--surface-sunken);
  border: var(--bw) solid var(--line);
  border-radius: var(--r-sm);
  padding: 2px;
}

.st-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border: none;
  background: transparent;
  color: var(--ink-3);
  font-family: var(--font);
  font-size: var(--fs-1);
  font-weight: var(--fw-semi);
  padding: 4px 10px;
  border-radius: 4px;
  transition: all 0.12s;
  white-space: nowrap;
}
.st-btn i { font-size: 10px; }
.st-btn:hover { color: var(--ink-2); }
.st-btn.act {
  background: var(--surface);
  color: var(--brand);
  box-shadow: var(--sh-1);
}

.serie-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 22px;
  padding: var(--s-3) var(--s-4) 2px;
}

.leg {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: var(--fs-1);
}

.leg-sw {
  flex-shrink: 0;
  border-radius: 2px;
}
.leg-sw.sw-barra { width: 9px; height: 9px; }
.leg-sw.sw-linea { width: 14px; height: 3px; }

.leg-lb { font-weight: var(--fw-semi); color: var(--ink-2); }

.leg-tot {
  color: var(--ink-3);
  font-variant-numeric: tabular-nums;
}

.serie-body {
  position: relative;
  height: v-bind('alto + "px"');
  margin: var(--s-1) 6px 0 0;
}

.serie-nodata {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--s-2);
  color: var(--ink-4);
  font-size: var(--fs-2);
}
.serie-nodata i { font-size: 22px; }

@media (max-width: 640px) {
  .serie-head { padding: var(--s-3) var(--s-3) 0; }
  .serie-legend { padding: 10px 14px 2px; }
  .st-btn { padding: 4px 7px; }
  .st-btn i { display: none; }
}
</style>
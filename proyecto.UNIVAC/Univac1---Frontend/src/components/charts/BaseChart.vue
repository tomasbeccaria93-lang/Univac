<template>
  <div class="base-chart">
    <div v-if="!hayDatos" class="bc-vacio">
      <i class="fas fa-chart-simple"></i>
      <span>Sin datos para graficar en esta consulta</span>
    </div>

    <div v-else class="bc-canvas" :style="{ height: alto + 'px' }">
      <Doughnut v-if="esDoughnut" :data="doughnutData" :options="doughnutOptions" />
      <Bar v-else :data="chartData" :options="chartOptions" />
    </div>

    <ul v-if="hayDatos && series.length > 1" class="bc-leyenda">
      <li v-for="d in series" :key="d.label">
        <span class="bc-sw" :class="'bc-sw-' + d.render" :style="{ background: d.color }" />
        <span class="bc-lb">{{ d.label }}</span>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Bar, Doughnut } from 'vue-chartjs'
import { colorFor, rgba, INK } from '../../utils/chartTokens'
import { fmtAxisMoney, fmtCurrency, fmtNum, fmtPercent, toNum } from '../../utils/format'

const props = defineProps({
  tipo: { type: String, default: 'bar' },
  labels: { type: Array, default: () => [] },
  datasets: { type: Array, default: () => [] },
  area: { type: Boolean, default: false },
  apilado: { type: Boolean, default: false },
  unidad: { type: String, default: 'moneda' },
  orientacion: { type: String, default: 'v' },
  alto: { type: Number, default: 280 }
})

const horizontal = computed(() => props.orientacion === 'h')

function renderDe(d) {
  if (d.render === 'bar' || d.render === 'line') return d.render
  return props.tipo === 'line' ? 'line' : 'bar'
}

const series = computed(() =>
  props.datasets.map((d, i) => ({
    ...d,
    render: renderDe(d),
    color: d.color || colorFor(i)
  }))
)

const hayDatos = computed(
  () => props.labels.length > 0 && props.datasets.some((d) => d.data.some((v) => Math.abs(toNum(v)) > 0.0001))
)

const esDoughnut = computed(() => props.tipo === 'doughnut')

const usaEjeDerecho = computed(() => series.value.some((d) => d.eje === 'der'))

const chartData = computed(() => ({
  labels: props.labels,
  datasets: series.value.map((d) => {
    const comun = { label: d.label, data: d.data }
    if (d.render === 'line') {
      return {
        ...comun,
        type: 'line',
        yAxisID: d.eje === 'der' ? 'y1' : 'y',
        order: d.order ?? 0,
        borderColor: d.color,
        backgroundColor: props.area ? rgba(d.color, 0.18) : 'transparent',
        fill: props.area ? 'origin' : false,
        tension: 0.25,
        borderWidth: 2,
        pointRadius: props.labels.length <= 24 ? 2.5 : 0,
        pointHoverRadius: 5,
        pointBackgroundColor: d.color,
        pointBorderColor: '#FFFFFF',
        pointBorderWidth: 2
      }
    }
    return {
      ...comun,
      type: 'bar',
      yAxisID: 'y',
      order: d.order ?? 1,
      backgroundColor: d.color,
      hoverBackgroundColor: rgba(d.color, 0.82),
      borderWidth: 0,
      borderRadius: horizontal.value ? { topRight: 3, bottomRight: 3 } : { topLeft: 3, topRight: 3 },
      borderSkipped: false,
      maxBarThickness: horizontal.value ? 22 : 26,
      categoryPercentage: 0.76,
      barPercentage: 0.9,
      stack: props.apilado ? 'a' : undefined
    }
  })
}))

const fmtValor = (v) => {
  if (props.unidad === 'moneda') return fmtCurrency(v)
  if (props.unidad === 'porcentaje') return fmtNum(v) + ' %'
  return fmtNum(v)
}

const fmtEje = (v) => {
  if (props.unidad === 'moneda') return fmtAxisMoney(v)
  if (props.unidad === 'porcentaje') return fmtNum(v) + ' %'
  return fmtNum(v)
}

const doughnutData = computed(() => {
  const d = series.value[0]
  const data = (d && Array.isArray(d.data) ? d.data : []).map((v) => toNum(v))
  return {
    labels: props.labels,
    datasets: [
      {
        data,
        backgroundColor: props.labels.map((_, i) => colorFor(i)),
        borderColor: '#FFFFFF',
        borderWidth: 2,
        hoverOffset: 6
      }
    ]
  }
})

const doughnutOptions = {
  responsive: true,
  maintainAspectRatio: false,
  cutout: '58%',
  plugins: {
    legend: {
      display: true,
      position: 'bottom',
      labels: {
        color: INK.tick,
        boxWidth: 10,
        boxHeight: 10,
        padding: 10,
        font: { size: 11, weight: '500' }
      }
    },
    tooltip: {
      callbacks: {
        label: (c) => {
          const total = c.dataset.data.reduce((a, b) => a + (toNum(b) || 0), 0)
          const pct = total ? (toNum(c.parsed) / total) * 100 : 0
          return ` ${c.label}: ${fmtValor(c.parsed)} (${fmtPercent(pct)})`
        }
      }
    },
    excelValueLabels: { enabled: false }
  }
}

const catAxis = {
  grid: { display: false },
  border: { display: false },
  ticks: { color: INK.tick, font: { size: 10, weight: '500' }, maxRotation: 0, minRotation: 0, autoSkip: true, autoSkipPadding: 14, padding: 6 }
}

const valAxis = {
  beginAtZero: true,
  grace: '8%',
  border: { display: false },
  grid: { color: INK.grid, drawTicks: false, lineWidth: 1 },
  ticks: { color: INK.tick, font: { size: 10, weight: '500' }, maxTicksLimit: 6, padding: 10, callback: (v) => fmtEje(v) }
}

const chartOptions = computed(() => {
  const scales = horizontal.value
    ? { x: { ...valAxis, stacked: props.apilado }, y: { ...catAxis, stacked: props.apilado } }
    : { x: { ...catAxis, stacked: props.apilado }, y: { ...valAxis, stacked: props.apilado } }

  if (usaEjeDerecho.value) {
    scales.y1 = {
      position: 'right',
      beginAtZero: true,
      grace: '8%',
      border: { display: false },
      grid: { display: false },
      ticks: { color: INK.tick, font: { size: 10, weight: '500' }, maxTicksLimit: 6, padding: 10, callback: (v) => fmtEje(v) }
    }
  }

  return {
    indexAxis: horizontal.value ? 'y' : 'x',
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    animation: { duration: props.labels.length > 90 ? 0 : 260, easing: 'easeOutCubic' },
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          title: (items) => (items.length ? items[0].label : ''),
          label: (c) => {
            const eje = horizontal.value ? 'x' : 'y'
            const esPct = props.unidad === 'porcentaje'
            return ` ${c.dataset.label}: ${esPct ? fmtPercent(c.parsed[eje]) : fmtValor(c.parsed[eje])}`
          },
          footer: (items) => {
            if (!props.apilado || items.length < 2) return ''
            const eje = horizontal.value ? 'x' : 'y'
            const t = items.reduce((a, c) => a + (c.parsed[eje] || 0), 0)
            return ' Total: ' + fmtValor(t)
          }
        }
      },
      excelValueLabels: {
        enabled: !horizontal.value && !props.apilado && props.labels.length <= 14,
        orientacion: 'v',
        maxLabels: 16,
        color: INK.label,
        colorInside: INK.labelInside,
        font: '600 10px IBM Plex Sans, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        formatter: (v) => fmtAxisMoney(v)
      }
    },
    scales
  }
})
</script>

<style scoped>
.base-chart {
  display: flex;
  flex-direction: column;
  gap: var(--s-2);
  min-width: 0;
}

.bc-canvas {
  position: relative;
  width: 100%;
  min-width: 0;
}

.bc-vacio {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--s-2);
  min-height: 180px;
  color: var(--ink-4);
  font-size: var(--fs-2);
}
.bc-vacio i { font-size: 24px; }

.bc-leyenda {
  display: flex;
  flex-wrap: wrap;
  gap: var(--s-1) var(--s-4);
  list-style: none;
  padding: 0;
  margin: 0;
}
.bc-leyenda li {
  display: inline-flex;
  align-items: center;
  gap: var(--s-1);
  font-size: var(--fs-1);
  color: var(--ink-2);
}
.bc-sw { flex-shrink: 0; border-radius: 2px; }
.bc-sw-bar { width: 9px; height: 9px; }
.bc-sw-line { width: 14px; height: 3px; border-radius: 2px; }
.bc-lb { font-weight: var(--fw-medium); }
</style>

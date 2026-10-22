<template>
  <div class="page-container">
    <h1>Ventas Acumuladas</h1>

    <div class="filtros">
      <div class="filtro-group">
        <label>Modo</label>
        <select v-model.number="mrad">
          <option :value="1">Agrupado por Período</option>
          <option :value="2">Agrupado por Fecha</option>
        </select>
      </div>
      <div class="filtro-group">
        <label>Desde</label>
        <input v-model="desde" :type="mrad === 1 ? 'month' : 'date'" />
      </div>
      <div class="filtro-group">
        <label>Hasta</label>
        <input v-model="hasta" :type="mrad === 1 ? 'month' : 'date'" />
      </div>
      <button class="btn-buscar" :disabled="cargando" @click="buscar">{{ cargando ? 'Buscando...' : 'Buscar' }}</button>
    </div>

    <div v-if="cargando" class="cargando">
      <div class="cargando-box">
        <div class="cargando-spinner"></div>
        <p>Cargando datos...</p>
        <span>Esto puede demorar unos segundos</span>
      </div>
    </div>

    <div v-else-if="error" class="error-box">
      <i class="fas fa-triangle-exclamation"></i>
      <p>{{ error }}</p>
      <button @click="buscar"><i class="fas fa-rotate-right"></i> Reintentar</button>
    </div>

    <div v-else-if="datos.length" class="tabla-card">
      <div class="report-card-header align-end">
        <button class="btn-excel" @click="exportar" :disabled="!datos.length">
          <i class="fas fa-file-excel"></i> Exportar Excel
        </button>
      </div>
      <table>
        <thead>
          <tr>
            <th>Mes</th>
            <th>Año</th>
            <th>Fecha</th>
            <th>Cantidad</th>
            <th>Neto Gravado</th>
            <th>IVA</th>
            <th>Perc. IVA</th>
            <th>Ret. Ganancias</th>
            <th>Perc. IIBB</th>
            <th>Exento</th>
            <th>Imp. Internos</th>
            <th>Total</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(d, i) in datos" :key="i">
            <td>{{ d.mes_imputacion }}</td>
            <td>{{ d.ano_imputacion }}</td>
            <td>{{ d.fecha }}</td>
            <td>{{ d.cantidad }}</td>
            <td>{{ formatCurrency(d.ng) }}</td>
            <td>{{ formatCurrency(d.iv) }}</td>
            <td>{{ formatCurrency(d.piva) }}</td>
            <td>{{ formatCurrency(d.rg) }}</td>
            <td>{{ formatCurrency(d.pib) }}</td>
            <td>{{ formatCurrency(d.pex) }}</td>
            <td>{{ formatCurrency(d.imp) }}</td>
            <td>{{ formatCurrency(d.tot) }}</td>
          </tr>
        </tbody>
        <tfoot v-if="totales">
          <tr>
            <td colspan="3">Totales</td>
            <td>{{ totales.cantidad }}</td>
            <td>{{ formatCurrency(totales.ng) }}</td>
            <td>{{ formatCurrency(totales.iv) }}</td>
            <td>{{ formatCurrency(totales.piva) }}</td>
            <td>{{ formatCurrency(totales.rg) }}</td>
            <td>{{ formatCurrency(totales.pib) }}</td>
            <td>{{ formatCurrency(totales.pex) }}</td>
            <td>{{ formatCurrency(totales.imp) }}</td>
            <td>{{ formatCurrency(totales.tot) }}</td>
          </tr>
        </tfoot>
      </table>
    </div>

    <div v-else class="empty-state">No hay datos para mostrar.</div>

    <div v-if="!cargando && !error && datos.length" class="grid-12 graficos">
      <div class="chart-slot col-12">
        <ChartCard titulo="Evolución de ventas" subtitulo="Total por período y acumulado">
          <BaseChart tipo="bar" :labels="labelsEvo" :datasets="datasetsEvo" area :alto="320" />
        </ChartCard>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, shallowRef, computed, onMounted } from 'vue'
import api from '../../api'
import { exportToExcel } from '../../utils/exportToExcel'
import ChartCard from '../../components/ui/ChartCard.vue'
import BaseChart from '../../components/charts/BaseChart.vue'
import { colorVentas, colorAcumulado } from '../../utils/chartTokens'

const mrad = ref(1)
const desde = ref('')
const hasta = ref('')
const datos = shallowRef([])
const cargando = ref(false)
const error = ref('')

const formatCurrency = (v) =>
  new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(v || 0)

const labelsEvo = computed(() => datos.value.map((d, i) => {
  if (d.fecha) return d.fecha
  if (d.mes_imputacion && d.ano_imputacion) return `${d.mes_imputacion}/${d.ano_imputacion}`
  return String(i + 1)
}))

const acumulados = computed(() => {
  let acc = 0
  return datos.value.map((d) => (acc += Number(d.tot) || 0))
})

const datasetsEvo = computed(() => [
  { label: 'Total', data: datos.value.map((d) => Number(d.tot) || 0), color: colorVentas(), order: 1 },
  { label: 'Acumulado', data: acumulados.value, render: 'line', eje: 'der', color: colorAcumulado(), order: 0 }
])

const totales = computed(() => {
  if (!datos.value.length) return null
  const suma = (k) => datos.value.reduce((s, r) => s + Number(r[k] || 0), 0)
  return {
    cantidad: suma('cantidad'),
    ng: suma('ng'),
    iv: suma('iv'),
    piva: suma('piva'),
    rg: suma('rg'),
    pib: suma('pib'),
    pex: suma('pex'),
    imp: suma('imp'),
    tot: suma('tot')
  }
})

const buscar = async () => {
  cargando.value = true
  error.value = ''
  datos.value = []
  try {
    const { data } = await api.get('/reportes/ventas/acumuladas', {
      params: {
        desde: desde.value || undefined,
        hasta: hasta.value || undefined,
        mrad: mrad.value
      }
    })
    datos.value = Array.isArray(data) ? data : (data.detalle || [])
  } catch (e) {
    error.value = e.response?.data?.detail || 'No se pudieron cargar los datos.'
  } finally {
    cargando.value = false
  }
}

const exportar = () => {
  exportToExcel(datos.value, [
    { key: 'mes_imputacion', label: 'Mes' },
    { key: 'ano_imputacion', label: 'Año' },
    { key: 'fecha', label: 'Fecha' },
    { key: 'cantidad', label: 'Cantidad' },
    { key: 'ng', label: 'Neto Gravado' },
    { key: 'iv', label: 'IVA' },
    { key: 'piva', label: 'Perc. IVA' },
    { key: 'rg', label: 'Ret. Ganancias' },
    { key: 'pib', label: 'Perc. IIBB' },
    { key: 'pex', label: 'Exento' },
    { key: 'imp', label: 'Imp. Internos' },
    { key: 'tot', label: 'Total' },
  ], 'Ventas_Acumuladas')
}

onMounted(buscar)
</script>

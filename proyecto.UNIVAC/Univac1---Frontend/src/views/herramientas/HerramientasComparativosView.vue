<template>
  <div class="page-container">
    <h1>Comparativos</h1>

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
      <button @click="cargar"><i class="fas fa-rotate-right"></i> Reintentar</button>
    </div>

    <template v-else>
      <div class="tabla-card">
        <div class="report-card-header">
          <div class="kpi-summary-container">
            <div class="summary-bar">
              <div class="summary-item">
                <div class="summary-value sum-ventas">{{ formatCurrency(totalVentas) }}</div>
                <div class="summary-label">Ventas</div>
              </div>
              <div class="summary-item">
                <div class="summary-value sum-compras">{{ formatCurrency(totalCompras) }}</div>
                <div class="summary-label">Total Compras</div>
              </div>
            </div>
          </div>
          <button class="btn-excel" @click="exportar" :disabled="!comparativos.length">
            <i class="fas fa-file-excel"></i> Exportar Excel
          </button>
        </div>
        <table>
          <thead>
            <tr>
              <th>Período</th>
              <th>Ventas</th>
              <th>Compras</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, i) in comparativos" :key="i">
              <td>{{ item.periodo }}</td>
              <td>{{ formatCurrency(item.ventas) }}</td>
              <td>{{ formatCurrency(item.compras) }}</td>
            </tr>
          </tbody>
          <tfoot v-if="comparativos.length">
            <tr>
              <td>Totales</td>
              <td>{{ formatCurrency(totalVentas) }}</td>
              <td>{{ formatCurrency(totalCompras) }}</td>
            </tr>
          </tfoot>
        </table>
        <p v-if="comparativos.length === 0" class="empty-msg">No hay datos para mostrar.</p>
      </div>

      <div v-if="comparativos.length" class="grid-12 graficos">
        <div class="chart-slot col-12">
          <ChartCard titulo="Ventas contra compras por período" subtitulo="Comparativo por período">
            <BaseChart tipo="bar" :labels="labelsCmp" :datasets="datasetsCmp" :alto="320" />
          </ChartCard>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, shallowRef, computed, onMounted } from 'vue'
import api from '../../api'
import { exportToExcel } from '../../utils/exportToExcel'
import ChartCard from '../../components/ui/ChartCard.vue'
import BaseChart from '../../components/charts/BaseChart.vue'
import { colorVentas, colorCompras } from '../../utils/chartTokens'

const comparativos = shallowRef([])
const cargando = ref(false)
const error = ref('')

const totalVentas = computed(() => comparativos.value.reduce((s, r) => s + Number(r.ventas || 0), 0))
const totalCompras = computed(() => comparativos.value.reduce((s, r) => s + Number(r.compras || 0), 0))

const formatCurrency = (v) =>
  new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(v || 0)

const filasCmp = computed(() => [...comparativos.value].reverse())

const labelsCmp = computed(() => filasCmp.value.map((r) => r.periodo))

const datasetsCmp = computed(() => [
  { label: 'Ventas', data: filasCmp.value.map((r) => Number(r.ventas) || 0), color: colorVentas() },
  { label: 'Compras', data: filasCmp.value.map((r) => Number(r.compras) || 0), color: colorCompras() }
])

const cargar = async () => {
  cargando.value = true
  error.value = ''
  try {
    const { data } = await api.get('/reportes/herramientas/comparativos')
    comparativos.value = Array.isArray(data) ? data : data.data || []
  } catch (e) {
    error.value = e.response?.data?.detail || 'No se pudieron cargar los datos.'
  } finally {
    cargando.value = false
  }
}

const exportar = () => {
  exportToExcel(comparativos.value, [
    { key: 'periodo', label: 'Período' },
    { key: 'ventas', label: 'Ventas' },
    { key: 'compras', label: 'Compras' },
  ], 'Comparativos')
}

onMounted(cargar)
</script>

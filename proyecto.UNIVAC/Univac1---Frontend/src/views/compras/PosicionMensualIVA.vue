<template>
  <div class="page-container">
    <h1>Posición Mensual IVA</h1>

    <div class="filtros">
      <div class="filtro-group">
        <label>Año</label>
        <input v-model.number="anio" type="number" placeholder="Todos" />
      </div>
      <div class="filtro-group">
        <label>Mes</label>
        <input v-model.number="mes" type="number" placeholder="Todos" min="1" max="12" />
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
      <div class="report-card-header">
        <div class="kpi-summary-container">
          <div class="summary-bar">
            <div class="summary-item">
              <div class="summary-value">{{ formatCurrency(debitoFiscal) }}</div>
              <div class="summary-label">Débito Fiscal</div>
            </div>
            <div class="summary-item">
              <div class="summary-value">{{ formatCurrency(creditoFiscal) }}</div>
              <div class="summary-label">Crédito Fiscal</div>
            </div>
            <div class="summary-item">
              <div class="summary-value">{{ formatCurrency(saldoIVA) }}</div>
              <div class="summary-label">Saldo IVA</div>
            </div>
          </div>
        </div>
        <button class="btn-excel" @click="exportar" :disabled="!datos.length">
          <i class="fas fa-file-excel"></i> Exportar Excel
        </button>
      </div>
      <table>
        <thead>
          <tr>
            <th>Concepto</th>
            <th>Comprobantes</th>
            <th>Neto</th>
            <th>IVA</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(d, i) in datos" :key="i">
            <td>{{ d.concepto }}</td>
            <td>{{ d.comprobantes }}</td>
            <td>{{ formatCurrency(d.neto) }}</td>
            <td>{{ formatCurrency(d.iva) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-else class="empty-state">No hay datos para mostrar.</div>

    <div v-if="!cargando && !error && datos.length" class="grid-12 graficos">
      <div class="chart-slot col-12">
        <ChartCard titulo="Neto e IVA por concepto" :subtitulo="subtituloChart">
          <BaseChart tipo="bar" :labels="labelsIva" :datasets="datasetsIva" :alto="300" />
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
import { colorVentas, colorCompras } from '../../utils/chartTokens'

const anio = ref(null)
const mes = ref(null)
const datos = shallowRef([])
const debitoFiscal = ref(0)
const creditoFiscal = ref(0)
const saldoIVA = ref(0)
const cargando = ref(false)
const error = ref('')

const formatCurrency = (v) =>
  new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(v || 0)

const subtituloChart = computed(() => {
  const partes = []
  if (anio.value) partes.push(`Año ${anio.value}`)
  if (mes.value) partes.push(`Mes ${mes.value}`)
  return partes.join(' · ')
})

const labelsIva = computed(() => datos.value.map((d) => d.concepto))

const datasetsIva = computed(() => [
  { label: 'Neto', data: datos.value.map((d) => Number(d.neto) || 0), color: colorVentas() },
  { label: 'IVA', data: datos.value.map((d) => Number(d.iva) || 0), color: colorCompras() }
])

const buscar = async () => {
  cargando.value = true
  error.value = ''
  datos.value = []
  try {
    const { data } = await api.get('/reportes/compras/iva', {
      params: { anio: anio.value || undefined, mes: mes.value || undefined }
    })
    datos.value = Array.isArray(data) ? data : (data.detalle || [])
    debitoFiscal.value = data.debito_fiscal || 0
    creditoFiscal.value = data.credito_fiscal || 0
    saldoIVA.value = data.saldo || 0
  } catch (e) {
    error.value = e.response?.data?.detail || 'No se pudieron cargar los datos.'
  } finally {
    cargando.value = false
  }
}

const exportar = () => {
  exportToExcel(datos.value, [
    { key: 'concepto', label: 'Concepto' },
    { key: 'comprobantes', label: 'Comprobantes' },
    { key: 'neto', label: 'Neto' },
    { key: 'iva', label: 'IVA' },
  ], 'Posicion_Mensual_IVA')
}

onMounted(buscar)
</script>

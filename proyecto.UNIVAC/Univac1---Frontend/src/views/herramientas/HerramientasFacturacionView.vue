<template>
  <div class="page-container">
    <h1>Facturación</h1>

    <div class="filtros">
      <div class="filtro-group">
        <label>Desde</label>
        <input v-model="desde" type="date" />
      </div>
      <div class="filtro-group">
        <label>Hasta</label>
        <input v-model="hasta" type="date" />
      </div>
      <div class="filtro-group">
        <label>Tipo Comprobante</label>
        <select v-model="tipo_comprobante">
          <option value="">Todos</option>
          <option value="Factura A">Factura A</option>
          <option value="Factura B">Factura B</option>
          <option value="Factura C">Factura C</option>
          <option value="Nota de Crédito">Nota de Crédito</option>
        </select>
      </div>
      <div class="filtro-group">
        <label>Cliente</label>
        <input v-model="cliente" type="text" placeholder="Nombre del cliente" />
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

    <div v-else-if="facturas.length" class="tabla-card">
      <div class="report-card-header align-end">
        <button class="btn-excel" @click="exportar" :disabled="!facturas.length">
          <i class="fas fa-file-excel"></i> Exportar Excel
        </button>
      </div>
      <table>
        <thead>
          <tr>
            <th>Comprobante</th>
            <th>Cliente</th>
            <th>Fecha</th>
            <th>Total</th>
            <th>Neto</th>
            <th>IVA</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, i) in facturas" :key="i">
            <td>{{ item.comprobante }}</td>
            <td>{{ item.cliente }}</td>
            <td>{{ item.fecha }}</td>
            <td>{{ formatCurrency(item.total) }}</td>
            <td>{{ formatCurrency(item.neto) }}</td>
            <td>{{ formatCurrency(item.iva) }}</td>
          </tr>
        </tbody>
        <tfoot v-if="totales">
          <tr>
            <td colspan="3">Totales</td>
            <td>{{ formatCurrency(totales.total) }}</td>
            <td>{{ formatCurrency(totales.neto) }}</td>
            <td>{{ formatCurrency(totales.iva) }}</td>
          </tr>
        </tfoot>
      </table>
    </div>

    <div v-else class="empty-state">No hay facturas para mostrar.</div>

    <div v-if="!cargando && !error && facturas.length" class="grid-12 graficos">
      <div class="chart-slot col-12">
        <ChartCard titulo="Evolución de la facturación" subtitulo="Total por comprobante y acumulado">
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

const desde = ref('')
const hasta = ref('')
const tipo_comprobante = ref('')
const cliente = ref('')
const facturas = shallowRef([])
const cargando = ref(false)
const error = ref('')

const formatCurrency = (v) =>
  new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(v || 0)

const labelsEvo = computed(() => facturas.value.map((f, i) => f.comprobante || f.fecha || String(i + 1)))

const acumulados = computed(() => {
  let acc = 0
  return facturas.value.map((f) => (acc += Number(f.total) || 0))
})

const datasetsEvo = computed(() => [
  { label: 'Total', data: facturas.value.map((f) => Number(f.total) || 0), color: colorVentas(), order: 1 },
  { label: 'Acumulado', data: acumulados.value, render: 'line', eje: 'der', color: colorAcumulado(), order: 0 }
])

const totales = computed(() => {
  if (!facturas.value.length) return null
  const suma = (k) => facturas.value.reduce((s, r) => s + Number(r[k] || 0), 0)
  return { total: suma('total'), neto: suma('neto'), iva: suma('iva') }
})

const buscar = async () => {
  cargando.value = true
  error.value = ''
  facturas.value = []
  try {
    const { data } = await api.get('/reportes/herramientas/facturacion', {
      params: { desde: desde.value || undefined, hasta: hasta.value || undefined, tipo_comprobante: tipo_comprobante.value || undefined, cliente: cliente.value || undefined }
    })
    facturas.value = Array.isArray(data) ? data : data.data || []
  } catch (e) {
    error.value = e.response?.data?.detail || 'No se pudieron cargar los datos.'
  } finally {
    cargando.value = false
  }
}

const exportar = () => {
  exportToExcel(facturas.value, [
    { key: 'comprobante', label: 'Comprobante' },
    { key: 'cliente', label: 'Cliente' },
    { key: 'fecha', label: 'Fecha' },
    { key: 'total', label: 'Total' },
    { key: 'neto', label: 'Neto' },
    { key: 'iva', label: 'IVA' },
  ], 'Facturacion')
}

onMounted(buscar)
</script>

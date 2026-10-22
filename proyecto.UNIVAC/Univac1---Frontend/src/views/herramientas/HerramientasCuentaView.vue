<template>
  <div class="page-container">
    <h1>Cuentas Corrientes</h1>

    <div class="filtros">
      <div class="filtro-group filtro-grow">
        <label>Buscar</label>
        <input v-model="buscarTexto" type="text" placeholder="Nombre del cliente o proveedor" />
      </div>
      <button class="btn-buscar" :disabled="cargando" @click="cargar">{{ cargando ? 'Buscando...' : 'Buscar' }}</button>
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
      <button @click="cargar"><i class="fas fa-rotate-right"></i> Reintentar</button>
    </div>

    <template v-else>
      <div class="section">
        <h2>Cuentas Corrientes Clientes</h2>
        <div class="tabla-card">
          <div class="report-card-header align-end">
            <button class="btn-excel" @click="exportarClientes" :disabled="!clientes.length">
              <i class="fas fa-file-excel"></i> Exportar Excel
            </button>
          </div>
          <table>
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Fecha</th>
                <th>Comprobante</th>
                <th>Tipo</th>
                <th>Debe</th>
                <th>Haber</th>
                <th>Saldo</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, i) in clientes" :key="i">
                <td>{{ item.nombre }}</td>
                <td>{{ item.fecha }}</td>
                <td>{{ item.comprobante }}</td>
                <td>{{ item.tipo }}</td>
                <td>{{ formatCurrency(item.debe) }}</td>
                <td>{{ formatCurrency(item.haber) }}</td>
                <td>{{ formatCurrency(item.saldo) }}</td>
              </tr>
            </tbody>
          </table>
          <p v-if="clientes.length === 0" class="empty-msg">No hay datos de clientes.</p>
        </div>
        <div v-if="clientes.length" class="grid-12 graficos">
          <div class="chart-slot col-12">
            <ChartCard titulo="Saldo por cliente" subtitulo="Top 10 por saldo acumulado">
              <BaseChart tipo="bar" orientacion="h" :labels="labelsClientes" :datasets="datasetsClientes" :alto="alturaClientes" />
            </ChartCard>
          </div>
        </div>
      </div>

      <div class="section">
        <h2>Cuentas Corrientes Proveedores</h2>
        <div class="tabla-card">
          <div class="report-card-header align-end">
            <button class="btn-excel" @click="exportarProveedores" :disabled="!proveedores.length">
              <i class="fas fa-file-excel"></i> Exportar Excel
            </button>
          </div>
          <table>
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Fecha</th>
                <th>Comprobante</th>
                <th>Tipo</th>
                <th>Debe</th>
                <th>Haber</th>
                <th>Saldo</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, i) in proveedores" :key="i">
                <td>{{ item.nombre }}</td>
                <td>{{ item.fecha }}</td>
                <td>{{ item.comprobante }}</td>
                <td>{{ item.tipo }}</td>
                <td>{{ formatCurrency(item.debe) }}</td>
                <td>{{ formatCurrency(item.haber) }}</td>
                <td>{{ formatCurrency(item.saldo) }}</td>
              </tr>
            </tbody>
          </table>
          <p v-if="proveedores.length === 0" class="empty-msg">No hay datos de proveedores.</p>
        </div>
        <div v-if="proveedores.length" class="grid-12 graficos">
          <div class="chart-slot col-12">
            <ChartCard titulo="Saldo por proveedor" subtitulo="Top 10 por saldo acumulado">
              <BaseChart tipo="bar" orientacion="h" :labels="labelsProveedores" :datasets="datasetsProveedores" :alto="alturaProveedores" />
            </ChartCard>
          </div>
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

const buscarTexto = ref('')
const clientes = shallowRef([])
const proveedores = shallowRef([])
const cargando = ref(false)
const error = ref('')

const formatCurrency = (v) =>
  new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(v || 0)

function agruparSaldo(rows) {
  const mapa = new Map()
  for (const r of rows) {
    const k = String(r.nombre ?? '—')
    mapa.set(k, (mapa.get(k) || 0) + Number(r.saldo || 0))
  }
  return [...mapa.entries()]
    .map(([label, valor]) => ({ label, valor }))
    .sort((a, b) => Math.abs(b.valor) - Math.abs(a.valor))
    .slice(0, 10)
}

const topClientes = computed(() => agruparSaldo(clientes.value))
const labelsClientes = computed(() => topClientes.value.map((r) => r.label))
const datasetsClientes = computed(() => [
  { label: 'Saldo', data: topClientes.value.map((r) => r.valor), color: colorVentas() }
])
const alturaClientes = computed(() => Math.max(220, topClientes.value.length * 30 + 60))

const topProveedores = computed(() => agruparSaldo(proveedores.value))
const labelsProveedores = computed(() => topProveedores.value.map((r) => r.label))
const datasetsProveedores = computed(() => [
  { label: 'Saldo', data: topProveedores.value.map((r) => r.valor), color: colorCompras() }
])
const alturaProveedores = computed(() => Math.max(220, topProveedores.value.length * 30 + 60))

const cargar = async () => {
  cargando.value = true
  error.value = ''
  try {
    const { data } = await api.get('/reportes/herramientas/cuenta', {
      params: { buscar: buscarTexto.value || undefined }
    })
    clientes.value = Array.isArray(data.clientes) ? data.clientes : []
    proveedores.value = Array.isArray(data.proveedores) ? data.proveedores : []
  } catch (e) {
    error.value = e.response?.data?.detail || 'No se pudieron cargar los datos.'
  } finally {
    cargando.value = false
  }
}

const exportarClientes = () => {
  exportToExcel(clientes.value, [
    { key: 'nombre', label: 'Nombre' },
    { key: 'fecha', label: 'Fecha' },
    { key: 'comprobante', label: 'Comprobante' },
    { key: 'tipo', label: 'Tipo' },
    { key: 'debe', label: 'Debe' },
    { key: 'haber', label: 'Haber' },
    { key: 'saldo', label: 'Saldo' },
  ], 'Cuentas_Clientes')
}

const exportarProveedores = () => {
  exportToExcel(proveedores.value, [
    { key: 'nombre', label: 'Nombre' },
    { key: 'fecha', label: 'Fecha' },
    { key: 'comprobante', label: 'Comprobante' },
    { key: 'tipo', label: 'Tipo' },
    { key: 'debe', label: 'Debe' },
    { key: 'haber', label: 'Haber' },
    { key: 'saldo', label: 'Saldo' },
  ], 'Cuentas_Proveedores')
}

onMounted(cargar)
</script>

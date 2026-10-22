<template>
  <div class="page-container">
    <h1>Indicadores</h1>

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
      <div class="kpi-grid">
        <div class="kpi-card">
          <div class="kpi-bar bar-blue"></div>
          <div class="kpi-body">
            <div class="kpi-value">{{ formatCurrency(indicadores.ventas_totales || 0) }}</div>
            <div class="kpi-label">Ventas Totales</div>
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-bar bar-red"></div>
          <div class="kpi-body">
            <div class="kpi-value">{{ formatCurrency(indicadores.compras_totales || 0) }}</div>
            <div class="kpi-label">Compras Totales</div>
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-bar bar-green"></div>
          <div class="kpi-body">
            <div class="kpi-value">{{ indicadores.clientes || 0 }}</div>
            <div class="kpi-label">Clientes</div>
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-bar bar-amber"></div>
          <div class="kpi-body">
            <div class="kpi-value">{{ indicadores.proveedores || 0 }}</div>
            <div class="kpi-label">Proveedores</div>
          </div>
        </div>
      </div>

      <div v-if="indicadores.ventas_totales || indicadores.compras_totales" class="grid-12 graficos">
        <div class="chart-slot col-12">
          <ChartCard titulo="Ventas contra compras" subtitulo="Totales generales">
            <BaseChart tipo="bar" :labels="labelsInd" :datasets="datasetsInd" :alto="300" />
          </ChartCard>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../../api'
import ChartCard from '../../components/ui/ChartCard.vue'
import BaseChart from '../../components/charts/BaseChart.vue'
import { colorVentas, colorCompras } from '../../utils/chartTokens'

const indicadores = ref({})
const cargando = ref(false)
const error = ref('')

const formatCurrency = (v) =>
  new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(v || 0)

const labelsInd = ['Ventas Totales', 'Compras Totales']

const datasetsInd = computed(() => [
  { label: 'Ventas Totales', data: [Number(indicadores.value.ventas_totales) || 0, null], color: colorVentas() },
  { label: 'Compras Totales', data: [null, Number(indicadores.value.compras_totales) || 0], color: colorCompras() }
])

const cargar = async () => {
  cargando.value = true
  error.value = ''
  try {
    const { data } = await api.get('/reportes/herramientas/indicadores')
    indicadores.value = data
  } catch (e) {
    error.value = e.response?.data?.detail || 'No se pudieron cargar los datos.'
  } finally {
    cargando.value = false
  }
}

onMounted(cargar)
</script>

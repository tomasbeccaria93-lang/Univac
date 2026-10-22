<template>
  <div class="page">
    <PageHeader :titulo="cfg.titulo" :descripcion="cfg.descripcion" :area="cfg.area" :ques="cfg.ques">
      <template #acciones>
        <slot name="acciones" />
      </template>
    </PageHeader>

    <FilterBar
      :modos="modos"
      :model-value="mrad"
      :desde="desde"
      :hasta="hasta"
      :tipo-fecha="tipoFecha"
      :variantes="variantes"
      :valor-variante="segundo"
      :label-variante="cfg.labelVariante || 'Variante'"
      :filtros="filtrosVisibles"
      :extra="extra"
      :sucursales="sucursales"
      :con-sucursal="cfg.conSucursal !== false"
      :sucursal="sucursal"
      :cargando="cargando"
      :invalido="rangoInvalido"
      @update:model-value="cambiarModo"
      @update:desde="desde = $event"
      @update:hasta="hasta = $event"
      @update:segundo="cambiarSegundo"
      @update:sucursal="sucursal = $event"
      @update:extra="extra = $event"
      @buscar="buscar"
      @limpiar="limpiar"
    />

    <StateBlock v-if="cargando" tipo="cargando" />

    <StateBlock v-else-if="error" tipo="error" :mensaje="error" @reintentar="buscar" />

    <template v-else-if="hayDatos">
      <KpiRow :items="kpis" />

      <DataTable
        :filas="filas"
        :columnas="columnas"
        :titulo="cfg.tablaTitulo || 'Detalle'"
        :subtitulo="subtituloTabla"
        :totals="totales"
        :etiqueta-totales="cfg.etiquetaTotales || 'Totales'"
        :umbral-buscador="cfg.umbralBuscador ?? 30"
        :umbral-paginado="cfg.umbralPaginado ?? 200"
        @exportar="exportar"
      >
        <template #acciones>
          <i class="fas fa-file-excel is-ok"></i>
          Exportar Excel
        </template>
      </DataTable>

      <div v-if="graficos.length" class="grid-12 graficos">
        <div
          v-for="(g, i) in graficos"
          :key="g.titulo + i"
          :class="['chart-slot', span(i, graficos.length)]"
        >
          <ChartCard :titulo="g.titulo" :subtitulo="g.subtitulo">
            <BaseChart
              :tipo="g.tipo"
              :labels="g.labels"
              :datasets="g.datasets"
              :area="g.area === true"
              :apilado="g.apilado === true"
              :unidad="g.unidad || 'moneda'"
              :orientacion="g.orientacion || 'v'"
              :alto="g.alto || 280"
            />
          </ChartCard>
        </div>
      </div>
    </template>

    <StateBlock
      v-else-if="buscado"
      tipo="vacio"
      :mensaje="cfg.vacio || 'No hay datos en el período elegido.'"
      :ayuda="cfg.vacioAyuda || 'Ampliá el rango de fechas o sacá algún filtro para ver resultados.'"
    />

    <StateBlock
      v-else
      tipo="vacio"
      mensaje="Elegí un rango de fechas y presioná Buscar."
      ayuda="Cada informe consulta los datos del programa original. La consulta puede demorar unos segundos."
    />
  </div>
</template>

<script setup>
import { computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import PageHeader from './ui/PageHeader.vue'
import FilterBar from './ui/FilterBar.vue'
import KpiRow from './ui/KpiRow.vue'
import ChartCard from './ui/ChartCard.vue'
import DataTable from './ui/DataTable.vue'
import StateBlock from './ui/StateBlock.vue'
import BaseChart from './charts/BaseChart.vue'
import { useInforme } from '../composables/useInforme'
import { useSucursales } from '../composables/useSucursales'
import { useEstadoDatos } from '../composables/useEstadoDatos'
import { filaTotales, sumCol } from '../data/informes/_helpers'
import { exportToExcel } from '../utils/exportToExcel'
import { fmtFecha } from '../utils/format'

const props = defineProps({
  config: { type: Object, required: true }
})

const route = useRoute()

const cfg = props.config
const segundoUrl = props.config.variantes?.some((v) => v.value === Number(route.query.segundo))
  ? Number(route.query.segundo)
  : undefined
const cfgInicial = segundoUrl === undefined
  ? props.config
  : { ...props.config, segundoInicial: segundoUrl }

const {
  mrad, segundo, desde, hasta, sucursal, extra,
  filas, cargando, error, buscado, hayDatos,
  tipoFecha, rangoInvalido, columnas, kpis, graficos,
  buscar, limpiar, cambiarModo, cambiarSegundo
} = useInforme(cfgInicial, { segundo: segundoUrl })

const { sucursales, cargar } = useSucursales()
const { estado: estadoDatosSuc } = useEstadoDatos()
watch(estadoDatosSuc, () => cargar())

const MODOS = [
  { value: 1, nombre: 'mRAD 1', desc: 'Período', titulo: 'Agrupado por mes de imputación' },
  { value: 2, nombre: 'mRAD 2', desc: 'Fecha', titulo: 'Agrupado por fecha' },
  { value: 3, nombre: 'mRAD 3', desc: 'Detalle', titulo: 'Detalle por comprobante' },
  { value: 4, nombre: 'mRAD 4', desc: 'Registración', titulo: 'Detalle por fecha de registración' }
]

const modos = computed(() => (cfg.mrad === false ? [] : MODOS))

const variantes = computed(() => cfg.variantes || [])

const filtrosVisibles = computed(() =>
  (cfg.filtros || []).filter((f) => !f.soloSi || f.soloSi(mrad.value, segundo.value))
)

const filasDatos = computed(() => filas.value.filter((f) => !f.filaSubtotal))

const totales = computed(() =>
  cfg.sinTotales ? null : filaTotales(filasDatos.value, columnas.value)
)

const subtituloTabla = computed(() => {
  const n = filasDatos.value.length
  if (!n) return ''
  const cols = columnas.value.length
  return `${n} ${n === 1 ? 'fila' : 'filas'} · ${cols} columnas`
})

const span = (i, total) => {
  if (total <= 1) return 'col-12'
  if (total === 3) return i === 2 ? 'col-12' : 'col-6'
  return 'col-6'
}

function exportar() {
  const cols = columnas.value
  const exportCols = cols.map((c) => ({
    key: c.key,
    label: c.label,
    tipo: c.tipo,
    formato: c.formatoTotal,
    align: c.align === 'right' ? 'right' : c.align === 'center' ? 'center' : 'left'
  }))

  const filasXl = filas.value.map((f) => {
    const o = {}
    for (const c of cols) {
      o[c.key] = c.crudo ? c.crudo(f) : f[c.key]
    }
    return o
  })

  const filaTot = cfg.sinTotales
    ? null
    : cols.map((c, i) => (i === 0 ? cfg.etiquetaTotales || 'Totales' : c.total ? sumCol(filasDatos.value, c.key) : ''))

  const subs = []
  if (desde.value) subs.push(`Desde: ${fmtFecha(desde.value)}`)
  if (hasta.value) subs.push(`Hasta: ${fmtFecha(hasta.value)}`)
  if (sucursal.value) subs.push(`Sucursal: ${sucursal.value}`)
  subs.push(`Modo: mRAD ${mrad.value}${cfg.variantes?.length ? ` / ${cfg.labelVariante}: ${segundo.value}` : ''}`)

  exportToExcel(filasXl, exportCols, {
    filename: cfg.excel || cfg.titulo,
    sheet: 'Datos',
    titulo: cfg.titulo + (cfg.ques ? `  (QUES ${cfg.ques})` : ''),
    subtotulos: subs,
    totales: filaTot
  })
}

onMounted(() => {
  if (cfg.buscarAlMontar !== false) buscar()
  if (cfg.conSucursal !== false) cargar()
})
</script>

<style scoped>
.chart-slot { display: flex; min-width: 0; }
.chart-slot > * { flex: 1; min-width: 0; }
</style>

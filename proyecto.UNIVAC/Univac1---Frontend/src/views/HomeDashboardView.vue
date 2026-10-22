<template>
  <div class="dash">
    <header class="dash-top">
      <div class="dash-top-l">
        <span class="dash-label">Panel de Control</span>
        <h1 class="dash-title">{{ empresaNombre || 'Sin empresa' }}</h1>
      </div>
      <div class="dash-top-r">
        <span v-if="updating" class="dash-updating"><span class="dash-spin"></span>Actualizando datos&hellip;</span>
        <button class="dash-btn" @click="exportarTodo" title="Exportar resumen a Excel">
          <i class="fas fa-file-excel"></i>Exportar
        </button>
      </div>
    </header>

    <div v-if="!empresaActiva" class="dash-alert">
      <i class="fas fa-circle-info"></i>
      <span>La empresa <strong>{{ empresaNombre }}</strong> no está activa. Datos históricos (solo lectura).</span>
    </div>

    <div class="dash-toolbar">
      <div class="dt-dates">
        <div class="dt-field">
          <label>Desde</label>
          <input v-model="desde" type="date" @change="onFiltro" />
        </div>
        <span class="dt-sep">&mdash;</span>
        <div class="dt-field">
          <label>Hasta</label>
          <input v-model="hasta" type="date" @change="onFiltro" />
        </div>
      </div>
    </div>

    <template v-if="loading && firstLoad">
      <div class="sk-grid sk-table"><div v-for="n in 8" :key="n" class="sk-block sm"><div class="sk-shine"/></div></div>
    </template>

    <template v-else>
      <div v-if="err" class="dash-error"><i class="fas fa-circle-exclamation"></i> {{ err }}</div>

      <div class="divider">
        <span class="divider-line" />
        <span class="divider-txt">Ingresos y Egresos del Período</span>
        <span class="divider-line" />
      </div>

      <div v-for="g in grupos" :key="g.titulo" class="grupo">
        <div class="grupo-titulo">{{ g.titulo }}</div>
        <div class="cards">
          <div v-for="c in g.items" :key="c.key" class="card">
            <span class="card-lbl">{{ c.lb }}</span>
            <span class="card-val">{{ c.val }}</span>
          </div>
        </div>
      </div>

      <div class="section-row gap-top">
        <h2 class="section-title">Evolución de Ventas y de Compras</h2>
      </div>

      <div v-if="!chartData.fechas.length" class="chart-box">
        <div class="chart-empty">Sin datos en este periodo</div>
      </div>

      <div v-else class="dash-cols">
        <section class="dash-col">
          <h3 class="col-head">
            <span class="col-dot" :style="{ background: COLOR_VENTAS }"></span>
            Ventas
          </h3>
          <div class="chart-box">
            <SerieChart
              titulo="Ventas por período"
              tipo-inicial="bar"
              :fechas="chartData.fechas"
              :series="seriesVentas"
              :total="totalVentas"
            />
          </div>
        </section>

        <section class="dash-col">
          <h3 class="col-head">
            <span class="col-dot" :style="{ background: COLOR_COMPRAS }"></span>
            Compras
          </h3>
          <div class="chart-box">
            <SerieChart
              titulo="Compras por período"
              tipo-inicial="bar"
              :fechas="chartData.fechas"
              :series="seriesCompras"
              :total="totalCompras"
            />
          </div>
        </section>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import api from '../api'
import SerieChart from '../components/SerieChart.vue'
import { colorVentas, colorCompras } from '../utils/chartTokens'
import { useEstadoDatos } from '../composables/useEstadoDatos'

const { estado: estadoDatos } = useEstadoDatos()

const data = ref({})
const loading = ref(true)
const firstLoad = ref(true)
const updating = ref(false)
const err = ref('')
const empresaNombre = ref(localStorage.getItem('empresa_nombre') || '')
const empresaActiva = ref(localStorage.getItem('empresa_activa') !== 'false')
let debounceTmr
let abortCtrl = null
let reqId = 0

onMounted(() => { load() })
onUnmounted(() => { clearTimeout(debounceTmr); if (abortCtrl) abortCtrl.abort() })

const fm = (v) => v == null || isNaN(v) ? '$ 0,00' : new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS', minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(v)

const nNum = (v) => {
  if (v == null || v === '') return 0
  const n = Number(v)
  return isNaN(n) ? 0 : n
}
const FLAT = {
  ingresos: {
    ventasContado: 'ventas_contado',
    ventasCtaCte: 'ventas_ctacte',
    cobranzas: 'cobranzas',
    ingresosVarios: 'otros_ingresos',
    ccClientesVencidos: 'cc_clientes_vencidos',
    ccClientesTotal: 'cc_clientes_total',
    chequesCartera: 'cheques_cartera',
    chequesCarteraVencidos: 'cheques_vencer',
    chequesCarteraPeriodo: 'cheques_recibidos',
    bancosTransferenciaRecibida: 'bancos_transferencia_recibida'
  },
  egresos: {
    comprasContado: 'compras_contado',
    comprasCtaCte: 'compras_ctacte',
    pagos: 'ordenes_pago',
    egresosVarios: 'otros_egresos',
    ccProveedoresVencidos: 'cc_proveedores_vencidos',
    ccProveedoresTotal: 'cc_proveedores_total',
    chequesEntregados: 'cheques_entregados',
    bancosEmisionChequeProveedor: 'bancos_emision_cheque_proveedor',
    bancosTransferenciaCuentasPropias: 'bancos_transferencia_cuentas_propias',
    bancosDepositoEfectivoTerceros: 'bancos_deposito_efectivo_terceros'
  }
}
const ing = (k) => {
  if (data.value && data.value.ingresos && data.value.ingresos[k] != null) return nNum(data.value.ingresos[k])
  const fk = FLAT.ingresos[k]
  return fk ? nNum(data.value && data.value[fk]) : 0
}
const egr = (k) => {
  if (data.value && data.value.egresos && data.value.egresos[k] != null) return nNum(data.value.egresos[k])
  const fk = FLAT.egresos[k]
  return fk ? nNum(data.value && data.value[fk]) : 0
}

const grupos = computed(() => [
  {
    titulo: 'Operaciones',
    items: [
      { key:'vco', lb:'Ventas al Contado', val:fm(ing('ventasContado')) },
      { key:'vcc', lb:'Ventas en Cuenta Corriente', val:fm(ing('ventasCtaCte')) },
      { key:'cob', lb:'Cobranzas del Período', val:fm(ing('cobranzas')) },
      { key:'oin', lb:'Otros Ingresos', val:fm(ing('ingresosVarios')) },
      { key:'cco', lb:'Compras al Contado', val:fm(egr('comprasContado')) },
      { key:'ccc', lb:'Compras en Cuenta Corriente', val:fm(egr('comprasCtaCte')) },
      { key:'opg', lb:'Órdenes de Pago', val:fm(egr('pagos')) },
      { key:'oeg', lb:'Otros Egresos', val:fm(egr('egresosVarios')) }
    ]
  },
  {
    titulo: 'Cuentas Corrientes',
    items: [
      { key:'ccv', lb:'Cuentas Corrientes de Clientes Vencidas', val:fm(ing('ccClientesVencidos')) },
      { key:'tcc', lb:'Cuentas Corrientes de Clientes Total', val:fm(ing('ccClientesTotal')) },
      { key:'cpv', lb:'Cuentas Corrientes de Proveedores Vencidas', val:fm(egr('ccProveedoresVencidos')) },
      { key:'tcp', lb:'Cuentas Corrientes de Proveedores Total', val:fm(egr('ccProveedoresTotal')) }
    ]
  },
  {
    titulo: 'Cheques',
    items: [
      { key:'chc', lb:'Cheques en Cartera', val:fm(ing('chequesCartera')) },
      { key:'chv', lb:'Cheques en Cartera Vencidos', val:fm(ing('chequesCarteraVencidos')) },
      { key:'chr', lb:'Cheques Recibidos en el Período', val:fm(ing('chequesCarteraPeriodo')) },
      { key:'che', lb:'Cheques Entregados', val:fm(egr('chequesEntregados')) }
    ]
  },
  {
    titulo: 'Bancos',
    items: [
      { key:'btr', lb:'Transferencias Bancarias Recibidas', val:fm(ing('bancosTransferenciaRecibida')) },
      { key:'bec', lb:'Emisión de Cheques de Pago a Proveedores', val:fm(egr('bancosEmisionChequeProveedor')) },
      { key:'btc', lb:'Transferencias a Cuentas Propias o de Terceros', val:fm(egr('bancosTransferenciaCuentasPropias')) },
      { key:'bde', lb:'Depósitos en Efectivo o Cheques de Terceros', val:fm(egr('bancosDepositoEfectivoTerceros')) }
    ]
  }
])

const r2 = (n) => Math.round((n + Number.EPSILON) * 100) / 100

const chartData = computed(() => {
  const map = {}
  const push = (rows, campo) => {
    ;(rows || []).forEach(r => {
      const s = String(r.fecha || '').slice(0, 10)
      if (!s) return
      const e = map[s] || (map[s] = { v: 0, c: 0 })
      e[campo] += parseFloat(r.total) || 0
    })
  }
  push(data.value.ventas_diarias, 'v')
  push(data.value.compras_diarias, 'c')

  const fechas = Object.keys(map).sort()
  const ventas = []
  const compras = []
  fechas.forEach(k => {
    ventas.push(r2(map[k].v))
    compras.push(r2(map[k].c))
  })
  return { fechas, ventas, compras }
})

const COLOR_VENTAS = colorVentas()
const COLOR_COMPRAS = colorCompras()

const seriesVentas = computed(() => [
  { label: 'Ventas', color: COLOR_VENTAS, data: chartData.value.ventas }
])
const seriesCompras = computed(() => [
  { label: 'Compras', color: COLOR_COMPRAS, data: chartData.value.compras }
])

const totalVentas = computed(() => fm(chartData.value.ventas.reduce((a, b) => a + b, 0)))
const totalCompras = computed(() => fm(chartData.value.compras.reduce((a, b) => a + b, 0)))

const pad = (n) => String(n).padStart(2, '0')
const fmtLocal = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
const hoy = () => fmtLocal(new Date())

const desde = ref('')
const hasta = ref('')

const onFiltro = () => {
  clearTimeout(debounceTmr)
  debounceTmr = setTimeout(() => load(), 400)
}

const numAR = (s) => {
  const str = String(s).trim()
  const mult = /MM\b/.test(str) || /B\b/.test(str) ? 1e9 : /M\b/.test(str) ? 1e6 : /[kK]\b/.test(str) ? 1e3 : 1
  const num = parseFloat(str.replace(/[^0-9.,-]/g, '').replace(/\./g, '').replace(',', '.'))
  return isNaN(num) ? s : num * mult
}

async function exportarTodo() {
  const XLSX = await import('xlsx')
  const rows = []
  grupos.value.forEach(g => g.items.forEach(c => { rows.push({ Concepto: c.lb, Importe: numAR(c.val), Detalle: g.titulo }) }))
  rows.push({ Concepto: '', Importe: '', Detalle: '' })
  rows.push({ Concepto: '--- EVOLUCION DIARIA ---', Importe: '', Detalle: '' })
  chartData.value.fechas.forEach((k, i) => {
    rows.push({
      Concepto: k.split('-').reverse().join('/'),
      Importe: Number(chartData.value.ventas[i]),
      Detalle: `Ventas: ${Number(chartData.value.ventas[i])} | Compras: ${Number(chartData.value.compras[i])}`,
    })
  })
  const wb = XLSX.utils.book_new()
  const ws = XLSX.utils.json_to_sheet(rows)
  ws['!cols'] = [{wch:48},{wch:18},{wch:18}]
  XLSX.utils.book_append_sheet(wb, ws, 'Resumen')
  XLSX.writeFile(wb, `panel_control_${hoy()}.xlsx`)
}

const load = async () => {
  const id = ++reqId
  if (abortCtrl) abortCtrl.abort()
  abortCtrl = new AbortController()
  if (firstLoad.value) loading.value = true
  else updating.value = true
  err.value = ''
  try {
    const p = {}
    if (desde.value) p.desde = desde.value
    if (hasta.value) p.hasta = hasta.value
    if (estadoDatos.value) p.estado = estadoDatos.value
    const r = await api.get('/reportes/dashboard', { params: p, signal: abortCtrl.signal })
    if (id !== reqId) return
    data.value = r.data
  } catch (e) {
    if (id !== reqId) return
    if (e.code === 'ERR_CANCELED') return
    err.value = e.response?.data?.detail || 'Error al conectar con el servidor'
  } finally {
    if (id === reqId) {
      firstLoad.value = false
      loading.value = false
      updating.value = false
    }
  }
}

watch(estadoDatos, () => {
  load()
})
</script>

<style scoped>
.dash {
  font-family: var(--font);
  background: var(--bg);
  min-height: 100%;
  padding: 20px 24px 36px;
  color: var(--ink);
}

.dash-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 20px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--line);
}
.dash-top-l { min-width: 0; }
.dash-label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: var(--ink-3);
  text-transform: uppercase;
  letter-spacing: 1.2px;
  margin-bottom: 2px;
}
.dash-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--ink);
  line-height: 1.2;
  letter-spacing: -0.3px;
}
.dash-top-r {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}
.dash-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  background: var(--brand);
  color: #fff;
  border: none;
  border-radius: var(--r-md);
  font-family: var(--font);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}
.dash-btn:hover { background: var(--brand-strong); }
.dash-btn i { font-size: 12px; }
.dash-updating {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--ink-3);
}
.dash-spin {
  width: 11px; height: 11px;
  border: 2px solid var(--line);
  border-top-color: var(--ink-3);
  border-radius: 50%;
  animation: dspin 0.7s linear infinite;
}
@keyframes dspin { to { transform: rotate(360deg); } }

.dash-alert {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--g-100);
  border: 1px solid var(--line);
  color: var(--ink-2);
  border-radius: var(--r-md);
  padding: 10px 14px;
  margin-bottom: 16px;
  font-size: 13px;
}
.dash-alert i { font-size: 14px; flex-shrink: 0; color: var(--ink-3); }

.dash-toolbar {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  margin-bottom: 22px;
}
.dt-dates {
  display: flex;
  align-items: center;
  gap: 5px;
}
.dt-field {
  display: flex;
  flex-direction: column;
  gap: 1px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  padding: 5px 10px;
}
.dt-field:focus-within { border-color: var(--brand-mid); }
.dt-field label {
  font-size: 10px;
  font-weight: 600;
  color: var(--ink-3);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  line-height: 1;
}
.dt-field input {
  border: none;
  background: transparent;
  padding: 0;
  font-family: var(--font);
  font-size: 13px;
  font-weight: 500;
  color: var(--ink);
  outline: none;
  width: 110px;
}
.dt-field input::-webkit-calendar-picker-indicator { opacity: 0.2; cursor: pointer; }
.dt-sep { color: var(--line); font-size: 11px; }

.divider {
  display: flex;
  align-items: center;
  gap: 14px;
  margin: 26px 0 16px;
}
.divider-line {
  flex: 1;
  height: 1px;
  background: var(--line);
}
.divider-txt {
  font-size: 11px;
  font-weight: 600;
  color: var(--ink-3);
  text-transform: uppercase;
  letter-spacing: 0.7px;
  white-space: nowrap;
  padding: 0 4px;
}

.grupo {
  margin-bottom: 22px;
}
.grupo-titulo {
  font-size: 11px;
  font-weight: 600;
  color: var(--ink-3);
  text-transform: uppercase;
  letter-spacing: 0.7px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--line);
  margin-bottom: 12px;
}
.cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.card {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  padding: 13px 16px;
  display: flex;
  flex-direction: column;
  gap: 3px;
  transition: border-color 0.2s;
}
.card:hover {
  border-color: var(--brand-mid);
}
.card-lbl {
  font-size: 11px;
  font-weight: 600;
  color: var(--ink-3);
  margin-bottom: 2px;
  letter-spacing: 0.15px;
  min-height: 14px;
}
.card-val {
  font-size: 15px;
  font-weight: 700;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.15px;
  line-height: 1.2;
}

.section-row { margin-bottom: 10px; }
.section-row.gap-top { margin-top: 28px; }
.section-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--ink-3);
  text-transform: uppercase;
  letter-spacing: 0.7px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--line);
}

.dash-cols {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--s-4);
  align-items: start;
}

.dash-col {
  display: flex;
  flex-direction: column;
  gap: var(--s-3);
  min-width: 0;
}

.col-head {
  display: flex;
  align-items: center;
  gap: var(--s-2);
  font-size: var(--fs-3);
  font-weight: var(--fw-semi);
  color: var(--ink);
  padding-bottom: var(--s-2);
  border-bottom: 2px solid var(--line);
}

.col-dot {
  width: 10px;
  height: 10px;
  border-radius: 3px;
  flex-shrink: 0;
}

.chart-box {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  overflow: hidden;
}
.chart-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ink-3);
  font-size: var(--fs-3);
  height: 320px;
}

.dash-error {
  background: var(--g-100);
  border: 1px solid var(--line);
  color: var(--ink-2);
  border-radius: var(--r-md);
  padding: 11px 14px;
  font-size: 13px;
  margin-bottom: 16px;
}
.dash-error i { margin-right: 6px; }

.sk-grid {
  display: grid;
  gap: 12px;
  margin-bottom: 16px;
}
.sk-table { grid-template-columns: repeat(4, 1fr); }
.sk-block {
  background: var(--line);
  border-radius: var(--r-md);
  height: 80px;
  overflow: hidden;
  position: relative;
}
.sk-block.sm { height: 48px; }
.sk-shine {
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
  animation: skshim 1.4s infinite;
}
@keyframes skshim { 0% { transform: translateX(-100%); } 100% { transform: translateX(100%); } }

@media (max-width: 1100px) {
  .cards { grid-template-columns: repeat(2, 1fr); }
  .dash-cols { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
  .dash { padding: 14px; }
  .dash-top { flex-wrap: wrap; gap: 8px; }
  .cards { grid-template-columns: 1fr 1fr; gap: 8px; }
  .dash-toolbar { gap: 8px; }
  .dt-dates { width: 100%; }
  .dt-field { flex: 1; }
  .dt-field input { width: 100%; }
  .chart-empty { height: 260px; }
}
@media (max-width: 480px) {
  .cards { grid-template-columns: 1fr; }
  .sk-table { grid-template-columns: 1fr; }
}
</style>

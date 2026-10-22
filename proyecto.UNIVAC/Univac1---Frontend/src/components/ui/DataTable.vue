<template>
  <section class="data-table">
    <header class="dt-head">
      <div>
        <h3 class="dt-title">{{ titulo }}</h3>
        <p class="dt-sub">{{ subtitulo }}</p>
      </div>
      <div class="dt-tools">
        <div v-if="mostrarBuscador" class="dt-search">
          <i class="fas fa-magnifying-glass"></i>
          <input
            class="dt-search-input"
            type="search"
            :placeholder="placeholderBusqueda"
            :value="busqueda"
            @input="busqueda = $event.target.value"
          />
        </div>
        <span v-if="filasFiltradas.length !== filas.length" class="dt-count">
          {{ filasFiltradas.length }} de {{ filas.length }}
        </span>
        <button v-if="$slots.acciones" class="btn" @click="$emit('exportar')">
          <slot name="acciones" />
        </button>
      </div>
    </header>

    <div class="dt-scroll">
      <table>
        <thead>
          <tr>
            <th
              v-for="(c, i) in columnas"
              :key="c.key"
              :class="[c.align === 'right' ? 'a-right' : c.align === 'center' ? 'a-center' : '', c.sortable !== false ? 'sortable' : '']"
              :style="c.ancho ? { width: c.ancho } : null"
              :aria-sort="orden === i ? (asc ? 'ascending' : 'descending') : 'none'"
              :tabindex="c.sortable !== false ? 0 : null"
              @click="c.sortable !== false ? ordenar(i) : null"
              @keydown.enter="c.sortable !== false ? ordenar(i) : null"
              @keydown.space.prevent="c.sortable !== false ? ordenar(i) : null"
            >
              <span class="dt-th">
                {{ c.label }}
                <i v-if="c.sortable !== false" class="dt-sort" :class="claseOrden(i)"></i>
              </span>
            </th>
          </tr>
        </thead>

        <tbody>
          <tr v-for="(f, idx) in enPagina" :key="idx">
            <td
              v-for="c in columnas"
              :key="c.key"
              :class="[c.align === 'right' ? 'a-right' : c.align === 'center' ? 'a-center' : '', esNegativo(f, c) ? 'neg' : '']"
            >
              {{ celda(f, c) }}
            </td>
          </tr>
        </tbody>

        <tfoot v-if="filaTotales">
          <tr>
            <td
              v-for="(c, i) in columnas"
              :key="c.key"
              :class="c.align === 'right' ? 'a-right' : c.align === 'center' ? 'a-center' : ''"
            >
              <strong v-if="i === 0">{{ etiquetaTotales }}</strong>
              <strong v-else>{{ filaTotales[c.key] }}</strong>
            </td>
          </tr>
        </tfoot>
      </table>
    </div>

    <footer v-if="paginas > 1" class="dt-foot">
      <button class="btn" :disabled="pagina === 1" @click="pagina = 1">
        <i class="fas fa-angles-left"></i>
      </button>
      <button class="btn" :disabled="pagina === 1" @click="pagina--">
        <i class="fas fa-angle-left"></i>
      </button>
      <span class="dt-pag">Página {{ pagina }} de {{ paginas }}</span>
      <button class="btn" :disabled="pagina === paginas" @click="pagina++">
        <i class="fas fa-angle-right"></i>
      </button>
      <button class="btn" :disabled="pagina === paginas" @click="pagina = paginas">
        <i class="fas fa-angles-right"></i>
      </button>
    </footer>
  </section>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { toNum, parseFecha } from '../../utils/format'

const props = defineProps({
  filas: { type: Array, default: () => [] },
  columnas: { type: Array, default: () => [] },
  titulo: { type: String, default: 'Detalle' },
  subtitulo: { type: String, default: '' },
  totals: { type: Object, default: null },
  etiquetaTotales: { type: String, default: 'Totales' },
  porPagina: { type: Number, default: 50 },
  umbralBuscador: { type: Number, default: 30 },
  umbralPaginado: { type: Number, default: 200 },
  placeholderBusqueda: { type: String, default: 'Buscar en la tabla…' }
})

defineEmits(['exportar'])

const busqueda = ref('')
const pagina = ref(1)
const orden = ref(-1)
const asc = ref(true)

watch(() => props.filas, () => { pagina.value = 1 })

const textoBusqueda = computed(() => busqueda.value.trim().toLowerCase())
const mostrarBuscador = computed(() => props.filas.length > props.umbralBuscador)

const filasFiltradas = computed(() => {
  let out = props.filas
  const q = textoBusqueda.value
  if (q) {
    out = out.filter((f) =>
      props.columnas.some((c) => {
        if (c.searchable === false) return false
        return String(c.crudo ? c.crudo(f) : f[c.key] ?? '')
          .toLowerCase()
          .includes(q)
      })
    )
  }
  const i = orden.value
  if (i >= 0 && props.columnas[i]) {
    const c = props.columnas[i]
    const dir = asc.value ? 1 : -1
    out = [...out].sort((a, b) => {
      if (c.tipo === 'numero') return (toNum(c.crudo ? c.crudo(a) : a[c.key]) - toNum(c.crudo ? c.crudo(b) : b[c.key])) * dir
      if (c.tipo === 'fecha') {
        const ta = parseFecha(c.crudo ? c.crudo(a) : a[c.key])?.getTime() ?? 0
        const tb = parseFecha(c.crudo ? c.crudo(b) : b[c.key])?.getTime() ?? 0
        return (ta - tb) * dir
      }
      const va = String(c.crudo ? c.crudo(a) : a[c.key] ?? '')
      const vb = String(c.crudo ? c.crudo(b) : b[c.key] ?? '')
      return va.localeCompare(vb, 'es', { numeric: true }) * dir
    })
  }
  return out
})

const paginaEfectiva = computed(() =>
  props.filas.length > props.umbralPaginado ? props.porPagina : props.filas.length || 1
)

const paginas = computed(() => Math.max(1, Math.ceil(filasFiltradas.value.length / paginaEfectiva.value)))

watch(paginas, (n) => {
  if (pagina.value > n) pagina.value = n
})

const enPagina = computed(() => {
  const p = paginaEfectiva.value
  if (filasFiltradas.value.length <= p) return filasFiltradas.value
  const ini = (pagina.value - 1) * p
  return filasFiltradas.value.slice(ini, ini + p)
})

const filaTotales = computed(() => {
  if (!props.totals) return null
  const out = {}
  for (const c of props.columnas) {
    out[c.key] = c.tipo === 'numero' && props.totals[c.key] !== undefined
      ? props.totals[c.key]
      : ''
  }
  return out
})

function celda(f, c) {
  if (c.render) return c.render(f)
  const v = f[c.key]
  return v === null || v === undefined ? '' : v
}

function esNegativo(f, c) {
  if (c.tipo !== 'numero' || c.signo !== true) return false
  return toNum(c.crudo ? c.crudo(f) : f[c.key]) < 0
}

function ordenar(i) {
  if (orden.value === i) asc.value = !asc.value
  else {
    orden.value = i
    asc.value = true
  }
}

function claseOrden(i) {
  if (orden.value !== i) return 'fa-sort'
  return asc.value ? 'fa-sort-up' : 'fa-sort-down'
}
</script>

<style scoped>
.data-table {
  display: flex;
  flex-direction: column;
  background: var(--surface);
  border: var(--bw) solid var(--line);
  border-radius: var(--r-md);
  overflow: hidden;
  min-width: 0;
}

.dt-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s-3);
  flex-wrap: wrap;
  padding: var(--s-3) var(--s-4);
  border-bottom: var(--bw) solid var(--line);
}

.dt-title { font-size: var(--fs-3); font-weight: var(--fw-semi); }
.dt-sub { font-size: var(--fs-1); color: var(--ink-3); margin-top: 1px; }

.dt-tools {
  display: flex;
  align-items: center;
  gap: var(--s-2);
  flex-shrink: 0;
}

.dt-search {
  display: flex;
  align-items: center;
  gap: var(--s-2);
  height: 30px;
  padding: 0 var(--s-2) 0 var(--s-3);
  border: var(--bw) solid var(--line-strong);
  border-radius: var(--r-sm);
  background: var(--surface);
}
.dt-search:focus-within {
  border-color: var(--brand-mid);
  box-shadow: 0 0 0 3px rgb(44 97 120 / 0.14);
}
.dt-search i { font-size: 11px; color: var(--ink-4); }
.dt-search-input {
  border: none;
  outline: none;
  background: transparent;
  font-size: var(--fs-1);
  width: 150px;
}
.dt-search-input::-webkit-search-cancel-button { cursor: pointer; }

.dt-count { font-size: var(--fs-1); color: var(--ink-3); }

.dt-scroll {
  overflow: auto;
  max-height: 62vh;
}

table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: var(--fs-2);
}

thead th {
  position: sticky;
  top: 0;
  z-index: 2;
  padding: var(--s-2) var(--s-3);
  background: var(--brand);
  color: var(--ink-invert);
  font-size: var(--fs-1);
  font-weight: var(--fw-semi);
  text-align: left;
  white-space: nowrap;
  user-select: none;
  border-bottom: var(--bw) solid var(--brand-strong);
}
thead th.sortable { cursor: pointer; }
thead th.sortable:hover { background: var(--brand-strong); }

.dt-th { display: inline-flex; align-items: center; gap: var(--s-1); }
.dt-sort { font-size: 9px; opacity: 0.45; }
th.sortable:hover .dt-sort { opacity: 0.9; }
th[aria-sort='ascending'] .dt-sort,
th[aria-sort='descending'] .dt-sort { opacity: 1; }

tbody td {
  padding: var(--s-2) var(--s-3);
  border-bottom: var(--bw) solid var(--g-100);
  color: var(--ink);
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
tbody tr:hover td { background: var(--surface-2); }

tfoot td {
  position: sticky;
  bottom: 0;
  padding: var(--s-2) var(--s-3);
  background: var(--surface-sunken);
  border-top: var(--bw) solid var(--line-strong);
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
  color: var(--ink);
}

.dt-foot {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--s-2);
  padding: var(--s-2);
  border-top: var(--bw) solid var(--line);
}
.dt-pag {
  font-size: var(--fs-1);
  color: var(--ink-3);
  padding: 0 var(--s-2);
  font-variant-numeric: tabular-nums;
}

@media (max-width: 640px) {
  .dt-head { padding: var(--s-2) var(--s-3); }
  .dt-scroll { max-height: 55vh; }
  thead th,
  tbody td,
  tfoot td { padding: var(--s-2); font-size: var(--fs-1); }
  .dt-search-input { width: 100px; }
}
</style>

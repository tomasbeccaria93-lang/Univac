<template>
  <form class="filter-bar" @submit.prevent="emitir">
    <div v-if="hayModos" class="field field-modo">
      <span class="field-label">Modo</span>
      <div class="segmented" role="radiogroup" aria-label="Modo del informe">
        <button
          v-for="m in modos"
          :key="m.value"
          type="button"
          role="radio"
          class="seg-btn"
          :class="{ act: modelValue === m.value }"
          :aria-checked="modelValue === m.value"
          :title="m.titulo"
          @click="elegirModo(m.value)"
        >
          <span class="seg-code">{{ m.nombre }}</span>
          <span class="seg-desc">{{ m.desc }}</span>
        </button>
      </div>
    </div>

    <div class="field field-fecha">
      <label class="field-label" for="fb-desde">Desde</label>
      <input
        id="fb-desde"
        class="input"
        :class="{ 'is-invalid': invalido }"
        :type="tipoFecha"
        :value="desde"
        @input="set('desde', $event.target.value)"
      />
    </div>
    <div class="field field-fecha">
      <label class="field-label" for="fb-hasta">Hasta</label>
      <input
        id="fb-hasta"
        class="input"
        :class="{ 'is-invalid': invalido }"
        :type="tipoFecha"
        :value="hasta"
        @input="set('hasta', $event.target.value)"
      />
    </div>

    <div v-if="variantes.length > 1" class="field field-modo">
      <span class="field-label">{{ labelVariante }}</span>
      <div class="segmented segmented-sm" role="radiogroup" :aria-label="labelVariante">
        <button
          v-for="s in variantes"
          :key="s.value"
          type="button"
          role="radio"
          class="seg-btn seg-btn-sm"
          :class="{ act: valorVariante === s.value }"
          :aria-checked="valorVariante === s.value"
          :title="s.titulo"
          @click="set('segundo', s.value)"
        >
          <span class="seg-desc">{{ s.desc }}</span>
        </button>
      </div>
    </div>

    <div v-for="f in filtros" :key="f.key" class="field">
      <label class="field-label" :for="'fb-' + f.key">{{ f.label }}</label>
      <input
        v-if="f.tipo !== 'select'"
        :id="'fb-' + f.key"
        class="input"
        :type="f.tipo || 'text'"
        :placeholder="f.placeholder || ''"
        :value="extra[f.key] || ''"
        @input="setExtra(f.key, $event.target.value)"
      />
      <select
        v-else
        :id="'fb-' + f.key"
        class="select"
        :value="extra[f.key] || ''"
        @change="setExtra(f.key, $event.target.value)"
      >
        <option value="">{{ f.placeholder || 'Todos' }}</option>
        <option v-for="o in f.opciones" :key="o.value" :value="o.value">{{ o.label }}</option>
      </select>
    </div>

    <div v-if="conSucursal" class="field field-suc">
      <label class="field-label" for="fb-sucursal">Sucursal</label>
      <select
        id="fb-sucursal"
        class="select"
        :value="sucursal"
        :disabled="!sucursales.length"
        @change="set('sucursal', $event.target.value)"
      >
        <option value="">Todas</option>
        <option v-for="s in sucursales" :key="s.id" :value="s.id">
          Sucursal {{ s.id }} ({{ s.comprobantes }})
        </option>
      </select>
    </div>

    <div class="filter-acciones">
      <button class="btn btn-primary" type="submit" :disabled="cargando || invalido">
        <i class="fas" :class="cargando ? 'fa-circle-notch fa-spin' : 'fa-magnifying-glass'"></i>
        {{ cargando ? 'Buscando' : 'Buscar' }}
      </button>
      <button class="btn" type="button" :disabled="cargando" @click="emitirLimpiar">
        <i class="fas fa-eraser"></i>
        Limpiar
      </button>
    </div>

    <p v-if="invalido" class="filter-error" role="alert">
      <i class="fas fa-triangle-exclamation"></i>
      La fecha «Desde» no puede ser posterior a «Hasta».
    </p>
  </form>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modos: { type: Array, default: () => [] },
  modelValue: { type: Number, default: 1 },
  desde: { type: String, default: '' },
  hasta: { type: String, default: '' },
  tipoFecha: { type: String, default: 'date' },
  variantes: { type: Array, default: () => [] },
  valorVariante: { type: Number, default: 1 },
  labelVariante: { type: String, default: 'Variante' },
  filtros: { type: Array, default: () => [] },
  extra: { type: Object, default: () => ({}) },
  sucursales: { type: Array, default: () => [] },
  conSucursal: { type: Boolean, default: false },
  sucursal: { type: String, default: '' },
  cargando: { type: Boolean, default: false },
  invalido: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'update:desde', 'update:hasta', 'update:segundo', 'update:sucursal', 'update:extra', 'buscar', 'limpiar'])

const hayModos = computed(() => props.modos.length > 0)

function set(campo, valor) {
  const ev = 'update:' + campo
  if (campo === 'segundo') emit(ev, Number(valor))
  else emit(ev, valor)
}

function setExtra(key, valor) {
  emit('update:extra', { ...props.extra, [key]: valor })
}

function elegirModo(v) {
  emit('update:modelValue', v)
}

function emitir() {
  if (!props.invalido) emit('buscar')
}

function emitirLimpiar() {
  emit('limpiar')
}
</script>

<style scoped>
.filter-bar {
  display: flex;
  align-items: flex-end;
  gap: var(--s-3);
  flex-wrap: wrap;
  padding: var(--s-3) var(--s-4);
  background: var(--surface);
  border: var(--bw) solid var(--line);
  border-radius: var(--r-md);
}

.field-modo { flex: 0 0 auto; }
.field-fecha { width: 152px; }
.field-suc { width: 190px; }
.field:has(.input), .field:has(.select) { width: 170px; }

.filter-acciones {
  display: flex;
  align-items: center;
  gap: var(--s-2);
  margin-left: auto;
  padding-bottom: 1px;
}

.filter-error {
  flex: 1 0 100%;
  display: flex;
  align-items: center;
  gap: var(--s-2);
  font-size: var(--fs-1);
  color: var(--danger);
}

.segmented {
  display: flex;
  gap: 2px;
  padding: 2px;
  background: var(--surface-sunken);
  border: var(--bw) solid var(--line);
  border-radius: var(--r-sm);
}

.seg-btn {
  display: flex;
  align-items: baseline;
  gap: var(--s-1);
  padding: 5px 10px;
  border: var(--bw) solid transparent;
  border-radius: 4px;
  background: transparent;
  color: var(--ink-3);
  font-size: var(--fs-1);
  font-weight: var(--fw-medium);
  white-space: nowrap;
  transition: background 0.14s ease, color 0.14s ease, border-color 0.14s ease;
}
.seg-btn:hover { color: var(--ink); background: rgb(255 255 255 / 0.6); }
.seg-btn.act {
  background: var(--surface);
  border-color: var(--line-strong);
  color: var(--brand);
  font-weight: var(--fw-semi);
  box-shadow: var(--sh-1);
}
.seg-code {
  font-weight: var(--fw-bold);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  opacity: 0.6;
}
.seg-btn.act .seg-code { opacity: 1; color: var(--brand-mid); }
.seg-desc { font-size: var(--fs-1); }

.segmented-sm .seg-btn { padding: 5px 12px; }

@media (max-width: 900px) {
  .filter-bar { padding: var(--s-3); }
  .field-modo { flex: 1 0 100%; }
  .segmented { flex-wrap: wrap; }
  .seg-btn { flex: 1 0 auto; justify-content: center; }
  .field-fecha,
  .field-suc,
  .field:has(.input),
  .field:has(.select) { width: calc(50% - var(--s-2)); }
  .filter-acciones { flex: 1 0 100%; margin-left: 0; }
  .filter-acciones .btn { flex: 1; }
}

@media (max-width: 560px) {
  .field-fecha,
  .field-suc,
  .field:has(.input),
  .field:has(.select) { width: 100%; }
  .seg-desc { display: none; }
  .seg-btn { padding: 6px 10px; }
}
</style>

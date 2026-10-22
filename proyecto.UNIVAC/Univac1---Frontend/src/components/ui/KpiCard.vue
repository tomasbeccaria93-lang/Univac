<template>
  <div class="kpi" :class="{ 'kpi-neg': negativo }">
    <span class="kpi-label">{{ label }}</span>
    <span class="kpi-value">{{ texto }}</span>
    <span v-if="nota" class="kpi-nota">{{ nota }}</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { toNum } from '../../utils/format'

const props = defineProps({
  label: { type: String, required: true },
  value: { type: [Number, String], default: 0 },
  format: { type: String, default: 'moneda' },
  nota: { type: String, default: '' }
})

const fmt = computed(() => {
  if (props.format === 'entero') {
    return new Intl.NumberFormat('es-AR', { maximumFractionDigits: 0 }).format(toNum(props.value))
  }
  if (props.format === 'numero') {
    return new Intl.NumberFormat('es-AR', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2
    }).format(toNum(props.value))
  }
  if (props.format === 'porcentaje') {
    return (
      new Intl.NumberFormat('es-AR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(
        toNum(props.value)
      ) + ' %'
    )
  }
  return new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency: 'ARS',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(toNum(props.value))
})

const texto = computed(() => fmt.value)
const negativo = computed(() => props.format === 'moneda' && toNum(props.value) < 0)
</script>

<style scoped>
.kpi {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--s-1);
  padding: var(--s-3) var(--s-4);
  background: var(--surface);
  border: var(--bw) solid var(--line);
  border-radius: var(--r-md);
  min-width: 0;
  overflow: hidden;
}

.kpi::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--brand-mid);
}
.kpi-neg::before { background: var(--danger); }

.kpi-label {
  font-size: var(--fs-1);
  font-weight: var(--fw-semi);
  color: var(--ink-3);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.kpi-value {
  font-size: var(--fs-5);
  font-weight: var(--fw-bold);
  color: var(--ink);
  line-height: 1.15;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.kpi-neg .kpi-value { color: var(--danger); }

.kpi-nota {
  font-size: var(--fs-1);
  color: var(--ink-4);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>

<template>
  <div v-if="items.length" class="kpi-row" :style="{ '--n': Math.min(items.length, 5) }">
    <KpiCard
      v-for="k in items"
      :key="k.label"
      :label="k.label"
      :value="k.value"
      :format="k.format"
      :nota="k.nota || ''"
    />
  </div>
</template>

<script setup>
import KpiCard from './KpiCard.vue'

defineProps({
  items: { type: Array, default: () => [] }
})
</script>

<style scoped>
.kpi-row {
  display: grid;
  grid-template-columns: repeat(var(--n, 4), minmax(0, 1fr));
  gap: var(--s-3);
}

@media (max-width: 1280px) {
  .kpi-row { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 780px) {
  .kpi-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 420px) {
  .kpi-row { grid-template-columns: minmax(0, 1fr); }
}
</style>

<template>
  <section class="chart-card">
    <header class="cc-head">
      <div class="cc-titles">
        <h3 class="cc-title">{{ titulo }}</h3>
        <p v-if="subtitulo" class="cc-sub">{{ subtitulo }}</p>
      </div>
      <div v-if="$slots.acciones" class="cc-acciones">
        <slot name="acciones" />
      </div>
    </header>
    <div class="cc-body">
      <slot />
    </div>
  </section>
</template>

<script setup>
defineProps({
  titulo: { type: String, required: true },
  subtitulo: { type: String, default: '' }
})
</script>

<style scoped>
.chart-card {
  display: flex;
  flex-direction: column;
  background: var(--surface);
  border: var(--bw) solid var(--line);
  border-radius: var(--r-md);
  padding: var(--s-4);
  min-width: 0;
}

.cc-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--s-3);
  margin-bottom: var(--s-3);
}

.cc-titles { min-width: 0; }

.cc-title {
  font-size: var(--fs-3);
  font-weight: var(--fw-semi);
  color: var(--ink);
}

.cc-sub {
  margin-top: 2px;
  font-size: var(--fs-1);
  color: var(--ink-3);
}

.cc-acciones {
  display: flex;
  align-items: center;
  gap: var(--s-2);
  flex-shrink: 0;
}

.cc-body { min-width: 0; }
</style>

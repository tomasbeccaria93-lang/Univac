<template>
  <header class="page-header">
    <div class="ph-text">
      <div class="ph-crumb">
        <span v-if="ques" class="ph-ques">QUES {{ ques }}</span>
        <span v-if="ques" class="ph-sep">/</span>
        <span>{{ area }}</span>
      </div>
      <h1 class="ph-title">{{ titulo }}</h1>
      <p v-if="descripcion" class="ph-desc">{{ descripcion }}</p>
    </div>
    <div v-if="$slots.acciones" class="ph-actions">
      <slot name="acciones" />
    </div>
  </header>
</template>

<script setup>
defineProps({
  titulo: { type: String, required: true },
  descripcion: { type: String, default: '' },
  area: { type: String, default: 'Informes' },
  ques: { type: [Number, String], default: '' }
})
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--s-4);
  flex-wrap: wrap;
}

.ph-text { min-width: 0; }

.ph-crumb {
  display: flex;
  align-items: center;
  gap: var(--s-2);
  font-size: var(--fs-1);
  font-weight: var(--fw-semi);
  color: var(--ink-4);
  margin-bottom: var(--s-1);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.ph-ques { color: var(--brand-mid); }
.ph-sep { color: var(--line-strong); }

.ph-title {
  font-size: var(--fs-5);
  font-weight: var(--fw-bold);
  color: var(--ink);
}

.ph-desc {
  margin-top: var(--s-1);
  font-size: var(--fs-2);
  color: var(--ink-3);
  max-width: 78ch;
}

.ph-actions {
  display: flex;
  align-items: center;
  gap: var(--s-2);
  flex-shrink: 0;
}
</style>

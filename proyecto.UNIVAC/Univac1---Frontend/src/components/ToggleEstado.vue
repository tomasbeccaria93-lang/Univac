<template>
  <label
    class="tgl"
    :title="estado === 0 ? 'Datos activos (tablas principales)' : 'Datos de respaldo (tablas _)'"
  >
    <span class="tgl-lbl">{{ estado === 0 ? 'Datos activos' : 'Datos de respaldo' }}</span>
    <input
      type="checkbox"
      role="switch"
      :checked="estado === 0"
      :aria-checked="estado === 0 ? 'true' : 'false'"
      @change="onChange"
    />
    <span class="tgl-track"><span class="tgl-knob" /></span>
  </label>
</template>

<script setup>
defineProps({
  estado: { type: Number, default: 0 }
})
const emit = defineEmits(['update:estado'])

const onChange = (e) => {
  emit('update:estado', e.target.checked ? 0 : 1)
}
</script>

<style scoped>
.tgl {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
  font-size: 12px;
  font-weight: 600;
  color: var(--ink-2);
}

.tgl input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.tgl-track {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
  border-radius: 999px;
  background: var(--g-300);
  transition: background 0.2s ease;
  flex-shrink: 0;
}

.tgl-knob {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--g-0);
  box-shadow: var(--sh-1);
  transition: transform 0.2s ease;
}

.tgl input:checked + .tgl-track {
  background: var(--brand-mid);
}

.tgl input:checked + .tgl-track .tgl-knob {
  transform: translateX(20px);
}

.tgl input:focus-visible + .tgl-track {
  outline: 2px solid var(--brand-mid);
  outline-offset: 2px;
}

@media (max-width: 900px) {
  .tgl-lbl {
    display: none;
  }
}
</style>

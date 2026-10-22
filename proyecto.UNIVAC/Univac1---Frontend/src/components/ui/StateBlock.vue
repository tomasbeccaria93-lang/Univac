<template>
  <div class="state-block" :class="'state-' + tipo">
    <template v-if="tipo === 'cargando'">
      <div class="sk sk-line" v-for="i in 3" :key="i" :style="{ width: [70, 90, 55][i - 1] + '%' }"></div>
      <div class="sk-grid">
        <div class="sk sk-box" v-for="i in 4" :key="i"></div>
      </div>
      <p class="state-msg">Consultando el servidor…</p>
    </template>

    <template v-else-if="tipo === 'error'">
      <i class="fas fa-triangle-exclamation state-icon"></i>
      <p class="state-msg">{{ mensaje || 'No se pudieron cargar los datos.' }}</p>
      <button v-if="reintentable" class="btn btn-primary" @click="$emit('reintentar')">
        <i class="fas fa-rotate-right"></i>
        Reintentar
      </button>
    </template>

    <template v-else>
      <i class="fas fa-inbox state-icon"></i>
      <p class="state-msg">{{ mensaje || 'No hay datos en el período elegido.' }}</p>
      <p v-if="ayuda" class="state-help">{{ ayuda }}</p>
    </template>
  </div>
</template>

<script setup>
defineProps({
  tipo: { type: String, default: 'vacio' },
  mensaje: { type: String, default: '' },
  ayuda: { type: String, default: '' },
  reintentable: { type: Boolean, default: true }
})
defineEmits(['reintentar'])
</script>

<style scoped>
.state-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--s-3);
  min-height: 180px;
  padding: var(--s-5) var(--s-4);
  background: var(--surface);
  border: var(--bw) dashed var(--line-strong);
  border-radius: var(--r-md);
  text-align: center;
}

.state-icon {
  font-size: 26px;
  color: var(--ink-4);
}
.state-error .state-icon { color: var(--danger); }

.state-msg {
  font-size: var(--fs-2);
  color: var(--ink-2);
  max-width: 60ch;
}

.state-help {
  font-size: var(--fs-1);
  color: var(--ink-4);
  max-width: 60ch;
}

.state-error {
  border-style: solid;
  border-color: var(--danger);
  background: var(--danger-bg);
}
.state-error .state-msg { color: var(--danger); }

.sk {
  background: linear-gradient(90deg, var(--g-100) 25%, var(--g-50) 50%, var(--g-100) 75%);
  background-size: 200% 100%;
  animation: sk-brillo 1.3s ease-in-out infinite;
  border-radius: 4px;
}
.sk-line { height: 12px; margin-bottom: var(--s-2); }
.sk-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--s-3);
  width: 100%;
  max-width: 720px;
  margin-top: var(--s-3);
}
.sk-box { height: 54px; }

@keyframes sk-brillo {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>

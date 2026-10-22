<template>
  <div class="notfound">
    <div class="nf-card">
      <div class="nf-code">404</div>
      <h1>Página no encontrada</h1>
      <p>La dirección que buscas no existe o fue movida.</p>
      <button class="nf-btn" @click="irInicio">
        <i class="fas fa-arrow-left"></i> Volver al inicio
      </button>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

function irInicio() {
  if (localStorage.getItem('token')) {
    router.push('/dashboard')
  } else {
    router.push('/')
  }
}
</script>

<style scoped>
.notfound {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg);
  padding: 24px;
  font-family: var(--font);
}

.nf-card {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  padding: var(--s-5) var(--s-4);
  text-align: center;
  max-width: 420px;
}

.nf-code {
  font-family: var(--font);
  font-size: 48px;
  font-weight: 800;
  color: var(--brand);
  line-height: 1;
  margin-bottom: var(--s-3);
}

.nf-card h1 {
  font-family: var(--font);
  font-size: 20px;
  font-weight: 700;
  color: var(--ink);
  margin: 0 0 var(--s-2);
}

.nf-card p {
  font-size: 13px;
  color: var(--ink-2);
  margin: 0 0 var(--s-4);
}

.nf-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--brand);
  color: white;
  border: none;
  border-radius: var(--r-md);
  padding: 11px 22px;
  font-size: 13px;
  font-weight: 600;
  font-family: var(--font);
  cursor: pointer;
  transition: background 0.2s ease;
}

.nf-btn:hover {
  background: var(--brand-strong);
}
</style>

<template>
  <aside class="sidebar" :class="{ open }">
    <div class="sidebar-brand">
      <img src="../assets/logo-univac.png" alt="UNIVAC" class="brand-logo" />
      <div class="brand-info">
        <span class="brand-name">UNIVAC</span>
        <span class="brand-sub">Sistema de Gestión</span>
      </div>
    </div>

    <nav class="sidebar-nav">
      <router-link to="/dashboard" class="nav-item" :class="{active:activeItem==='inicio'}" @click="setActive('inicio')">
        <svg viewBox="0 0 20 20" fill="currentColor" width="18" height="18"><path d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z"/></svg>
        <span>Inicio</span>
      </router-link>

      <div class="nav-section">
        <button class="nav-section-btn" :class="{open:openSections.informes}" @click="toggle('informes')">
          <svg viewBox="0 0 20 20" fill="currentColor" width="18" height="18"><path fill-rule="evenodd" d="M3 3a2 2 0 012-2h5.586A2 2 0 0112 2.586L17.414 8A2 2 0 0118 9.414V17a2 2 0 01-2 2H5a2 2 0 01-2-2V3zm2 0v14h11V9.414L10.586 3H5zm3 8a1 1 0 011-1h4a1 1 0 110 2H9a1 1 0 01-1-1zm0 3a1 1 0 011-1h4a1 1 0 110 2H9a1 1 0 01-1-1zm0 3a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z" clip-rule="evenodd"/></svg>
          <span>Informes</span>
          <svg class="nav-arrow" viewBox="0 0 20 20" fill="currentColor" width="14" height="14"><path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd"/></svg>
        </button>
        <div class="nav-sub" :style="{maxHeight:openSections.informes?'4200px':'0'}"><MenuInformes /></div>
      </div>
    </nav>

    <div class="sidebar-footer">
      <span class="footer-text">UNIVAC ERP v1.0</span>
    </div>
  </aside>
</template>

<script setup>
import { ref, reactive, watch, computed, defineAsyncComponent } from 'vue'
import { useRoute } from 'vue-router'
const MenuInformes = defineAsyncComponent(() => import('./MenuInformes.vue'))

defineProps({
  open: { type: Boolean, default: false },
})

const route = useRoute()
const activeItem = ref('inicio')

const openSections = reactive({
  informes: false,
})

const sectionForPath = computed(() => {
  const p = route.path
  if (p === '/dashboard') return 'inicio'
  if (p === '/dashboard/perfil') return null
  if (p.startsWith('/dashboard/')) return 'informes'
  return null
})

watch(sectionForPath, (sec) => {
  if (sec === 'inicio') {
    activeItem.value = 'inicio'
    return
  }
  if (sec) {
    activeItem.value = ''
    openSections.informes = true
  }
}, { immediate: true })

function toggle(section) {
  openSections[section] = !openSections[section]
}

function setActive(item) {
  activeItem.value = item
  openSections.informes = false
}
</script>

<style scoped>
.sidebar {
  width: 260px;
  min-height: 100vh;
  background: var(--brand-strong);
  color: #fff;
  font-family: var(--font);
  display: flex;
  flex-direction: column;
  user-select: none;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 22px 20px 20px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}

.brand-logo {
  width: 38px;
  height: 38px;
  object-fit: contain;
  flex-shrink: 0;
}

.brand-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.brand-name {
  font-family: var(--font);
  font-size: 16px;
  font-weight: 700;
  letter-spacing: -0.2px;
  line-height: 1.2;
}

.brand-sub {
  font-size: 10px;
  color: #7E99B0;
  font-weight: 500;
  letter-spacing: 0.2px;
}

.sidebar-nav {
  flex: 1;
  min-height: 0;
  padding: 10px 10px;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-radius: var(--r-md);
  color: #AEC3D4;
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.15s;
  margin-bottom: 2px;
}

.nav-item:hover {
  background: rgba(255,255,255,0.06);
  color: #E7EEF5;
}

.nav-item.active {
  background: rgba(44, 97, 120, 0.32);
  color: #B9D7EA;
}

.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  border-radius: 3px;
  background: var(--brand-mid);
}

.nav-item { position: relative; }

.nav-item svg { flex-shrink: 0; }

.nav-section { margin-bottom: 2px; }

.nav-section-btn {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 10px 14px;
  border: none;
  border-radius: var(--r-md);
  background: transparent;
  color: #AEC3D4;
  font-family: inherit;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  text-align: left;
  position: relative;
}

.nav-section-btn:hover {
  background: rgba(255,255,255,0.06);
  color: #E7EEF5;
}

.nav-section-btn.open {
  color: #E7EEF5;
  background: rgba(255,255,255,0.04);
}

.nav-section-btn.open::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  border-radius: 3px;
  background: var(--brand-mid);
}

.nav-section-btn svg { flex-shrink: 0; }

.nav-section-btn span { flex: 1; }

.nav-arrow {
  transition: transform 0.25s ease;
  opacity: 0.5;
}

.nav-section-btn.open .nav-arrow {
  transform: rotate(180deg);
  opacity: 0.8;
}

.nav-sub {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.25s ease;
  padding-left: 8px;
}

.sidebar-footer {
  padding: 14px 20px;
  border-top: 1px solid rgba(255,255,255,0.06);
}

.footer-text {
  font-size: 11px;
  color: #67829B;
  font-weight: 500;
}

.sidebar::-webkit-scrollbar { width: 4px; }
.sidebar::-webkit-scrollbar-track { background: transparent; }
.sidebar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: var(--r-md); }

@media (max-width: 900px) {
  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    z-index: 70;
    transform: translateX(-100%);
    transition: transform 0.25s ease;
    box-shadow: 6px 0 28px rgba(0, 0, 0, 0.22);
  }
  .sidebar.open {
    transform: translateX(0);
  }
}
</style>

<template>
  <div class="dashboard">
    <Sidebar :open="menuOpen" />
    <div v-if="menuOpen" class="sidebar-backdrop" @click="menuOpen = false"></div>
    <div class="contenido">
      <Navbar @toggle-menu="menuOpen = !menuOpen" />
      <main class="pagina">
        <router-view v-slot="{ Component, route }">
          <transition name="subpagina" mode="out-in">
            <component :is="Component" :key="route.fullPath" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import Sidebar from '../components/Sidebar.vue'
import Navbar from '../components/Navbar.vue'

const route = useRoute()
const menuOpen = ref(false)

watch(() => route.fullPath, () => {
  menuOpen.value = false
})
</script>

<style scoped>
.dashboard {
  display: flex;
  min-height: 100vh;
  background: #eef1f8;
}

.contenido {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.pagina {
  flex: 1;
  overflow: auto;
  padding: 0;
}

.sidebar-backdrop {
  display: none;
}

@media (max-width: 900px) {
  .sidebar-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.45);
    z-index: 60;
  }
}

.subpagina-enter-active {
  animation: subEntrar 0.18s ease;
}

.subpagina-leave-active {
  animation: subSalir 0.12s ease;
}

@keyframes subEntrar {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes subSalir {
  from {
    opacity: 1;
  }
  to {
    opacity: 0;
  }
}
</style>

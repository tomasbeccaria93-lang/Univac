<template>
  <header class="navbar">
    <div class="navbar-l">
      <button class="menu-burger" type="button" aria-label="Abrir menú" @click="$emit('toggle-menu')">
        <i class="fas fa-bars"></i>
      </button>
      <div class="empresa">
        <img src="../assets/logo-univac.png" alt="UNIVAC" class="logo" />
        <div>
          <h2>
            {{ empresaNombre }}
            <span v-if="!empresaActiva" class="badge-inactiva">
              <i class="fas fa-ban"></i> Inactiva
            </span>
          </h2>
          <span>{{ empresaActiva ? 'Sistema de Gestión Empresarial' : 'Empresa sin operaciones activas' }}</span>
        </div>
      </div>
      <ToggleEstado class="navbar-estado" :estado="estado" @update:estado="setEstado" />
    </div>

    <div class="usuario">
      <div class="perfil">
        <button class="avatar-btn" aria-haspopup="true" :aria-expanded="mostrarMenu ? 'true' : 'false'" @click="mostrarMenu = !mostrarMenu">
          <span class="avatar-circle">{{ iniciales }}</span>
          <span class="nombre-text">{{ nombreUsuario }}</span>
          <i class="fas fa-chevron-down" :class="{ rotado: mostrarMenu }"></i>
        </button>

        <transition name="dropdown">
          <div v-if="mostrarMenu" class="menu-usuario">
            <div class="menu-header">
              <span class="menu-avatar">{{ iniciales }}</span>
              <div>
                <h3>{{ nombreUsuario }}</h3>
                <p>{{ empresaNombre }}</p>
              </div>
            </div>
            <div class="menu-divider"></div>
            <router-link to="/dashboard/perfil" class="menu-link" @click="mostrarMenu = false">
              <i class="fas fa-user-circle"></i>
              <span>Mi Perfil</span>
              <i class="fas fa-chevron-right menu-link-arrow"></i>
            </router-link>
            <div class="menu-divider"></div>
            <div class="menu-item-info">
              <i class="fas fa-id-badge"></i>
              <span>{{ nombreCompleto }}</span>
            </div>
          </div>
        </transition>
      </div>

      <button class="salir" @click="cerrarSesion">
        <i class="fas fa-right-from-bracket"></i>
        Cerrar sesión
      </button>
    </div>
  </header>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'
import { limpiarSesion } from '../utils/sesion'
import ToggleEstado from './ToggleEstado.vue'
import { useEstadoDatos } from '../composables/useEstadoDatos'

const router = useRouter()
const mostrarMenu = ref(false)
const { estado, setEstado } = useEstadoDatos()

defineEmits(['toggle-menu'])

const nombreCompleto = ref(localStorage.getItem('nombre') || 'Usuario')
const nombreUsuario = ref(localStorage.getItem('usuario_nombre') || 'Usuario')
const empresaNombre = ref(localStorage.getItem('empresa_nombre') || 'UNIVAC ERP')
const empresaActiva = ref(localStorage.getItem('empresa_activa') !== 'false')

const iniciales = computed(() => {
  let n = nombreCompleto.value.trim()
  if (!n) return 'U'
  n = n.replace(/,/g, ' ').replace(/\s+/g, ' ').trim()
  const parts = n.split(/\s+/)
  return (parts[0][0] + (parts[1] ? parts[1][0] : '')).toUpperCase()
})

const cerrarSesion = async () => {
  try {
    await api.post('/auth/logout')
  } catch {
  }
  limpiarSesion()
  router.replace('/')
}

const cerrarFuera = (e) => {
  if (!e.target.closest('.perfil')) {
    mostrarMenu.value = false
  }
}

onMounted(() => document.addEventListener('click', cerrarFuera))
onBeforeUnmount(() => document.removeEventListener('click', cerrarFuera))
</script>

<style scoped>
.navbar {
  height: 70px;
  background: var(--surface);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 30px;
  border-bottom: 1px solid var(--line);
  position: relative;
  z-index: 50;
}

.navbar-l {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}

.navbar-estado {
  flex-shrink: 0;
}

.menu-burger {
  display: none;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: 1px solid var(--line);
  background: var(--surface);
  color: var(--brand);
  border-radius: var(--r-md);
  cursor: pointer;
  font-size: 15px;
  flex-shrink: 0;
}

.menu-burger:hover {
  background: var(--g-100);
  border-color: var(--brand-mid);
}

.empresa {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}

.empresa > div {
  min-width: 0;
}

.logo {
  width: 44px;
  height: 44px;
  object-fit: contain;
}

.empresa h2 {
  margin: 0;
  color: var(--ink);
  font-size: 20px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.badge-inactiva {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: var(--danger-bg);
  color: var(--danger);
  font-size: 11px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: var(--r-md);
  border: 1px solid #F3C6C2;
}

.empresa span {
  font-size: 12px;
  color: var(--ink-3);
}

.usuario {
  display: flex;
  align-items: center;
  gap: 16px;
}

.perfil {
  position: relative;
}

.avatar-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--g-100);
  border: 2px solid transparent;
  padding: 8px 16px 8px 8px;
  border-radius: var(--r-md);
  cursor: pointer;
  transition: all 0.25s ease;
  font-family: var(--font);
}

.avatar-btn:hover {
  background: #E8ECF4;
  border-color: #D0D8E8;
}

.avatar-circle {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--brand);
  color: white;
  border-radius: var(--r-md);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.nombre-text {
  color: var(--ink);
  font-weight: 600;
  font-size: 14px;
}

.avatar-btn i {
  font-size: 11px;
  color: var(--ink-3);
  transition: transform 0.3s ease;
}

.avatar-btn i.rotado {
  transform: rotate(180deg);
}

.menu-usuario {
  position: absolute;
  right: 0;
  top: 58px;
  width: 270px;
  background: white;
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  z-index: 100;
  overflow: hidden;
}

.menu-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px;
}

.menu-avatar {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--brand);
  color: white;
  border-radius: var(--r-md);
  font-size: 15px;
  font-weight: 700;
  flex-shrink: 0;
}

.menu-header h3 {
  margin: 0 0 4px;
  color: var(--ink);
  font-size: 16px;
  font-weight: 700;
}

.menu-header p {
  margin: 0;
  color: var(--ink-3);
  font-size: 12px;
}

.menu-divider {
  height: 1px;
  background: var(--line);
  margin: 0 16px;
}

.menu-link {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  color: var(--ink);
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.2s ease;
  cursor: pointer;
}

.menu-link:hover {
  background: var(--g-100);
  color: var(--brand);
}

.menu-link i:first-child {
  color: var(--brand);
  font-size: 16px;
  width: 20px;
  text-align: center;
}

.menu-link span {
  flex: 1;
}

.menu-link-arrow {
  font-size: 10px;
  color: #b0bdd4;
  transition: transform 0.2s ease;
}

.menu-link:hover .menu-link-arrow {
  transform: translateX(3px);
  color: var(--brand);
}

.menu-item-info {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 20px;
  color: #5a6478;
  font-size: 13px;
}

.menu-item-info i {
  color: #b0bdd4;
}

.dropdown-enter-active {
  animation: dropIn 0.2s ease;
}
.dropdown-leave-active {
  animation: dropIn 0.2s ease reverse;
}
@keyframes dropIn {
  from { opacity: 0; transform: translateY(-8px) scale(0.97); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.salir {
  display: flex;
  align-items: center;
  gap: 8px;
  background: transparent;
  color: #5a6478;
  border: 1px solid #d0d8e8;
  padding: 9px 16px;
  border-radius: var(--r-md);
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  font-family: var(--font);
  transition: all 0.2s ease;
}

.salir:hover {
  background: var(--g-100);
  color: var(--ink);
  border-color: var(--line);
}

.salir i {
  font-size: 14px;
}

@media (max-width: 900px) {
  .navbar {
    padding: 0 12px;
    height: 60px;
  }
  .menu-burger {
    display: inline-flex;
  }
  .logo {
    width: 34px;
    height: 34px;
  }
  .empresa {
    gap: 10px;
  }
  .empresa h2 {
    font-size: 15px;
  }
  .empresa span {
    display: none;
  }
  .usuario {
    gap: 8px;
  }
  .avatar-btn {
    padding: 5px;
  }
  .nombre-text,
  .avatar-btn i {
    display: none;
  }
  .salir {
    padding: 8px 10px;
    font-size: 0;
  }
  .salir i {
    font-size: 14px;
    margin: 0;
  }
}
</style>

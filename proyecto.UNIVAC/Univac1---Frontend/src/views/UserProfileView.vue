<template>
  <div class="perfil-page">
    <div v-if="cargando" class="cargando-overlay">
      <div class="cargando-box">
        <div class="cargando-spinner"></div>
        <p>Cargando perfil...</p>
      </div>
    </div>

    <div v-else-if="error" class="error-box">
      <i class="fas fa-triangle-exclamation"></i>
      <p>{{ error }}</p>
      <button @click="cargar"><i class="fas fa-rotate-right"></i> Reintentar</button>
    </div>

    <div v-else class="perfil-panel">
      <div class="perfil-head">
        <div class="perfil-head-izq">
          <h2>Perfil de Usuario</h2>
          <p class="perfil-sub">
            {{ perfil.nombre }} {{ perfil.apellido }} <span class="perfil-sep">•</span> {{ textoRol }}
          </p>
          <p v-if="perfil.empresa_nombre" class="perfil-empresa">{{ perfil.empresa_nombre }}</p>
        </div>
        <div class="perfil-head-der">
          <span class="badge" :class="perfil.bloqueado ? 'badge-inactivo' : 'badge-activo'">
            {{ perfil.bloqueado ? 'Deshabilitado' : 'Activo' }}
          </span>
        </div>
      </div>

      <div class="perfil-cuerpo">
        <div class="perfil-col">
          <section class="perfil-seccion">
            <h3>Datos Personales</h3>
            <div class="seccion-cuerpo">
              <div class="fila">
                <span class="fila-label">Nombre completo</span>
                <span class="fila-valor">{{ perfil.nombre }} {{ perfil.apellido }}</span>
              </div>
              <div class="fila">
                <span class="fila-label">Usuario</span>
                <span class="fila-valor">{{ perfil.usuario }}</span>
              </div>
              <div class="fila">
                <span class="fila-label">Documento</span>
                <span class="fila-valor">{{ perfil.documento || '---' }}</span>
              </div>
              <div class="fila">
                <span class="fila-label">Identificación</span>
                <span class="fila-valor">{{ perfil.identificacion || '---' }}</span>
              </div>
              <div class="fila" v-if="perfil.dia_cumpleanos && perfil.mes_cumpleanos">
                <span class="fila-label">Cumpleaños</span>
                <span class="fila-valor">{{ diaCumpleanos }}</span>
              </div>
            </div>
          </section>
        </div>

        <div class="perfil-col perfil-col-borde">
          <section class="perfil-seccion">
            <h3>Configuración y Permisos</h3>
            <div class="seccion-cuerpo">
              <div class="fila">
                <span class="fila-label">Visualiza Totales</span>
                <span class="badge" :class="perfil.visualiza_totales ? 'badge-activo' : 'badge-inactivo'">
                  {{ perfil.visualiza_totales ? 'Activo' : 'Inactivo' }}
                </span>
              </div>
              <div class="fila">
                <span class="fila-label">Venta Rápida</span>
                <span class="badge" :class="perfil.venta_rapida ? 'badge-activo' : 'badge-inactivo'">
                  {{ perfil.venta_rapida ? 'Activo' : 'Inactivo' }}
                </span>
              </div>
              <div class="fila">
                <span class="fila-label">Modifica Precio Venta</span>
                <span class="badge" :class="perfil.modifica_precio_venta ? 'badge-activo' : 'badge-inactivo'">
                  {{ perfil.modifica_precio_venta ? 'Activo' : 'Inactivo' }}
                </span>
              </div>
              <div class="fila">
                <span class="fila-label">Scanner</span>
                <span class="badge" :class="perfil.scanner ? 'badge-activo' : 'badge-inactivo'">
                  {{ perfil.scanner ? 'Activo' : 'Inactivo' }}
                </span>
              </div>
              <div class="fila">
                <span class="fila-label">Nivel de clave</span>
                <span class="fila-valor">{{ perfil.nivel_clave || 'Sin nivel' }}</span>
              </div>
              <div class="fila">
                <span class="fila-label">Orden artículos</span>
                <span class="fila-valor">{{ perfil.ordenamiento_articulos || 'Por defecto' }}</span>
              </div>
              <div class="fila">
                <span class="fila-label">Rol</span>
                <span class="fila-valor">{{ textoRol }}</span>
              </div>
            </div>
          </section>
        </div>

        <section class="perfil-seccion perfil-seccion-ancho">
          <h3>Horario de Acceso</h3>
          <div class="seccion-cuerpo">
            <div class="fila">
              <span class="fila-label">Rango horario</span>
              <span class="fila-valor">{{ perfil.hora_desde || '--:--' }} hs a {{ perfil.hora_hasta || '--:--' }} hs</span>
            </div>
            <div class="fila" v-if="perfil.estado_default">
              <span class="fila-label">Estado por defecto</span>
              <span class="fila-valor">{{ perfil.estado_default }}</span>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../api'

const perfil = ref({})
const cargando = ref(true)
const error = ref('')

const textoRol = computed(() => {
  const roles = { 1: 'Administrador', 2: 'Supervisor', 3: 'Operador', 4: 'Consultas' }
  return roles[perfil.value.rol] || 'Usuario'
})

const diaCumpleanos = computed(() => {
  if (!perfil.value.dia_cumpleanos || !perfil.value.mes_cumpleanos) return ''
  const meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
  return `${perfil.value.dia_cumpleanos} de ${meses[perfil.value.mes_cumpleanos - 1] || ''}`
})

const cargar = async () => {
  cargando.value = true
  error.value = ''
  try {
    const { data } = await api.get('/auth/me')
    perfil.value = data
  } catch (e) {
    error.value = e.response?.data?.detail || 'No se pudo cargar el perfil.'
  } finally {
    cargando.value = false
  }
}

onMounted(cargar)
</script>

<style scoped>
.perfil-page {
  width: 100%;
  max-width: var(--page-max);
  margin: 0 auto;
  padding: var(--s-5) var(--s-5) var(--s-6);
  font-family: var(--font);
}

.perfil-panel {
  width: 100%;
  background: var(--surface);
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05);
  overflow: hidden;
}

.perfil-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 24px 28px;
  border-bottom: 1px solid #e5e7eb;
}

.perfil-head h2 {
  margin: 0 0 4px;
  font-size: 18px;
  font-weight: 700;
  color: #111827;
  letter-spacing: -0.2px;
}

.perfil-sub {
  margin: 0;
  font-size: 14px;
  color: #6b7280;
  font-weight: 500;
  line-height: 1.4;
}

.perfil-sep {
  color: #9ca3af;
  padding: 0 2px;
}

.perfil-empresa {
  margin: 4px 0 0;
  font-size: 13px;
  color: #9ca3af;
}

.perfil-head-der {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  padding-top: 2px;
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.5;
  white-space: nowrap;
}

.badge-activo {
  background: #ecfdf5;
  color: #047857;
  border: 1px solid #a7f3d0;
}

.badge-inactivo {
  background: #f3f4f6;
  color: #6b7280;
  border: 1px solid #e5e7eb;
}

.perfil-cuerpo {
  display: grid;
  grid-template-columns: 1fr 1fr;
}

.perfil-head-izq {
  min-width: 0;
}

.perfil-col {
  min-width: 0;
}

.perfil-col-borde {
  border-left: 1px solid #e5e7eb;
}

.perfil-seccion {
  padding: 20px 28px 24px;
}

.perfil-seccion h3 {
  margin: 0 0 12px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #6b7280;
}

.seccion-cuerpo {
  display: flex;
  flex-direction: column;
}

.fila {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 0;
  border-bottom: 1px solid #f3f4f6;
}

.fila:last-child {
  border-bottom: none;
}

.fila-label {
  font-size: 13px;
  color: #6b7280;
}

.fila-valor {
  font-size: 14px;
  color: #111827;
  font-weight: 500;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.perfil-seccion-ancho {
  grid-column: 1 / -1;
  border-top: 1px solid #e5e7eb;
}

.cargando-overlay {
  display: flex;
  justify-content: center;
  padding: 80px 20px;
}

.cargando-box {
  text-align: center;
  background: var(--surface);
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 32px 44px;
}

.cargando-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e5e7eb;
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: girar 0.8s linear infinite;
  margin: 0 auto 14px;
}

@keyframes girar { to { transform: rotate(360deg); } }

.cargando-box p {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.error-box {
  text-align: center;
  background: var(--surface);
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 40px 32px;
  max-width: 640px;
  margin: 0 auto;
}

.error-box i {
  font-size: 34px;
  color: #b91c1c;
  margin-bottom: 14px;
}

.error-box p {
  color: #6b7280;
  font-size: 14px;
  margin: 0 0 20px;
}

.error-box button {
  background: #111827;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 10px 22px;
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
  font-family: var(--font);
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transition: background 0.2s ease;
}

.error-box button:hover {
  background: #1f2937;
}

@media (max-width: 900px) {
  .perfil-cuerpo {
    grid-template-columns: 1fr;
  }

  .perfil-col-borde {
    border-left: none;
    border-top: 1px solid #e5e7eb;
  }

  .perfil-seccion-ancho {
    grid-column: 1;
    border-top: 1px solid #e5e7eb;
  }
}

@media (max-width: 600px) {
  .perfil-page {
    padding: var(--s-4);
  }

  .perfil-head {
    flex-direction: column;
    padding: var(--s-4);
  }

  .perfil-seccion {
    padding: var(--s-4) var(--s-5);
  }

  .fila {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .fila-valor {
    text-align: left;
    overflow-wrap: anywhere;
  }

  .fila-label {
    overflow-wrap: anywhere;
  }
}
</style>
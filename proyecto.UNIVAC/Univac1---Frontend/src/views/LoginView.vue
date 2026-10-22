<template>
  <div class="login-page">
    <div class="left-panel">
      <div class="brand" :class="{ visible: brandVisible }">
        <div class="kicker">Cluster Tecnológico San Francisco</div>
        <div class="logo-frame">
          <div class="logo-ring"></div>
          <img src="../assets/logo-univac.png" alt="UNIVAC" class="logo" />
        </div>
        <h1>UNIVAC</h1>
        <h2>Sistema de Gestión Empresarial</h2>
        <p>Administración integral de ventas, compras, clientes, proveedores y resultados.</p>
      </div>

      <div class="left-foot">UNIVAC ERP &mdash; 2026</div>
    </div>

    <div class="right-panel">
      <a href="https://clustersanfrancisco.com.ar/" target="_blank" rel="noopener noreferrer" class="link-info">
        Acerca de UNIVAC
      </a>

      <transition name="cambio-panel" mode="out-in">
        <div v-if="!mostrandoEmpresas" key="login" class="login-block" :class="{ visible: cardVisible }">
          <div class="card-head">
            <h3>Acceso al sistema</h3>
            <p>Ingresá tus credenciales para acceder a tu empresa</p>
          </div>
          <form @submit.prevent="login" autocomplete="off">
            <div class="campo" :class="{ focus: focusDoc, filled: documento }">
              <label for="login-documento">N° de Documento</label>
              <input id="login-documento" v-model="documento" type="text" placeholder="Ej: 30123456" @focus="focusDoc = true" @blur="focusDoc = false" />
            </div>
            <div class="campo" :class="{ focus: focusUser, filled: usuario }">
              <label for="login-usuario">Usuario</label>
              <input id="login-usuario" v-model="usuario" type="text" placeholder="Tu nombre de usuario" @focus="focusUser = true" @blur="focusUser = false" />
            </div>
            <div class="campo" :class="{ focus: focusPass, filled: clave }">
              <label for="login-clave">Contraseña</label>
              <div class="pass-wrap">
                <input id="login-clave" v-model="clave" :type="verClave ? 'text' : 'password'" placeholder="Tu contraseña" @focus="focusPass = true" @blur="focusPass = false" />
                <button type="button" class="toggle-pass" @click="verClave = !verClave" tabindex="-1">
                  <i :class="verClave ? 'fas fa-eye-slash' : 'fas fa-eye'"></i>
                </button>
              </div>
            </div>
            <button type="submit" class="btn-login" :class="{ loading: cargando }" :disabled="cargando">
              <span v-if="!cargando">Iniciar Sesión</span>
              <span v-else class="spinner"></span>
            </button>
            <transition name="mensaje">
              <div v-if="mensaje" class="mensaje" :class="tipoMensaje">
                <i :class="tipoMensaje === 'error' ? 'fas fa-circle-exclamation' : 'fas fa-circle-check'"></i>
                {{ mensaje }}
              </div>
            </transition>
          </form>
        </div>

        <div v-else key="empresas" class="login-block" :class="{ visible: cardVisible }">
          <div class="card-head">
            <h3>Elegí tu Empresa</h3>
            <p>Seleccioná la empresa con la que querés trabajar</p>
          </div>
          <div class="empresas-lista">
            <button
              v-for="emp in empresasActivas"
              :key="emp.id"
              class="empresa-item"
              :class="{ seleccionando: empresaSeleccionando === emp.id }"
              @click="seleccionarEmpresa(emp)"
              :disabled="empresaSeleccionando !== null"
            >
              <span class="emp-estado on"></span>
              <div class="emp-info">
                <h4>{{ emp.nombre }}</h4>
                <span v-if="emp.cuit" class="emp-cuit">CUIT: {{ emp.cuit }}</span>
              </div>
              <div class="emp-flecha">
                <span v-if="empresaSeleccionando === emp.id" class="mini-spinner"></span>
                <i v-else class="fas fa-chevron-right"></i>
              </div>
            </button>
          </div>
          <button class="btn-volver" @click="volverAlLogin" :disabled="empresaSeleccionando !== null">
            <i class="fas fa-arrow-left"></i> Volver al login
          </button>
          <transition name="mensaje">
            <div v-if="mensaje" class="mensaje" :class="tipoMensaje">
              <i :class="tipoMensaje === 'error' ? 'fas fa-circle-exclamation' : 'fas fa-circle-check'"></i>
              {{ mensaje }}
            </div>
          </transition>
        </div>
      </transition>
    </div>

    <footer class="footer-login">
      <p>2026 Cluster Tecnológico San Francisco. Todos los derechos reservados.</p>
      <span>San Francisco, Córdoba, Argentina</span>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'

const router = useRouter()
const documento = ref('')
const usuario = ref('')
const clave = ref('')
const verClave = ref(false)
const mensaje = ref('')
const tipoMensaje = ref('')
const cargando = ref(false)
const focusDoc = ref(false)
const focusUser = ref(false)
const focusPass = ref(false)
const brandVisible = ref(false)
const cardVisible = ref(false)

const mostrandoEmpresas = ref(false)
const empresas = ref([])
const empresaSeleccionando = ref(null)

const empresasActivas = computed(() => empresas.value.filter((e) => e.activa))

onMounted(() => {
  setTimeout(() => { brandVisible.value = true }, 100)
  setTimeout(() => { cardVisible.value = true }, 300)
})

const login = async () => {
  mensaje.value = ''
  if (!documento.value.trim()) { mensaje.value = 'Debe ingresar el número de documento.'; tipoMensaje.value = 'error'; return }
  if (!usuario.value.trim()) { mensaje.value = 'Debe ingresar el usuario.'; tipoMensaje.value = 'error'; return }
  if (!clave.value.trim()) { mensaje.value = 'Debe ingresar la contraseña.'; tipoMensaje.value = 'error'; return }

  cargando.value = true
  try {
    const { data } = await api.post('/auth/login', {
      usuario: usuario.value.trim(),
      documento: documento.value.trim(),
      password: clave.value.trim()
    })

    if (data.require_selection) {
      const empresasDisp = data.empresas || []
      const activas = empresasDisp.filter((e) => e.activa)
      if (activas.length === 0) {
        mensaje.value = 'No tiene acceso a ninguna empresa activa.'
        tipoMensaje.value = 'error'
        cargando.value = false
        return
      }
      empresas.value = empresasDisp
      cargando.value = false
      if (activas.length === 1) {
        seleccionarEmpresa(activas[0])
        return
      }
      mostrandoEmpresas.value = true
      return
    }

    guardarSesion(data)
    mensaje.value = 'Sesión iniciada correctamente.'
    tipoMensaje.value = 'success'
    setTimeout(() => { router.push('/dashboard') }, 800)
  } catch (e) {
    mensaje.value = e.response?.data?.detail || 'No se pudo conectar con el servidor.'
    tipoMensaje.value = 'error'
    cargando.value = false
  }
}

const seleccionarEmpresa = async (emp) => {
  if (!emp.activa) {
    mensaje.value = `La empresa "${emp.nombre}" se encuentra inactiva actualmente. Comuníquese con el administrador del sistema para más información.`
    tipoMensaje.value = 'error'
    return
  }
  empresaSeleccionando.value = emp.id
  mensaje.value = ''

  try {
    const { data } = await api.post('/auth/seleccionar-empresa', {
      usuario_id: emp.usuario_id,
      empresa_id: emp.id
    })
    guardarSesion(data)
    mensaje.value = `Accediendo a ${emp.nombre}...`
    tipoMensaje.value = 'success'
    setTimeout(() => { router.push('/dashboard') }, 600)
  } catch (e) {
    mensaje.value = e.response?.data?.detail || 'No se pudo acceder a esa empresa.'
    tipoMensaje.value = 'error'
    empresaSeleccionando.value = null
  }
}

const guardarSesion = (data) => {
  try {
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('token_expiry', Date.now() + 120 * 60 * 1000)
    localStorage.setItem('usuario_id', data.usuario_id)
    localStorage.setItem('empresa_id', data.empresa_id)
    localStorage.setItem('ultima_empresa', data.empresa_id)
    localStorage.setItem('nombre', data.nombre)
    localStorage.setItem('usuario_nombre', data.usuario)
    localStorage.setItem('empresa_nombre', data.empresa_nombre)
    localStorage.setItem('empresa_activa', data.empresa_activa)
    localStorage.setItem('visualiza_totales', data.visualiza_totales)
    localStorage.setItem('venta_rapida', data.venta_rapida)
    localStorage.setItem('modifica_precio_venta', data.modifica_precio_venta)
    localStorage.setItem('scanner', data.scanner)
    localStorage.setItem('nivel_clave', data.nivel_clave ?? '')
    localStorage.setItem('ordenamiento_articulos', data.ordenamiento_articulos ?? '')
  } catch (e) {
    console.warn('No se pudo guardar la sesión (localStorage):', e)
  }
}

const volverAlLogin = () => {
  mostrandoEmpresas.value = false
  empresas.value = []
  empresaSeleccionando.value = null
  mensaje.value = ''
}
</script>

<style scoped>
.login-page {
  display: flex;
  min-height: 100vh;
  position: relative;
  background: var(--brand-strong);
  overflow: hidden;
  font-family: var(--font);
}

.left-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px;
  position: relative;
  background: linear-gradient(165deg, #0F2D3B 0%, #0A1F2A 100%);
}

.brand {
  position: relative;
  max-width: 440px;
  color: white;
  text-align: center;
  opacity: 0;
  transform: translateY(18px);
  transition: opacity 0.8s ease, transform 0.8s ease;
}
.brand.visible {
  opacity: 1;
  transform: translateY(0);
}

.kicker {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 3px;
  text-transform: uppercase;
  color: #7FA3C0;
  margin-bottom: 34px;
}

.logo-frame {
  position: relative;
  display: inline-block;
  margin-bottom: 28px;
}

.logo-ring {
  position: absolute;
  inset: -12px;
  border: 1.5px solid transparent;
  border-top-color: rgba(140, 190, 220, 0.55);
  border-right-color: rgba(140, 190, 220, 0.15);
  border-radius: 50%;
  animation: spinRing 5s linear infinite;
}

@keyframes spinRing {
  to { transform: rotate(360deg); }
}

.logo {
  width: 148px;
  display: block;
  position: relative;
  z-index: 1;
}

.brand h1 {
  font-size: 42px;
  font-weight: 700;
  letter-spacing: -1px;
  margin-bottom: 8px;
  line-height: 1;
}

.brand h2 {
  font-size: 13px;
  font-weight: 500;
  color: #8BA6BC;
  margin-bottom: 18px;
  letter-spacing: 2px;
  text-transform: uppercase;
}

.brand p {
  font-size: 14px;
  line-height: 1.7;
  color: #6E8CA3;
  max-width: 380px;
  margin: 0 auto;
}

.left-foot {
  position: absolute;
  bottom: 26px;
  font-size: 11px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.28);
}

.right-panel {
  width: 460px;
  min-width: 420px;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 48px;
  background: var(--surface);
  position: relative;
  z-index: 2;
}

.link-info {
  position: absolute;
  top: 24px;
  right: 28px;
  color: var(--ink-3);
  text-decoration: none;
  font-weight: 500;
  font-size: 12px;
  transition: color 0.2s ease;
  z-index: 5;
}
.link-info:hover { color: var(--brand); }

.login-block {
  width: 100%;
  max-width: 360px;
  opacity: 0;
  transform: translateY(14px);
  transition: opacity 0.7s ease, transform 0.7s ease;
}
.login-block.visible {
  opacity: 1;
  transform: translateY(0);
}

.cambio-panel-enter-active { animation: panelCambiar 0.3s ease; }
.cambio-panel-leave-active { animation: panelCambiar 0.2s ease reverse; }
@keyframes panelCambiar {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.card-head {
  text-align: left;
  margin-bottom: 28px;
}
.card-head h3 {
  color: var(--ink);
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 6px;
  letter-spacing: -0.3px;
}
.card-head p {
  color: var(--ink-2);
  font-size: 13px;
  line-height: 1.5;
}

.campo {
  margin-bottom: 18px;
}
.campo label {
  display: flex;
  align-items: center;
  margin-bottom: 7px;
  color: var(--ink-2);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  transition: color 0.25s ease;
}
.campo.focus label,
.campo.filled label { color: var(--brand); }

.campo input {
  width: 100%;
  padding: 11px 14px;
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  font-size: 14px;
  font-family: var(--font);
  color: var(--ink);
  background: var(--surface);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  outline: none;
}
.campo input::placeholder { color: #B4BCCB; }
.campo input:focus {
  border-color: var(--brand);
  box-shadow: 0 0 0 3px rgba(44, 97, 120, 0.12);
}

.pass-wrap { position: relative; }
.pass-wrap input { padding-right: 48px; }
.toggle-pass {
  position: absolute;
  right: 2px;
  top: 50%;
  transform: translateY(-50%);
  width: 38px;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: var(--ink-3);
  cursor: pointer;
  border-radius: var(--r-md);
  transition: background 0.2s ease, color 0.2s ease;
  font-size: 14px;
}
.toggle-pass:hover { background: var(--g-100); color: var(--brand); }

.btn-login {
  width: 100%;
  padding: 12px;
  border: none;
  border-radius: var(--r-md);
  background: var(--brand);
  color: white;
  font-size: 14px;
  font-weight: 600;
  font-family: var(--font);
  cursor: pointer;
  transition: background 0.2s ease;
  margin-top: 8px;
  letter-spacing: 0.3px;
}
.btn-login:hover:not(:disabled) { background: var(--brand-strong); }
.btn-login:active { transform: translateY(1px); }
.btn-login.loading { pointer-events: none; opacity: 0.85; }

.spinner {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 2.5px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: girar 0.7s linear infinite;
}
@keyframes girar { to { transform: rotate(360deg); } }

.mensaje {
  margin-top: 16px;
  padding: 12px 14px;
  border-radius: var(--r-md);
  font-size: 13px;
  font-weight: 500;
  line-height: 1.45;
  display: flex;
  align-items: flex-start;
  gap: 9px;
}
.mensaje i { font-size: 15px; flex-shrink: 0; margin-top: 1px; }
.mensaje.error {
  background: var(--danger-bg);
  color: var(--danger);
  border: 1px solid #F3C6C2;
}
.mensaje.success {
  background: var(--ok-bg);
  color: #146B36;
  border: 1px solid #BFE3CE;
}
.mensaje-enter-active { animation: aparecerMsj 0.3s ease; }
.mensaje-leave-active { animation: aparecerMsj 0.2s ease reverse; }
@keyframes aparecerMsj {
  from { opacity: 0; transform: translateY(-6px); }
  to { opacity: 1; transform: translateY(0); }
}

.empresas-lista {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 18px;
  max-height: 340px;
  overflow-y: auto;
  padding-right: 4px;
}
.empresas-lista::-webkit-scrollbar { width: 5px; }
.empresas-lista::-webkit-scrollbar-track { background: transparent; }
.empresas-lista::-webkit-scrollbar-thumb { background: var(--line); border-radius: 10px; }

.empresa-item {
  display: flex;
  align-items: center;
  gap: 13px;
  padding: 13px 16px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  cursor: pointer;
  transition: border-color 0.2s ease, background 0.2s ease;
  font-family: var(--font);
  text-align: left;
}
.empresa-item:hover:not(:disabled) {
  border-color: var(--brand-mid);
  background: var(--g-100);
}
.empresa-item.seleccionando {
  border-color: var(--brand-mid);
  background: var(--g-100);
  pointer-events: none;
}
.empresa-item:disabled { opacity: 0.5; cursor: not-allowed; }

.emp-estado {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex-shrink: 0;
}
.emp-estado.on { background: var(--ok); }

.emp-info { flex: 1; min-width: 0; }
.emp-info h4 {
  margin: 0 0 2px;
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.emp-info span { font-size: 12px; color: var(--ink-2); display: block; }

.emp-flecha {
  color: #B4BCCB;
  font-size: 13px;
  flex-shrink: 0;
  transition: color 0.2s ease;
}
.empresa-item:hover:not(:disabled) .emp-flecha { color: var(--brand-mid); }

.mini-spinner {
  display: inline-block;
  width: 15px;
  height: 15px;
  border: 2px solid var(--line);
  border-top-color: var(--brand-mid);
  border-radius: 50%;
  animation: girar 0.6s linear infinite;
}

.btn-volver {
  width: 100%;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  background: var(--surface);
  color: var(--ink-2);
  font-size: 13px;
  font-weight: 600;
  font-family: var(--font);
  cursor: pointer;
  transition: border-color 0.2s ease, color 0.2s ease, background 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
.btn-volver:hover:not(:disabled) {
  border-color: var(--brand-mid);
  color: var(--brand);
  background: var(--g-100);
}
.btn-volver:disabled { opacity: 0.5; cursor: not-allowed; }

.footer-login {
  position: fixed;
  bottom: 0;
  left: 0;
  width: 100%;
  background: var(--brand-strong);
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.35);
  text-align: center;
  padding: 11px 10px;
  z-index: 10;
}
.footer-login p { margin: 0; font-weight: 500; font-size: 12px; }
.footer-login span { display: block; color: rgba(255, 255, 255, 0.2); font-size: 11.5px; margin-top: 1px; }

@media (max-width: 1000px) {
  .login-page { flex-direction: column; }
  .left-panel { padding: 40px 30px; min-height: auto; }
  .right-panel { width: 100%; min-width: auto; padding: 40px 30px; padding-bottom: 90px; }
  .brand h1 { font-size: 34px; }
  .card-head h3 { font-size: 20px; }
  .footer-login { position: relative; }
}

@media (max-width: 600px) {
  .left-panel { padding: 28px 20px; }
  .kicker { margin-bottom: 24px; }
  .logo { width: 110px; }
  .logo-ring { inset: -9px; }
  .brand h1 { font-size: 28px; }
  .brand h2 { font-size: 12px; letter-spacing: 1px; }
  .brand p { font-size: 12px; }

  .right-panel { padding: 28px 20px; padding-bottom: 80px; }
  .link-info { top: 16px; right: 16px; font-size: 11px; }
  .login-block { max-width: 100%; }
  .card-head { margin-bottom: 24px; }
  .card-head h3 { font-size: 19px; }
  .card-head p { font-size: 12px; }
  .campo input { padding: 10px 12px; font-size: 13px; }
  .btn-login { padding: 11px; font-size: 13px; }

  .footer-login { padding: 10px 8px; }
  .footer-login p { font-size: 11px; }
  .footer-login span { font-size: 10.5px; }
}
</style>

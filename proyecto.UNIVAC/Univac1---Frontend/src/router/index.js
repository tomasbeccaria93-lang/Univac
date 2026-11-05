import { createRouter, createWebHistory } from 'vue-router'
import api from '../api'
import {
  estaLogueado,
  guardarCsrf,
  limpiarSesion,
  obtenerCsrf
} from '../utils/sesion'

const LoginView = () => import('../views/LoginView.vue')
const DashboardView = () => import('../views/DashboardView.vue')
const HomeDashboardView = () => import('../views/HomeDashboardView.vue')
const UserProfileView = () => import('../views/UserProfileView.vue')
const NotFoundView = () => import('../views/NotFoundView.vue')

const PosicionMensualIVA = () => import('../views/compras/PosicionMensualIVA.vue')
const ComprasAcumuladas = () => import('../views/compras/ComprasAcumuladasView.vue')
const ComprasProvincias = () => import('../views/compras/ComprasProvinciasView.vue')
const ComprasProveedores = () => import('../views/compras/ComprasProveedoresView.vue')
const ComprasInsumos = () => import('../views/compras/ComprasInsumosView.vue')
const Gastos = () => import('../views/compras/GastosView.vue')

const ComprasVentasArticulos = () => import('../views/movimientos/ComprasVentasArticulosView.vue')

const Comparativos = () => import('../views/herramientas/HerramientasComparativosView.vue')
const Facturacion = () => import('../views/herramientas/HerramientasFacturacionView.vue')
const Cuenta = () => import('../views/herramientas/HerramientasCuentaView.vue')
const Indicadores = () => import('../views/herramientas/HerramientasIndicadoresView.vue')

const Acumuladas = () => import('../views/ventas/VentasAcumuladasView.vue')
const Clientes = () => import('../views/ventas/VentasClientesView.vue')
const Comprobante = () => import('../views/ventas/VentasComprobanteView.vue')
const VProductos = () => import('../views/ventas/VentasProductosView.vue')
const Provincias = () => import('../views/ventas/VentasProvinciasView.vue')
const Vendedor = () => import('../views/ventas/VentasVendedorView.vue')
const Zonas = () => import('../views/ventas/VentasZonasView.vue')
const Totales = () => import('../views/ventas/VentasTotalesView.vue')
const Vendedores = () => import('../views/ventas/VentasVendedorArticulosView.vue')
const VendedoresRubros = () => import('../views/ventas/VentasVendedorRubrosView.vue')

const ResultadoVentas = () => import('../views/resultados/ResultadoVentasView.vue')

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),

  routes: [
    {
      path: '/',
      component: LoginView,
      beforeEnter: (_, __, next) => {
        if (estaLogueado()) {
          next('/dashboard')
        } else {
          next()
        }
      }
    },

    {
      path: '/dashboard',
      component: DashboardView,
      children: [
        {
          path: '',
          component: HomeDashboardView
        },
        {
          path: 'perfil',
          component: UserProfileView
        },
        {
          path: 'compras/iva',
          component: PosicionMensualIVA
        },
        {
          path: 'compras/acumuladas',
          component: ComprasAcumuladas
        },
        {
          path: 'compras/provincias',
          component: ComprasProvincias
        },
        {
          path: 'compras/proveedores',
          component: ComprasProveedores
        },
        {
          path: 'compras/insumos',
          component: ComprasInsumos
        },
        {
          path: 'compras/gastos',
          component: Gastos
        },
        {
          path: 'movimientos/compras-ventas',
          component: ComprasVentasArticulos
        },
        {
          path: 'herramientas/comparativos',
          component: Comparativos
        },
        {
          path: 'herramientas/cuenta',
          component: Cuenta
        },
        {
          path: 'herramientas/facturacion',
          component: Facturacion
        },
        {
          path: 'herramientas/indicadores',
          component: Indicadores
        },
        {
          path: 'ventas/acumuladas',
          component: Acumuladas
        },
        {
          path: 'ventas/clientes',
          component: Clientes
        },
        {
          path: 'ventas/comprobante',
          component: Comprobante
        },
        {
          path: 'ventas/productos',
          component: VProductos
        },
        {
          path: 'ventas/provincias',
          component: Provincias
        },
        {
          path: 'ventas/vendedor',
          component: Vendedor
        },
        {
          path: 'ventas/vendedores',
          component: Vendedores
        },
        {
          path: 'ventas/vendedores-rubros',
          component: VendedoresRubros
        },
        {
          path: 'ventas/zonas',
          component: Zonas
        },
        {
          path: 'ventas/totales',
          component: Totales
        },
        {
          path: 'resultados/ventas',
          component: ResultadoVentas
        }
      ]
    },

    {
      path: '/:pathMatch(.*)*',
      component: NotFoundView
    }
  ]
})

router.beforeEach(async (to, from, next) => {
  if (to.path === '/') {
    if (estaLogueado()) {
      next('/dashboard')
    } else {
      next()
    }
    return
  }

  if (!estaLogueado()) {
    limpiarSesion()
    next('/')
    return
  }

  if (!obtenerCsrf()) {
    try {
      const { data } = await api.get('/auth/me')
      guardarCsrf(data.csrf_token)
    } catch {
      limpiarSesion()
      next('/')
      return
    }
  }

  next()
})

export default router
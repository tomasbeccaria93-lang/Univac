import { ref, computed, shallowRef, watch, onBeforeUnmount } from 'vue'
import api from '../api'
import { etiquetaRango } from '../utils/format'
import { useEstadoDatos } from './useEstadoDatos'

export function useInforme(config, opciones = {}) {
  const storageKey = `univac:informe:${config.id}`
  const conVariante = Boolean(config.variantes?.length)
  const conSucursal = config.conSucursal !== false
  const { estado } = useEstadoDatos()

  const mrad = ref(config.mradInicial ?? 1)
  const segundo = ref(config.segundoInicial ?? 1)
  const desde = ref('')
  const hasta = ref('')
  const sucursal = ref('')
  const extra = ref({})

  const filas = shallowRef([])
  const cargando = ref(false)
  const error = ref('')
  const buscado = ref(false)
  const meta = shallowRef({})

  let controller = null

  const iso = (d) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

  function rangoPorDefecto() {
    const hoy = new Date()
    if (mrad.value === 1) {
      return [iso(new Date(hoy.getFullYear(), 0, 1)), iso(hoy)]
    }
    const desde30 = new Date(hoy)
    desde30.setDate(hoy.getDate() - 30)
    return [iso(desde30), iso(hoy)]
  }

  let haySesion = false
  try {
    const saved = JSON.parse(sessionStorage.getItem(storageKey) || 'null')
    if (saved) {
      if (saved.mrad !== undefined) mrad.value = saved.mrad
      if (saved.segundo !== undefined) segundo.value = saved.segundo
      desde.value = saved.desde || ''
      hasta.value = saved.hasta || ''
      sucursal.value = saved.sucursal || ''
      extra.value = saved.extra || {}
      haySesion = true
    }
  } catch {
    haySesion = false
  }

  if (opciones.segundo !== undefined) {
    segundo.value = opciones.segundo
    haySesion = true
  }

  if (!haySesion) {
    const [d, h] = rangoPorDefecto()
    desde.value = mrad.value === 1 ? d.slice(0, 7) : d
    hasta.value = mrad.value === 1 ? h.slice(0, 7) : h
  }

  watch([mrad, segundo, desde, hasta, sucursal, extra], () => {
    try {
      sessionStorage.setItem(
        storageKey,
        JSON.stringify({
          mrad: mrad.value,
          segundo: segundo.value,
          desde: desde.value,
          hasta: hasta.value,
          sucursal: sucursal.value,
          extra: extra.value
        })
      )
    } catch {
    }
  }, { deep: true })

  watch(estado, () => {
    if (buscado.value) buscar()
  })

  const esPeriodo = computed(() => mrad.value === 1)
  const tipoFecha = computed(() => (esPeriodo.value ? 'month' : 'date'))
  const granularidad = computed(() => (esPeriodo.value ? 'mes' : 'dia'))

  function cambiarModo(v) {
    if (mrad.value === v) return
    mrad.value = v
    if (config.alCambiarModo) config.alCambiarModo(v)
    limpiarResultados()
    ajustarFechasAlTipo()
  }

  function cambiarSegundo(v) {
    if (segundo.value === v) return
    segundo.value = v
    limpiarResultados()
  }

  function ajustarFechasAlTipo() {
    const esMes = mrad.value === 1
    desde.value = recortar(esMes ? desde.value.slice(0, 7) : desde.value, esMes)
    hasta.value = recortar(esMes ? hasta.value.slice(0, 7) : hasta.value, esMes)
  }

  function recortar(v, esMes) {
    if (!v) return ''
    if (esMes) return /^\d{4}-\d{2}$/.test(v) ? v : v.slice(0, 7)
    return /^\d{4}-\d{2}-\d{2}$/.test(v) ? v : v.slice(0, 10)
  }

  function limpiarResultados() {
    filas.value = []
    meta.value = {}
    error.value = ''
    buscado.value = false
  }

  const rangoInvalido = computed(() =>
    Boolean(desde.value && hasta.value && desde.value > hasta.value)
  )

  function params() {
    const p = {}
    if (config.mrad) p.mrad = mrad.value
    if (conVariante) p.segundo = segundo.value
    if (desde.value) p.desde = desde.value
    if (hasta.value) p.hasta = hasta.value
    if (conSucursal && sucursal.value) p.sucursal = sucursal.value
    if (estado.value) p.estado = estado.value
    for (const f of config.filtros || []) {
      const v = extra.value[f.key]
      if (v !== undefined && v !== null && v !== '') p[f.param || f.key] = v
    }
    return p
  }

  async function buscar() {
    if (rangoInvalido.value) return
    if (controller) controller.abort()
    controller = new AbortController()
    const signal = controller.signal

    cargando.value = true
    error.value = ''
    try {
      const { data } = await api.get(config.endpoint, { params: params(), signal })
      filas.value = config.extract ? config.extract(data, mrad.value) : Array.isArray(data) ? data : []
      meta.value = config.meta ? config.meta(data) : {}
      buscado.value = true
    } catch (e) {
      if (e.code === 'ERR_CANCELED' || e.name === 'CanceledError' || e.name === 'AbortError') return
      filas.value = []
      buscado.value = true
      error.value =
        e.response?.data?.detail ||
        'No se pudieron cargar los datos. Revisá la conexión con el servidor.'
    } finally {
      if (!signal.aborted) cargando.value = false
    }
  }

  function limpiar() {
    sucursal.value = ''
    extra.value = {}
    if (config.mrad) mrad.value = config.mradInicial ?? 1
    if (conVariante) segundo.value = config.segundoInicial ?? 1
    const [d, h] = rangoPorDefecto()
    desde.value = mrad.value === 1 ? d.slice(0, 7) : d
    hasta.value = mrad.value === 1 ? h.slice(0, 7) : h
    limpiarResultados()
  }

  onBeforeUnmount(() => {
    if (controller) controller.abort()
  })

  const columnas = computed(() => {
    if (typeof config.columnas !== 'function') return config.columnas || []
    return config.columnas(mrad.value, conVariante ? segundo.value : undefined)
  })

  const kpis = computed(() => (config.kpis ? config.kpis(filas.value) : []))

  const graficos = computed(() => {
    if (!filas.value.length) return []
    const lista = config.graficos ? config.graficos(filas.value, ctx()) : []
    return lista.filter(Boolean)
  })

  function ctx() {
    return {
      mrad: mrad.value,
      segundo: segundo.value,
      granularidad: granularidad.value,
      desde: desde.value,
      hasta: hasta.value,
      titulo: config.titulo,
      subtitulo: etiquetaRango(desde.value, hasta.value, granularidad.value),
      meta: meta.value
    }
  }

  const hayDatos = computed(() => filas.value.length > 0)

  return {
    mrad,
    segundo,
    desde,
    hasta,
    sucursal,
    extra,
    filas,
    meta,
    cargando,
    error,
    buscado,
    esPeriodo,
    tipoFecha,
    granularidad,
    rangoInvalido,
    columnas,
    kpis,
    graficos,
    hayDatos,
    buscar,
    limpiar,
    cambiarModo,
    cambiarSegundo
  }
}

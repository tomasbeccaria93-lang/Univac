import { ref, readonly } from 'vue'
import api from '../api'
import { useEstadoDatos } from './useEstadoDatos'

const cache = ref([])
const cargando = ref(false)
let promesa = null
let intentado = false
let firma = null

const { estado } = useEstadoDatos()

function firmaActual() {
  let empresa
  try {
    empresa = localStorage.getItem('empresa_id') || ''
  } catch {
    empresa = ''
  }
  return `${empresa}|${estado.value}`
}

export function useSucursales() {
  async function cargar() {
    const actual = firmaActual()
    if (firma !== null && firma !== actual) {
      cache.value = []
      intentado = false
      promesa = null
    }
    firma = actual
    if (intentado) return
    if (promesa) return promesa
    cargando.value = true
    promesa = api
      .get('/reportes/sucursales', { params: estado.value ? { estado: estado.value } : {} })
      .then(({ data }) => {
        cache.value = Array.isArray(data) ? data : []
      })
      .catch(() => {
        cache.value = []
      })
      .finally(() => {
        cargando.value = false
        intentado = true
        promesa = null
      })
    return promesa
  }

  return { sucursales: readonly(cache), cargandoSucursales: readonly(cargando), cargar }
}

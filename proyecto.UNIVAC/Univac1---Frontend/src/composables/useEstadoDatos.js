import { ref } from 'vue'

const CLAVE = 'estado_datos'

const estado = ref(0)

try {
  const guardado = parseInt(localStorage.getItem(CLAVE), 10)
  if (guardado === 1) estado.value = 1
} catch {
  estado.value = 0
}

export function useEstadoDatos() {
  const setEstado = (valor) => {
    const nuevo = Number(valor) === 1 ? 1 : 0
    if (nuevo === estado.value) return
    estado.value = nuevo
    try {
      localStorage.setItem(CLAVE, String(nuevo))
    } catch {
    }
  }

  return { estado, setEstado }
}

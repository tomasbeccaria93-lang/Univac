<template>
  <div class="menu-informes">
    <ul class="submenu">
      <li v-for="g in grupos" :key="g.key" class="sub-grupo">
        <button
          class="sub-group-btn"
          :class="{ open: openGroups[g.key] }"
          @click="toggleGrupo(g.key)"
        >
          <i :class="'fas ' + g.icon" />
          <span class="g-label">{{ g.label }}</span>
          <svg class="g-arrow" viewBox="0 0 20 20" fill="currentColor" width="12" height="12">
            <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
          </svg>
        </button>
        <div
          class="sub-grupo-body"
          :ref="(el) => setBody(g.key, el)"
          :style="{ maxHeight: openGroups[g.key] ? alturaGrupo(g) : '0' }"
        >
          <ul>
            <li v-for="sub in g.items" :key="sub.to">
              <router-link :to="sub.to" class="sub-link sub2" :class="{ 'sub-link-activo': esActivo(sub.to) }">
                <i :class="'fas ' + sub.icon" />
                <span>{{ sub.label }}</span>
              </router-link>
            </li>
          </ul>
        </div>
      </li>
    </ul>

    <div v-if="mostrarNoOriginal" class="sub-sep" />
    <p v-if="mostrarNoOriginal" class="no-original-title">Otros informes</p>
    <ul v-if="mostrarNoOriginal" class="submenu">
      <li v-for="it in itemsNoOriginal" :key="it.to">
        <router-link :to="it.to" class="sub-link" :class="{ 'sub-link-activo': esActivo(it.to) }">
          <i :class="'fas ' + it.icon" />
          <span>{{ it.label }}</span>
        </router-link>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { grupos, itemsNoOriginal, prefijoRuta } from '../data/menuInformes'

const route = useRoute()

const openGroups = reactive({})
for (const g of grupos) openGroups[g.key] = false

const mostrarNoOriginal = import.meta.env.VITE_SHOW_NO_ORIGINAL === 'true'

watch(
  () => route.path,
  (p) => {
    for (const g of grupos) {
      if (g.items.some((it) => prefijoRuta(it.to) === p)) openGroups[g.key] = true
    }
  },
  { immediate: true }
)

function esActivo(to) {
  const [path, query] = String(to).split('?')
  if (path !== route.path) return false
  if (!query) return true
  const pedido = new URLSearchParams(query).get('segundo')
  if (!pedido) return true
  return pedido === String(route.query.segundo ?? '1')
}

const cuerpos = ref({})

function setBody(key, el) {
  if (el) cuerpos.value[key] = el
  else delete cuerpos.value[key]
}

function alturaGrupo(g) {
  const el = cuerpos.value[g.key]
  const medida = el ? el.scrollHeight : 0
  if (medida > 0) return `${medida}px`
  return `${g.items.length * 80 + 16}px`
}

function toggleGrupo(key) {
  openGroups[key] = !openGroups[key]
}
</script>

<style scoped>
.menu-informes {
  display: flex;
  flex-direction: column;
}

.submenu {
  list-style: none;
  padding: 4px 0 0 0;
  margin: 0;
}

.sub-link {
  display: flex;
  align-items: center;
  padding: 10px 14px 10px 48px;
  color: var(--brand-ink);
  text-decoration: none;
  font-size: 13px;
  border-radius: var(--r-md);
  margin: 1px 8px;
  transition: background 0.2s ease, color 0.2s ease;
  font-weight: 500;
  line-height: 1.35;
}
.sub-link:hover {
  background: var(--brand-mid);
  color: white;
}
.sub-link.sub-link-activo {
  background: rgba(44, 97, 120, 0.32);
  color: white;
}
.sub-link i {
  width: 18px;
  text-align: center;
  margin-right: 10px;
  font-size: 12px;
  opacity: 0.7;
  flex-shrink: 0;
}
.sub-link span {
  min-width: 0;
}

.sub-sep {
  height: 1px;
  background: rgba(255, 255, 255, 0.07);
  margin: 8px 14px;
  list-style: none;
}

.sub-grupo {
  margin: 1px 8px;
  list-style: none;
}
.sub-group-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 12px 10px 18px;
  border: none;
  border-radius: var(--r-md);
  background: transparent;
  color: var(--brand-ink);
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease;
  text-align: left;
  line-height: 1.35;
}
.sub-group-btn:hover,
.sub-group-btn.open {
  background: rgba(44, 97, 120, 0.3);
  color: white;
}
.sub-group-btn i {
  width: 18px;
  text-align: center;
  font-size: 12px;
  opacity: 0.7;
  flex-shrink: 0;
}
.sub-group-btn .g-label {
  flex: 1;
  min-width: 0;
}
.g-arrow {
  flex-shrink: 0;
  transition: transform 0.25s ease;
  opacity: 0.5;
}
.sub-group-btn.open .g-arrow {
  transform: rotate(180deg);
  opacity: 0.8;
}

.sub-grupo-body {
  overflow: hidden;
  transition: max-height 0.25s ease;
}
.sub-grupo-body ul {
  list-style: none;
  margin: 0;
  padding: 0;
}
.sub-link.sub2 {
  padding-left: 64px;
  font-size: 12.5px;
}

.no-original-title {
  padding: 2px 0 2px 26px;
  margin: 0 0 2px;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--brand-ink);
  opacity: 0.55;
}
</style>

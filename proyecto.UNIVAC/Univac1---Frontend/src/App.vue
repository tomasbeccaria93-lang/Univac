<template>
  <router-view v-slot="{ Component }">
    <transition name="pagina" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>

<script setup>
</script>

<style>
.pagina-enter-active {
  transition: opacity 0.18s ease;
}
.pagina-leave-active {
  transition: opacity 0.12s ease;
}
.pagina-enter-from {
  opacity: 0;
}
.pagina-leave-to {
  opacity: 0;
}
</style>

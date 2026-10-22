<template>
  <InformeView :config="informe" />
</template>

<script setup>
import InformeView from '../../components/InformeView.vue'
import { config } from '../../data/informes'

const informe = config('compras-acumuladas')
</script>


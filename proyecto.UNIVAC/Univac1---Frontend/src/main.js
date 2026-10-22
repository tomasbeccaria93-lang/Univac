import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import {
  Chart as ChartJS,
  BarController,
  LineController,
  DoughnutController,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  CategoryScale,
  LinearScale,
  Filler,
  Legend,
  Tooltip
} from 'chart.js'
import { valueLabelsPlugin } from './plugins/valueLabelsPlugin'

import '@fortawesome/fontawesome-free/css/all.min.css'
import '@fontsource/ibm-plex-sans/latin-ext-400.css'
import '@fontsource/ibm-plex-sans/latin-ext-500.css'
import '@fontsource/ibm-plex-sans/latin-ext-600.css'
import '@fontsource/ibm-plex-sans/latin-ext-700.css'
import '@fontsource/ibm-plex-sans/latin-400.css'
import '@fontsource/ibm-plex-sans/latin-500.css'
import '@fontsource/ibm-plex-sans/latin-600.css'
import '@fontsource/ibm-plex-sans/latin-700.css'
import './assets/main.css'

ChartJS.register(
  BarController,
  LineController,
  DoughnutController,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  CategoryScale,
  LinearScale,
  Filler,
  Legend,
  Tooltip,
  valueLabelsPlugin
)

const tokens = getComputedStyle(document.documentElement)
const readVar = (n) => tokens.getPropertyValue(n).trim()

ChartJS.defaults.font.family = "'IBM Plex Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
ChartJS.defaults.font.size = 11
ChartJS.defaults.color = readVar('--g-400')
ChartJS.defaults.borderColor = readVar('--g-200')
ChartJS.defaults.animation.duration = 260
ChartJS.defaults.animation.easing = 'easeOutCubic'
ChartJS.defaults.plugins.tooltip.backgroundColor = readVar('--brand-strong')
ChartJS.defaults.plugins.tooltip.titleColor = '#FFFFFF'
ChartJS.defaults.plugins.tooltip.bodyColor = '#D8E2E8'
ChartJS.defaults.plugins.tooltip.cornerRadius = 6
ChartJS.defaults.plugins.tooltip.padding = 10
ChartJS.defaults.plugins.tooltip.boxPadding = 4
ChartJS.defaults.plugins.tooltip.titleFont = { weight: 600, size: 11 }
ChartJS.defaults.plugins.tooltip.bodyFont = { weight: 500, size: 12 }
ChartJS.defaults.plugins.tooltip.displayColors = true
ChartJS.defaults.plugins.tooltip.boxWidth = 8
ChartJS.defaults.plugins.tooltip.boxHeight = 8
ChartJS.defaults.plugins.tooltip.boxBorderRadius = 2
ChartJS.defaults.plugins.tooltip.caretSize = 5

const app = createApp(App)
app.use(router)
app.mount('#app')

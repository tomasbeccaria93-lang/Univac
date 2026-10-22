export const valueLabelsPlugin = {
  id: 'excelValueLabels',
  afterDatasetsDraw(chart) {
    const cfg = (chart.config && chart.config.options && chart.config.options.plugins && chart.config.options.plugins.excelValueLabels) || {}
    if (cfg.enabled === false) return

    const area = chart.chartArea
    if (!area) return

    const ctx = chart.ctx
    const formatter = cfg.formatter
    const color = cfg.color || '#475569'
    const colorInside = cfg.colorInside || '#FFFFFF'
    const font = cfg.font || '600 10px IBM Plex Sans, sans-serif'
    const gap = cfg.minGap != null ? cfg.minGap : 8
    const horizontal = cfg.orientacion === 'h' || chart.options.indexAxis === 'y'

    ctx.save()
    ctx.font = font
    ctx.textBaseline = 'middle'

    const px = parseInt((font.match(/(\d+(?:\.\d+)?)px/) || [0, 11])[1], 10) || 11

    const numOk = (v) => v != null && v !== '' && !isNaN(v) && Number(v) !== 0
    const texto = (v) => (formatter ? formatter(v) : String(v))

    chart.data.datasets.forEach((ds, i) => {
      if (ds.type === 'line' || ds.hidden) return
      const meta = chart.getDatasetMeta(i)
      if (!meta || meta.hidden) return

      const vals = ds.data || []
      const bars = meta.data || []
      const total = Math.min(vals.length, bars.length)
      if (!total) return

      let hayValores = false
      let ancho = 0
      let alto = px
      for (let j = 0; j < total; j++) {
        if (!numOk(vals[j])) continue
        hayValores = true
        const t = texto(vals[j])
        const w = ctx.measureText(t).width
        if (w > ancho) ancho = w
      }
      if (!hayValores) return

      const pos = horizontal
        ? (k) => bars[k].y
        : (k) => bars[k].x
      let paso = Infinity
      for (let j = 1; j < total; j++) {
        const d = Math.abs(pos(j) - pos(j - 1))
        if (d < paso) paso = d
      }
      if (!isFinite(paso) || paso <= 0) {
        paso = horizontal
          ? (area.bottom - area.top) / total
          : (area.right - area.left) / total
      }

      const cupo = Math.floor(paso / (horizontal ? alto + gap * 0.6 : ancho + gap))
      if (cupo < 1) return

      let idx = []
      if (cupo === 1) {
        let imax = -1
        let maxAbs = -Infinity
        for (let j = 0; j < total; j++) {
          if (!numOk(vals[j])) continue
          const v = Math.abs(Number(vals[j]))
          if (v > maxAbs) { maxAbs = v; imax = j }
        }
        if (imax === -1) return
        idx = [imax]
      } else {
        const maxLabels = Math.min(cfg.maxLabels || 16, cupo)
        const stride = Math.max(1, Math.ceil(total / maxLabels))
        for (let j = 0; j < total; j += stride) idx.push(j)
        if (idx[idx.length - 1] !== total - 1) {
          if (idx.length >= maxLabels) idx.pop()
          idx.push(total - 1)
        }
      }

      idx.forEach((j) => {
        const v = vals[j]
        if (!numOk(v)) return
        const t = texto(v)
        const bar = bars[j]
        const w = ctx.measureText(t).width

        if (horizontal) {
          let y = bar.y
          if (y < area.top + alto / 2) y = area.top + alto / 2
          if (y > area.bottom - alto / 2) y = area.bottom - alto / 2
          const dentro = bar.x + w / 2 + 6 > area.right
          ctx.textAlign = dentro ? 'right' : 'left'
          ctx.fillStyle = dentro ? colorInside : color
          ctx.fillText(t, dentro ? bar.x - 5 : bar.x + 5, y)
        } else {
          const half = w / 2 + 1
          let x = bar.x
          if (x < area.left + half) x = area.left + half
          if (x > area.right - half) x = area.right - half
          const offsetY = cfg.offsetY != null ? cfg.offsetY : 5
          let y = bar.y - offsetY
          const dentro = y < area.top + px * 0.9
          if (dentro) y = bar.y + px * 0.7
          if (y > area.bottom + px * 0.5 || y < area.top) return
          ctx.textAlign = 'center'
          ctx.fillStyle = dentro ? colorInside : color
          ctx.fillText(t, x, y)
        }
      })
    })

    ctx.restore()
  }
}
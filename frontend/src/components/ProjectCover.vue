<script setup lang="ts">
import { onMounted, ref } from 'vue'
const props = defineProps<{ variant: number }>()
const canvas = ref<HTMLCanvasElement | null>(null)
onMounted(() => {
  const ctx = canvas.value?.getContext('2d')
  if (!ctx) return
  const w = 960
  const h = 720
  ctx.fillStyle = ['#e6dfd0', '#d9d5c9', '#ddd4c2', '#e3dccc'][props.variant % 4]!
  ctx.fillRect(0, 0, w, h)
  ctx.strokeStyle = '#c6bba6'
  ctx.lineWidth = 1
  for (let x = 0; x < w; x += 60) {
    ctx.beginPath()
    ctx.moveTo(x, 0)
    ctx.lineTo(x, h)
    ctx.stroke()
  }
  for (let y = 0; y < h; y += 60) {
    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(w, y)
    ctx.stroke()
  }
  if (props.variant % 4 === 0) {
    // Topographic route study, not a product screenshot or measured data.
    for (let level = 0; level < 18; level++) {
      ctx.beginPath()
      for (let step = 0; step <= 180; step++) {
        const a = (step / 180) * Math.PI * 2
        const radius = 45 + level * 20 + Math.sin(a * 3 + level * 0.12) * (12 + level * 1.5)
        const x = 490 + Math.cos(a) * radius * 1.15
        const y = 360 + Math.sin(a) * radius * 0.7
        if (!step) ctx.moveTo(x, y)
        else ctx.lineTo(x, y)
      }
      ctx.closePath()
      ctx.strokeStyle = level % 4 === 0 ? '#8f8065' : '#b2a48a'
      ctx.stroke()
    }
    ctx.beginPath()
    ctx.moveTo(120, 590)
    ctx.bezierCurveTo(270, 420, 470, 530, 510, 350)
    ctx.bezierCurveTo(535, 230, 750, 310, 810, 170)
    ctx.strokeStyle = '#aa4825'
    ctx.lineWidth = 4
    ctx.stroke()
    for (const [x, y] of [
      [120, 590],
      [510, 350],
      [810, 170],
    ]) {
      ctx.beginPath()
      ctx.arc(x!, y!, 8, 0, Math.PI * 2)
      ctx.fillStyle = '#aa4825'
      ctx.fill()
    }
  } else if (props.variant % 4 === 1) {
    // A knowledge graph, with no invented metrics or conversations.
    const nodes = [
      [480, 360],
      [240, 200],
      [700, 170],
      [780, 480],
      [250, 540],
      [440, 130],
      [550, 590],
      [140, 340],
    ]
    ctx.strokeStyle = '#9a8f79'
    ctx.lineWidth = 1.5
    for (let i = 1; i < nodes.length; i++) {
      ctx.beginPath()
      ctx.moveTo(480, 360)
      ctx.lineTo(nodes[i]![0]!, nodes[i]![1]!)
      ctx.stroke()
    }
    nodes.forEach(([x, y], i) => {
      ctx.beginPath()
      ctx.arc(x!, y!, i === 0 ? 72 : 25 + (i % 3) * 9, 0, Math.PI * 2)
      ctx.fillStyle = i === 0 ? '#aa4825' : '#eee9dd'
      ctx.fill()
      ctx.stroke()
      if (i) {
        ctx.beginPath()
        ctx.arc(x!, y!, 4, 0, Math.PI * 2)
        ctx.fillStyle = '#8e7c60'
        ctx.fill()
      }
    })
    ctx.strokeStyle = '#f4efe6'
    ctx.lineWidth = 3
    for (let i = 0; i < 3; i++) {
      ctx.beginPath()
      ctx.moveTo(455, 342 + i * 18)
      ctx.lineTo(505 - i * 8, 342 + i * 18)
      ctx.stroke()
    }
  } else if (props.variant % 4 === 2) {
    // Three registered spatial layers, drawn in an isometric projection.
    const project = (x: number, z: number, y: number) => [
      480 + (x - z) * 54,
      240 + (x + z) * 25 + y,
    ]
    for (let layer = 2; layer >= 0; layer--) {
      const corners = [
        [-3, -3],
        [3, -3],
        [3, 3],
        [-3, 3],
      ]
      ctx.beginPath()
      corners.forEach(([x, z], i) => {
        const [px, py] = project(x!, z!, layer * 90)
        if (!i) ctx.moveTo(px!, py!)
        else ctx.lineTo(px!, py!)
      })
      ctx.closePath()
      ctx.fillStyle = ['#eee9dd', '#bd6948', '#c3baa4'][layer]!
      ctx.fill()
      ctx.strokeStyle = '#8e8067'
      ctx.lineWidth = 1.5
      ctx.stroke()
      for (let line = -2; line <= 2; line++) {
        const [ax, ay] = project(line, -3, layer * 90)
        const [bx, by] = project(line, 3, layer * 90)
        ctx.beginPath()
        ctx.moveTo(ax!, ay!)
        ctx.lineTo(bx!, by!)
        ctx.strokeStyle = '#a99a7f'
        ctx.lineWidth = 0.7
        ctx.stroke()
        const [cx, cy] = project(-3, line, layer * 90)
        const [dx, dy] = project(3, line, layer * 90)
        ctx.beginPath()
        ctx.moveTo(cx!, cy!)
        ctx.lineTo(dx!, dy!)
        ctx.stroke()
      }
    }
  } else {
    ctx.save()
    ctx.translate(480, 360)
    ctx.rotate(-0.24)
    ctx.translate(-480, -360)
    for (let row = -1; row < 7; row++)
      for (let col = -1; col < 8; col++) {
        const x = col * 160
        const y = row * 140
        ctx.fillStyle = (row + col) % 4 === 0 ? '#c78b6d' : '#cfc4ae'
        ctx.fillRect(x + 12, y + 12, 130, 110)
        ctx.strokeStyle = '#a99a7e'
        ctx.strokeRect(x + 12, y + 12, 130, 110)
        ctx.fillStyle = '#eae3d5'
        ctx.fillRect(x + 30, y + 32, 65, 55)
      }
    ctx.fillStyle = '#aa4825'
    ctx.fillRect(332, 292, 130, 110)
    ctx.fillStyle = '#f4efe6'
    ctx.fillRect(357, 317, 70, 60)
    ctx.restore()
  }
})
</script>
<template>
  <canvas ref="canvas" width="960" height="720" class="project-cover" aria-hidden="true" />
</template>
<style scoped>
.project-cover {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
</style>

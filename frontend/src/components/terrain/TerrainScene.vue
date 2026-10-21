<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import * as THREE from 'three'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { createTerrain } from './terrain'
const host = ref<HTMLElement | null>(null)
const failed = ref(false)
let cleanup = () => {}
onMounted(() => {
  if (!host.value) return
  let renderer: THREE.WebGLRenderer
  try {
    renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: 'low-power',
    })
  } catch {
    failed.value = true
    return
  }
  gsap.registerPlugin(ScrollTrigger)
  const scene = new THREE.Scene()
  const camera = new THREE.OrthographicCamera(-5, 5, 5, -5, 0.1, 60)
  camera.position.set(8, 7.5, 10)
  camera.lookAt(0, 0.2, 0)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75))
  renderer.setClearColor(0x000000, 0)
  host.value.appendChild(renderer.domElement)
  const { group, layers, grid } = createTerrain()
  scene.add(group)
  scene.add(new THREE.HemisphereLight('#fffdf5', '#8e8066', 2.8))
  const light = new THREE.DirectionalLight('#fffaf0', 3)
  light.position.set(-4, 9, 6)
  scene.add(light)
  group.rotation.y = -0.14
  const render = () => renderer.render(scene, camera)
  const resize = () => {
    if (!host.value) return
    const { width, height } = host.value.getBoundingClientRect()
    const aspect = width / Math.max(height, 1)
    const halfHeight = Math.max(3.9, 4.3 / aspect)
    camera.left = -halfHeight * aspect
    camera.right = halfHeight * aspect
    camera.top = halfHeight
    camera.bottom = -halfHeight
    camera.updateProjectionMatrix()
    renderer.setSize(width, height)
    render()
  }
  const observer = new ResizeObserver(resize)
  observer.observe(host.value)
  resize()
  const media = gsap.matchMedia()
  media.add('(prefers-reduced-motion: no-preference)', () => {
    const animation = gsap.timeline({
      scrollTrigger: {
        trigger: host.value!.closest('#home'),
        start: 'top top',
        end: 'bottom top',
        scrub: 0.65,
      },
      onUpdate: render,
    })
    animation
      .to(group.rotation, { y: 0.48, x: 0.08, ease: 'none' }, 0)
      .to(group.position, { y: 0.35, x: 0.25, ease: 'none' }, 0)
    layers.forEach((layer, i) =>
      animation.to(layer.position, { y: -0.55 - i * 0.55, ease: 'none' }, 0),
    )
    animation.to(grid.position, { y: -2.1, ease: 'none' }, 0)
  })
  const onContextLost = (event: Event) => {
    event.preventDefault()
    failed.value = true
  }
  renderer.domElement.addEventListener('webglcontextlost', onContextLost)
  cleanup = () => {
    media.revert()
    observer.disconnect()
    renderer.domElement.removeEventListener('webglcontextlost', onContextLost)
    scene.traverse((object) => {
      const mesh = object as THREE.Mesh
      mesh.geometry?.dispose()
      if (Array.isArray(mesh.material)) mesh.material.forEach((m) => m.dispose())
      else mesh.material?.dispose()
    })
    renderer.dispose()
    renderer.domElement.remove()
  }
})
onBeforeUnmount(() => cleanup())
</script>
<template>
  <div
    class="terrain-scene"
    role="img"
    aria-label="An abstract 3D terrain model with contour lines and three data layers. The layers separate and the model rotates as you scroll."
  >
    <div v-show="!failed" ref="host" class="absolute inset-0" />
    <div v-if="failed" class="terrain-fallback" aria-hidden="true">
      <div
        v-for="n in 9"
        :key="n"
        :style="{ inset: `${n * 3}%`, transform: `translateY(${-n * 5}px)` }"
      />
    </div>
    <span class="terrain-cross terrain-cross-a" aria-hidden="true">+</span
    ><span class="terrain-cross terrain-cross-b" aria-hidden="true">+</span>
  </div>
</template>
<style scoped>
.terrain-scene {
  position: relative;
  width: 100%;
  height: 100%;
}
.terrain-cross {
  position: absolute;
  font: 20px var(--font-mono);
  color: #a2957f;
}
.terrain-cross-a {
  top: 12%;
  left: 10%;
}
.terrain-cross-b {
  bottom: 12%;
  right: 8%;
}
.terrain-fallback {
  position: absolute;
  inset: 20% 12%;
  transform: rotateX(45deg) rotateZ(-25deg);
  transform-style: preserve-3d;
}
.terrain-fallback div {
  position: absolute;
  border: 1px solid #97876b;
  border-radius: 43% 57% 55% 45%;
  background: #e8dfcf;
}
</style>

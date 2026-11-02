<script setup lang="ts">
import { ref } from 'vue'

defineOptions({ name: 'LogoMark' })

withDefaults(defineProps<{ size?: number }>(), { size: 44 })

/**
 * Owner note: this tile reads /logo.svg from the public folder.
 * Replace public/logo.svg with the official Thimi Tech logo — no component
 * change is needed. The monogram below is only a graceful fallback.
 */
const failed = ref(false)
// Bound rather than literal so Vite leaves the public asset path untouched in tests.
const logoSrc = '/logo.svg'
</script>

<template>
  <span class="logo-mark" :style="{ '--logo-size': `${size}px` }">
    <img
      v-if="!failed"
      :src="logoSrc"
      alt="Thimi Tech"
      class="logo-mark__image"
      width="32"
      height="32"
      @error="failed = true"
    />
    <span v-else class="logo-mark__fallback" aria-hidden="true">TT</span>
    <span class="logo-mark__corner" aria-hidden="true"></span>
  </span>
</template>

<style scoped>
.logo-mark {
  position: relative;
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  width: var(--logo-size);
  height: var(--logo-size);
  overflow: hidden;
  border: 1px solid rgb(10 10 10 / 0.16);
  border-radius: 4px;
  background:
    radial-gradient(circle at 30% 20%, rgb(255 255 255 / 0.95), transparent 62%),
    #f1f2f4;
  box-shadow:
    inset 0 0 0 1px rgb(255 255 255 / 0.6),
    0 1px 0 rgb(10 10 10 / 0.12);
}

.logo-mark__image {
  display: block;
  width: 58%;
  height: 58%;
  object-fit: contain;
}

.logo-mark__fallback {
  font-family: var(--font-display, 'Outfit Variable', sans-serif);
  font-size: calc(var(--logo-size) * 0.42);
  font-weight: 600;
  line-height: 1;
  letter-spacing: -0.09em;
  color: #0a0a0a;
  transform: translateX(-0.04em);
}

.logo-mark__corner {
  position: absolute;
  right: 4px;
  bottom: 4px;
  width: 5px;
  height: 5px;
  border-right: 1px solid rgb(10 10 10 / 0.45);
  border-bottom: 1px solid rgb(10 10 10 / 0.45);
}
</style>

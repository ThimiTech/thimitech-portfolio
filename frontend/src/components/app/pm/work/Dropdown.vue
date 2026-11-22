<script setup lang="ts">
/** A trigger plus a floating menu. The menu is teleported and fixed-positioned so scrolling board columns and
 *  clipped panels never cut it off. Closes on Escape, outside click, scroll and resize. */
import { nextTick, onBeforeUnmount, ref } from 'vue'
defineOptions({ name: 'WorkDropdown' })
const props = withDefaults(defineProps<{ disabled?: boolean; label: string; width?: number; align?: 'left' | 'right' }>(), {
  width: 224,
  align: 'left',
})
const open = ref(false)
const trigger = ref<HTMLElement | null>(null)
const menu = ref<HTMLElement | null>(null)
const pos = ref({ top: 0, left: 0, maxHeight: 320 })

function place() {
  const r = trigger.value!.getBoundingClientRect()
  const below = window.innerHeight - r.bottom - 8
  const above = r.top - 8
  const up = below < 220 && above > below
  const left = props.align === 'right' ? r.right - props.width : r.left
  pos.value = {
    top: up ? Math.max(8, r.top - Math.min(above, 360) - 4) : r.bottom + 4,
    left: Math.max(8, Math.min(left, window.innerWidth - props.width - 8)),
    maxHeight: Math.min(up ? above : below, 360),
  }
}
async function show() {
  if (props.disabled) return
  place()
  open.value = true
  document.addEventListener('pointerdown', outside, true)
  window.addEventListener('scroll', hideOnScroll, true)
  window.addEventListener('resize', hide)
  await nextTick()
  menu.value?.querySelector<HTMLElement>('input, [role="menuitem"], [role="option"], button')?.focus()
}
function hide() {
  if (!open.value) return
  open.value = false
  document.removeEventListener('pointerdown', outside, true)
  window.removeEventListener('scroll', hideOnScroll, true)
  window.removeEventListener('resize', hide)
}
function close(refocus = true) {
  hide()
  if (refocus) trigger.value?.querySelector<HTMLElement>('button')?.focus()
}
function outside(e: Event) {
  const t = e.target as Node
  if (!menu.value?.contains(t) && !trigger.value?.contains(t)) hide()
}
function hideOnScroll(e: Event) {
  if (!menu.value?.contains(e.target as Node)) hide()
}
function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    e.stopPropagation()
    close()
  }
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    const items = [...(menu.value?.querySelectorAll<HTMLElement>('[role="menuitem"], [role="option"]') || [])]
    const i = items.indexOf(document.activeElement as HTMLElement)
    items[(i + (e.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length]?.focus()
    e.preventDefault()
  }
}
onBeforeUnmount(hide)
defineExpose({ close })
</script>
<template>
  <span ref="trigger" class="inline-flex max-w-full min-w-0" @click.stop>
    <slot name="trigger" :open="open" :toggle="() => (open ? close() : show())" :disabled="disabled" />
    <Teleport to="body">
      <div
        v-if="open"
        ref="menu"
        class="fixed z-[10001] overflow-y-auto rounded-lg border border-ink/15 bg-sheet py-1 text-sm shadow-xl"
        :style="{ top: `${pos.top}px`, left: `${pos.left}px`, width: `${width}px`, maxHeight: `${pos.maxHeight}px` }"
        role="menu"
        :aria-label="label"
        @keydown="onKey"
        @click.stop
      >
        <slot :close="close" />
      </div>
    </Teleport>
  </span>
</template>

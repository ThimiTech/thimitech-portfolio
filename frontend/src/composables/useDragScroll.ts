import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { Ref } from 'vue'

export interface DragScrollApi {
  scrollRef: Ref<HTMLElement | null>
  isDragging: Ref<boolean>
  canScrollPrev: Ref<boolean>
  canScrollNext: Ref<boolean>
  progress: Ref<number>
  activeIndex: Ref<number>
  scrollPrev: () => void
  scrollNext: () => void
}

const DRAG_THRESHOLD_PX = 6
const EDGE_EPSILON_PX = 2
const FALLBACK_STEP_RATIO = 0.8
const NO_DRAG_SELECTOR = 'a, button, input, select, textarea, [data-no-drag]'
const CARD_SELECTOR = '[data-project-card]'
const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)'

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max)
}

function resolveBehavior(): ScrollBehavior {
  const reduced =
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia(REDUCED_MOTION_QUERY).matches
  return reduced ? 'auto' : 'smooth'
}

function resolveCards(el: HTMLElement): HTMLElement[] {
  const marked = Array.from(el.querySelectorAll<HTMLElement>(CARD_SELECTOR))
  if (marked.length > 0) return marked
  const children: HTMLElement[] = []
  for (const child of el.children) {
    if (child instanceof HTMLElement) children.push(child)
  }
  return children
}

function relativeLeft(el: HTMLElement, node: HTMLElement): number {
  if (node.offsetParent === el) return node.offsetLeft
  return node.offsetLeft - el.offsetLeft - el.clientLeft
}

function nearestIndex(el: HTMLElement, cards: HTMLElement[]): number {
  let nearest = 0
  let smallest = Number.POSITIVE_INFINITY
  for (const [index, card] of cards.entries()) {
    const distance = Math.abs(relativeLeft(el, card) - el.scrollLeft)
    if (distance < smallest) {
      smallest = distance
      nearest = index
    }
  }
  return nearest
}

function measureStep(el: HTMLElement, cards: HTMLElement[]): number {
  const first = cards[0]
  const second = cards[1]
  if (first && second) {
    const step = second.offsetLeft - first.offsetLeft
    if (step > 0) return step
  }
  return el.clientWidth * FALLBACK_STEP_RATIO
}

function computeProgress(el: HTMLElement): number {
  const range = el.scrollWidth - el.clientWidth
  if (range <= 0) return 0
  return clamp(el.scrollLeft / range, 0, 1)
}

export function useDragScroll(): DragScrollApi {
  const scrollRef = ref<HTMLElement | null>(null)
  const isDragging = ref(false)
  const canScrollPrev = ref(false)
  const canScrollNext = ref(false)
  const progress = ref(0)
  const activeIndex = ref(0)

  let boundEl: HTMLElement | null = null
  let observer: ResizeObserver | null = null
  let frameId: number | null = null
  let pointerId: number | null = null
  let startX = 0
  let startScrollLeft = 0
  let dragActive = false
  let savedSnapType = ''
  let savedUserSelect = ''

  function recompute(): void {
    const el = boundEl
    if (!el) return
    const range = el.scrollWidth - el.clientWidth
    progress.value = computeProgress(el)
    canScrollPrev.value = el.scrollLeft > EDGE_EPSILON_PX
    canScrollNext.value = el.scrollLeft < range - EDGE_EPSILON_PX
    const cards = resolveCards(el)
    activeIndex.value = cards.length > 0 ? nearestIndex(el, cards) : 0
  }

  function schedule(): void {
    if (frameId !== null) return
    frameId = requestAnimationFrame(() => {
      frameId = null
      recompute()
    })
  }

  function cancelFrame(): void {
    if (frameId === null) return
    cancelAnimationFrame(frameId)
    frameId = null
  }

  function scrollToIndex(el: HTMLElement, index: number, cards: HTMLElement[]): void {
    const card = cards[index]
    if (!card) return
    el.scrollTo({ left: relativeLeft(el, card), behavior: resolveBehavior() })
  }

  function snapToNearest(el: HTMLElement): void {
    const cards = resolveCards(el)
    if (cards.length === 0) return
    scrollToIndex(el, nearestIndex(el, cards), cards)
  }

  function scrollByCard(direction: number): void {
    const el = boundEl
    if (!el) return
    const cards = resolveCards(el)
    if (cards.length >= 2) {
      const index = clamp(nearestIndex(el, cards) + direction, 0, cards.length - 1)
      scrollToIndex(el, index, cards)
      return
    }
    const step = measureStep(el, cards) * direction
    el.scrollTo({ left: el.scrollLeft + step, behavior: resolveBehavior() })
  }

  function scrollPrev(): void {
    scrollByCard(-1)
  }

  function scrollNext(): void {
    scrollByCard(1)
  }

  function restoreDragStyles(el: HTMLElement): void {
    el.style.scrollSnapType = savedSnapType
    el.style.userSelect = savedUserSelect
  }

  function resetPointer(): void {
    const el = boundEl
    if (el && pointerId !== null && el.hasPointerCapture(pointerId)) {
      el.releasePointerCapture(pointerId)
    }
    pointerId = null
    dragActive = false
    isDragging.value = false
  }

  function endDrag(): void {
    const el = boundEl
    const wasDragging = dragActive
    resetPointer()
    if (!el || !wasDragging) return
    restoreDragStyles(el)
    snapToNearest(el)
    schedule()
  }

  function beginDrag(el: HTMLElement, event: PointerEvent): void {
    dragActive = true
    isDragging.value = true
    savedSnapType = el.style.scrollSnapType
    savedUserSelect = el.style.userSelect
    el.style.scrollSnapType = 'none'
    el.style.userSelect = 'none'
    el.setPointerCapture(event.pointerId)
  }

  function onPointerDown(event: PointerEvent): void {
    const el = boundEl
    if (!el || event.pointerType !== 'mouse' || event.button !== 0) return
    const target = event.target
    if (target instanceof Element && target.closest(NO_DRAG_SELECTOR)) return
    pointerId = event.pointerId
    startX = event.clientX
    startScrollLeft = el.scrollLeft
    dragActive = false
  }

  function onPointerMove(event: PointerEvent): void {
    const el = boundEl
    if (!el || pointerId === null || event.pointerId !== pointerId) return
    if (!dragActive) {
      if (Math.abs(event.clientX - startX) < DRAG_THRESHOLD_PX) return
      beginDrag(el, event)
    }
    event.preventDefault()
    el.scrollLeft = startScrollLeft - (event.clientX - startX)
  }

  function onPointerUp(event: PointerEvent): void {
    if (pointerId === null || event.pointerId !== pointerId) return
    endDrag()
  }

  function onPointerCancel(event: PointerEvent): void {
    if (pointerId === null || event.pointerId !== pointerId) return
    endDrag()
  }

  function onDragStart(event: DragEvent): void {
    if (pointerId !== null) event.preventDefault()
  }

  function attach(el: HTMLElement): void {
    boundEl = el
    el.addEventListener('pointerdown', onPointerDown)
    el.addEventListener('pointermove', onPointerMove)
    el.addEventListener('pointerup', onPointerUp)
    el.addEventListener('pointercancel', onPointerCancel)
    el.addEventListener('dragstart', onDragStart)
    el.addEventListener('scroll', schedule, { passive: true })
    if (typeof ResizeObserver !== 'undefined') {
      observer = new ResizeObserver(schedule)
      observer.observe(el)
      const first = el.firstElementChild
      if (first) observer.observe(first)
    }
    schedule()
  }

  function detach(): void {
    const el = boundEl
    const wasDragging = dragActive
    boundEl = null
    cancelFrame()
    observer?.disconnect()
    observer = null
    if (!el) return
    resetPointer()
    if (wasDragging) restoreDragStyles(el)
    el.removeEventListener('pointerdown', onPointerDown)
    el.removeEventListener('pointermove', onPointerMove)
    el.removeEventListener('pointerup', onPointerUp)
    el.removeEventListener('pointercancel', onPointerCancel)
    el.removeEventListener('dragstart', onDragStart)
    el.removeEventListener('scroll', schedule)
  }

  function bind(el: HTMLElement | null): void {
    if (el === boundEl) return
    detach()
    if (el) attach(el)
  }

  onMounted(() => {
    bind(scrollRef.value)
    window.addEventListener('resize', schedule, { passive: true })
  })

  watch(scrollRef, bind, { flush: 'post' })

  onBeforeUnmount(() => {
    window.removeEventListener('resize', schedule)
    detach()
  })

  return {
    scrollRef,
    isDragging,
    canScrollPrev,
    canScrollNext,
    progress,
    activeIndex,
    scrollPrev,
    scrollNext,
  }
}

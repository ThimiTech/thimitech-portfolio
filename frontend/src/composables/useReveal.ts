import { onBeforeUnmount, onMounted, ref } from 'vue'

const ENTER_TRANSITION_MS = 750
const STAGGER_CAP_MS = 600

/**
 * Scroll-reveal for `[data-reveal]` descendants of the returned root.
 *
 * - Adds `.is-visible` once an element enters the viewport (then unobserves).
 * - Optional stagger via `data-reveal-delay="120"` (clamped, cleared after
 *   the entrance so it never delays later hover transitions).
 * - `data-reveal="line"` variant grows hairlines via scaleX instead of fading.
 * - Fully inert under `prefers-reduced-motion` (handled in CSS).
 */
export function useReveal<T extends HTMLElement = HTMLElement>() {
  const root = ref<T | null>(null)
  let observer: IntersectionObserver | null = null
  const timers: Array<ReturnType<typeof setTimeout>> = []

  function reveal(target: HTMLElement): void {
    observer?.unobserve(target)
    target.classList.add('is-visible')
    // Clear the stagger delay after the entrance finishes so hover
    // transitions on the same element stay snappy.
    timers.push(
      setTimeout(
        () => {
          target.style.transitionDelay = ''
        },
        ENTER_TRANSITION_MS + STAGGER_CAP_MS,
      ),
    )
  }

  onMounted(() => {
    const el: HTMLElement | null = root.value
    if (!el) return
    const targets = el.querySelectorAll<HTMLElement>('[data-reveal]')
    if (targets.length === 0) return

    // Fail-safe: if IntersectionObserver is unavailable, show everything
    // immediately instead of leaving content hidden.
    if (typeof IntersectionObserver === 'undefined') {
      for (const target of targets) target.classList.add('is-visible')
      return
    }

    observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) reveal(entry.target as HTMLElement)
        }
      },
      { threshold: 0.15, rootMargin: '0px 0px -8% 0px' },
    )

    for (const target of targets) {
      const raw = Number(target.dataset.revealDelay ?? 0)
      const delay = Number.isFinite(raw) ? Math.min(Math.max(raw, 0), STAGGER_CAP_MS) : 0
      if (delay > 0) target.style.transitionDelay = `${delay}ms`
      observer.observe(target)
    }
  })

  onBeforeUnmount(() => {
    observer?.disconnect()
    observer = null
    for (const timer of timers) clearTimeout(timer)
    timers.length = 0
  })

  return { revealRoot: root }
}

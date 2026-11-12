import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

/**
 * Scroll animation is an enhancement: with reduced motion (or no matchMedia, e.g. tests)
 * every section renders its finished, static layout and no ScrollTrigger is created.
 */
export const canAnimate =
  typeof window !== 'undefined' &&
  typeof window.matchMedia === 'function' &&
  window.matchMedia('(prefers-reduced-motion: no-preference)').matches

if (canAnimate) gsap.registerPlugin(ScrollTrigger)

export { gsap, ScrollTrigger }

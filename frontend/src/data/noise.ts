/**
 * Deterministic value noise used by the generated scene imagery.
 * Everything is seeded, so a scene looks identical on every load and every machine.
 */

export function mulberry32(seed: number): () => number {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function latticeValue(ix: number, iy: number, seed: number): number {
  let h = Math.imul(ix, 0x27d4eb2d) ^ Math.imul(iy, 0x165667b1) ^ Math.imul(seed, 0x9e3779b1)
  h = Math.imul(h ^ (h >>> 15), 0x85ebca6b)
  h = Math.imul(h ^ (h >>> 13), 0xc2b2ae35)
  return ((h ^ (h >>> 16)) >>> 0) / 4294967295
}

/** Smooth 2D value noise in the 0..1 range. */
export function makeValueNoise(seed: number): (x: number, y: number) => number {
  return (x, y) => {
    const x0 = Math.floor(x)
    const y0 = Math.floor(y)
    const fx = x - x0
    const fy = y - y0
    const sx = fx * fx * (3 - 2 * fx)
    const sy = fy * fy * (3 - 2 * fy)

    const n00 = latticeValue(x0, y0, seed)
    const n10 = latticeValue(x0 + 1, y0, seed)
    const n01 = latticeValue(x0, y0 + 1, seed)
    const n11 = latticeValue(x0 + 1, y0 + 1, seed)

    return (n00 * (1 - sx) + n10 * sx) * (1 - sy) + (n01 * (1 - sx) + n11 * sx) * sy
  }
}

/** Fractal brownian motion — soft, cloud-like detail. */
export function fbm(
  noise: (x: number, y: number) => number,
  x: number,
  y: number,
  octaves = 5,
  lacunarity = 2,
  gain = 0.5,
): number {
  let amplitude = 0.5
  let frequency = 1
  let sum = 0
  let norm = 0
  for (let octave = 0; octave < octaves; octave += 1) {
    sum += amplitude * noise(x * frequency, y * frequency)
    norm += amplitude
    amplitude *= gain
    frequency *= lacunarity
  }
  return sum / norm
}

/** Ridged multifractal — sharp mountain ridges instead of rolling hills. */
export function ridged(
  noise: (x: number, y: number) => number,
  x: number,
  y: number,
  octaves = 6,
): number {
  let amplitude = 0.5
  let frequency = 1
  let sum = 0
  let norm = 0
  for (let octave = 0; octave < octaves; octave += 1) {
    const n = noise(x * frequency, y * frequency)
    sum += amplitude * (1 - Math.abs(n * 2 - 1))
    norm += amplitude
    amplitude *= 0.5
    frequency *= 2
  }
  return sum / norm
}

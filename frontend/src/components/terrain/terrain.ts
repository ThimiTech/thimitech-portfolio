import * as THREE from 'three'

// Abstract terrain, not survey or elevation data.
export function elevation(x: number, z: number) {
  const ridge =
    1.55 * Math.exp(-((x + 0.75) ** 2 / 1.8 + (z + 0.25) ** 2 / 1.15)) +
    1.12 * Math.exp(-((x - 1.25) ** 2 / 0.85 + (z + 0.7) ** 2 / 1.8)) +
    0.65 * Math.exp(-((x + 1.8) ** 2 / 0.65 + (z - 1) ** 2 / 0.65))
  return 0.12 + ridge + 0.09 * Math.sin(x * 5 + z * 3) * Math.sin(z * 4) * ridge
}

export function createTerrain() {
  const group = new THREE.Group()
  const n = 72
  const positions: number[] = []
  const indices: number[] = []
  for (let j = 0; j <= n; j++)
    for (let i = 0; i <= n; i++) {
      const x = (i / n) * 6 - 3
      const z = (j / n) * 4.8 - 2.4
      positions.push(x, elevation(x, z), z)
    }
  for (let j = 0; j < n; j++)
    for (let i = 0; i < n; i++) {
      const a = j * (n + 1) + i
      const b = a + 1
      const c = a + n + 1
      const d = c + 1
      indices.push(a, c, b, b, c, d)
    }
  const surface = new THREE.BufferGeometry()
  surface.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
  surface.setIndex(indices)
  surface.computeVertexNormals()
  group.add(
    new THREE.Mesh(
      surface,
      new THREE.MeshStandardMaterial({ color: '#d8c9ad', roughness: 1, side: THREE.DoubleSide }),
    ),
  )
  const contours: number[] = []
  for (let level = 0.16; level < 2.1; level += 0.11) {
    for (let t = 0; t < indices.length; t += 3) {
      const hits: number[][] = []
      for (let edge = 0; edge < 3; edge++) {
        const ai = indices[t + edge]! * 3
        const bi = indices[t + ((edge + 1) % 3)]! * 3
        const ay = positions[ai + 1]!
        const by = positions[bi + 1]!
        if (ay < level !== by < level) {
          const ratio = (level - ay) / (by - ay)
          hits.push([
            positions[ai]! + (positions[bi]! - positions[ai]!) * ratio,
            level + 0.008,
            positions[ai + 2]! + (positions[bi + 2]! - positions[ai + 2]!) * ratio,
          ])
        }
      }
      if (hits.length === 2) contours.push(...hits[0]!, ...hits[1]!)
    }
  }
  const contourGeometry = new THREE.BufferGeometry()
  contourGeometry.setAttribute('position', new THREE.Float32BufferAttribute(contours, 3))
  group.add(
    new THREE.LineSegments(
      contourGeometry,
      new THREE.LineBasicMaterial({ color: '#776749', transparent: true, opacity: 0.65 }),
    ),
  )
  const wall: number[] = []
  function edge(ax: number, az: number, bx: number, bz: number) {
    const ay = elevation(ax, az)
    const by = elevation(bx, bz)
    wall.push(ax, ay, az, bx, by, bz, ax, -0.13, az, bx, by, bz, bx, -0.13, bz, ax, -0.13, az)
  }
  for (let i = 0; i < n; i++) {
    const a = i / n
    const b = (i + 1) / n
    edge(a * 6 - 3, -2.4, b * 6 - 3, -2.4)
    edge(a * 6 - 3, 2.4, b * 6 - 3, 2.4)
    edge(-3, a * 4.8 - 2.4, -3, b * 4.8 - 2.4)
    edge(3, a * 4.8 - 2.4, 3, b * 4.8 - 2.4)
  }
  const wallGeometry = new THREE.BufferGeometry()
  wallGeometry.setAttribute('position', new THREE.Float32BufferAttribute(wall, 3))
  wallGeometry.computeVertexNormals()
  group.add(
    new THREE.Mesh(
      wallGeometry,
      new THREE.MeshStandardMaterial({ color: '#bbae92', roughness: 1, side: THREE.DoubleSide }),
    ),
  )
  const layers: THREE.Mesh[] = []
  for (let i = 0; i < 3; i++) {
    const geometry = new THREE.BoxGeometry(6, 0.075, 4.8)
    const slab = new THREE.Mesh(
      geometry,
      new THREE.MeshStandardMaterial({ color: ['#bd592f', '#ddd5c4', '#c4b9a2'][i], roughness: 1 }),
    )
    slab.position.y = -0.3 - i * 0.24
    slab.add(
      new THREE.LineSegments(
        new THREE.EdgesGeometry(geometry),
        new THREE.LineBasicMaterial({ color: '#7e735f', transparent: true, opacity: 0.45 }),
      ),
    )
    group.add(slab)
    layers.push(slab)
  }
  const grid = new THREE.GridHelper(6, 12, '#a68d70', '#a68d70')
  grid.position.y = -0.85
  grid.scale.z = 0.8
  const material = grid.material as THREE.LineBasicMaterial
  material.transparent = true
  material.opacity = 0.35
  group.add(grid)
  const marker = new THREE.Group()
  const stem = new THREE.Mesh(
    new THREE.CylinderGeometry(0.012, 0.012, 0.8, 8),
    new THREE.MeshBasicMaterial({ color: '#b4502a' }),
  )
  stem.position.y = 0.4
  const tip = new THREE.Mesh(
    new THREE.SphereGeometry(0.085, 16, 12),
    new THREE.MeshStandardMaterial({ color: '#b4502a', roughness: 0.7 }),
  )
  tip.position.y = 0.8
  marker.add(stem, tip)
  marker.position.set(0.7, elevation(0.7, 0.2), 0.2)
  group.add(marker)
  return { group, layers, grid }
}

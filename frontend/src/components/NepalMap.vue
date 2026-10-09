<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

interface Place {
  name: string
  note: string
  lat: number
  lng: number
}

const props = defineProps<{ places: Place[] }>()

const mapEl = ref<HTMLElement | null>(null)
let map: L.Map | null = null

// One colour per province (province codes 1-7)
const provinceColors: Record<string, string> = {
  '1': '#3b82c4',
  '2': '#d64545',
  '3': '#2e9e6b',
  '4': '#c98a3d',
  '5': '#8b5fbf',
  '6': '#e08e2b',
  '7': '#12726f',
}

onMounted(async () => {
  if (!mapEl.value) return

  map = L.map(mapEl.value, { scrollWheelZoom: false, attributionControl: false })
  map.fitBounds([[26.3, 80.0], [30.5, 88.3]])

  try {
    const res = await fetch('/nepal-districts.geojson')
    const data = await res.json()

    const districts = L.geoJSON(data, {
      style: (feature) => ({
        color: '#f3f6f5',
        weight: 1,
        fillColor: provinceColors[feature?.properties.province] ?? '#12726f',
        fillOpacity: 0.65,
      }),
      onEachFeature: (feature, layer) => {
        layer.bindTooltip(feature.properties.name, { sticky: true, className: 'district-tip' })
        layer.on({
          mouseover: (e) => (e.target as L.Path).setStyle({ weight: 2, fillOpacity: 0.9 }),
          mouseout: (e) => districts.resetStyle(e.target),
        })
      },
    }).addTo(map)
  } catch (err) {
    console.error('Could not load district boundaries', err)
  }

  const pinIcon = L.divIcon({
    className: '',
    html: '<span class="map-pin"></span>',
    iconSize: [22, 22],
    iconAnchor: [11, 22],
  })

  props.places.forEach((p) => {
    L.marker([p.lat, p.lng], { icon: pinIcon })
      .addTo(map!)
      .bindTooltip(p.name, { direction: 'top', offset: [0, -22] })
      .bindPopup(`<b>${p.name}</b><br>${p.note}`)
  })
})

onBeforeUnmount(() => {
  map?.remove()
})
</script>

<template>
  <div ref="mapEl" class="h-full w-full"></div>
</template>

<style>
/* Global (not scoped) because Leaflet builds this DOM outside Vue */
.map-pin {
  display: block;
  width: 22px;
  height: 22px;
  background: #d64545;
  border: 3px solid #f3f6f5;
  border-radius: 50% 50% 50% 0;
  transform: rotate(-45deg);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.35);
}
.district-tip {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
}
</style>
<script setup lang="ts">
import { computed } from 'vue'
import { LMap, LTileLayer, LPolyline, LMarker, LPopup, LCircleMarker } from '@vue-leaflet/vue-leaflet'
import * as L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { useCycleStore } from '@/stores/cycle'
import type { CaptureRecord, MountainPass, Route } from '@/types'

const store = useCycleStore()

// --- Emoji marker icon factory ---
function emojiIcon(emoji: string, size: number = 28): L.DivIcon {
  return L.divIcon({
    html: `<span style="font-size:${size}px;line-height:1;filter:drop-shadow(0 1px 2px rgba(0,0,0,0.3))">${emoji}</span>`,
    className: 'emoji-marker',
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  })
}

// --- Polyline decoding ---
function decodePolyline(encoded: string): [number, number][] {
  const points: [number, number][] = []
  let index = 0
  let lat = 0
  let lng = 0

  while (index < encoded.length) {
    let shift = 0
    let result = 0
    let byte: number

    do {
      byte = encoded.charCodeAt(index++) - 63
      result |= (byte & 0x1f) << shift
      shift += 5
    } while (byte >= 0x20)

    lat += result & 1 ? ~(result >> 1) : result >> 1

    shift = 0
    result = 0

    do {
      byte = encoded.charCodeAt(index++) - 63
      result |= (byte & 0x1f) << shift
      shift += 5
    } while (byte >= 0x20)

    lng += result & 1 ? ~(result >> 1) : result >> 1

    points.push([lat / 1e5, lng / 1e5])
  }

  return points
}

// --- Computed data ---

interface DecodedRoute {
  route: Route
  points: [number, number][]
}

const decodedRoutes = computed<DecodedRoute[]>(() => {
  return store.routes
    .filter((r) => r.polyline)
    .map((r) => ({ route: r, points: decodePolyline(r.polyline) }))
})

const sortedRoutes = computed<DecodedRoute[]>(() => {
  const selected = store.selectedRouteId
  return [...decodedRoutes.value].sort((a, b) => {
    const aSelected = a.route.route_id === selected ? 1 : 0
    const bSelected = b.route.route_id === selected ? 1 : 0
    return aSelected - bSelected
  })
})

const center = computed(() => {
  const selected = decodedRoutes.value.find(
    (dr) => dr.route.route_id === store.selectedRouteId,
  ) ?? decodedRoutes.value[0]
  if (selected && selected.points.length > 0) {
    const mid = Math.floor(selected.points.length / 2)
    return selected.points[mid] as [number, number]
  }
  return [40.45, -111.3] as [number, number]
})

const cameraMarkers = computed(() => {
  if (!store.currentCycle?.captures) return []
  return store.currentCycle.captures.filter(
    (c) => c.latitude != null && c.longitude != null,
  )
})

const passMarkers = computed(() => {
  return store.passes.filter((p) => p.latitude != null && p.longitude != null)
})

const plowMarkers = computed(() => {
  if (!store.currentCycle?.plows) return []
  return store.currentCycle.plows.filter(
    (p) => p.latitude != null && p.longitude != null,
  )
})

// --- Icon getters ---
function cameraIcon(capture: CaptureRecord): L.DivIcon {
  if (capture.has_snow) return emojiIcon('🥶', 26)
  if (capture.has_animal) return emojiIcon('🦌', 26)
  return emojiIcon('📷', 24)
}

function passIcon(p: MountainPass): L.DivIcon {
  if (p.closure_status?.toUpperCase() === 'CLOSED') return emojiIcon('🚫', 28)
  const temp = parseInt(p.air_temperature)
  if (!isNaN(temp) && temp <= 32) return emojiIcon('🥶', 28)
  return emojiIcon('⛰️', 28)
}

function formatDuration(seconds: number): string {
  const hrs = Math.floor(seconds / 3600)
  const mins = Math.round((seconds % 3600) / 60)
  return hrs > 0 ? `${hrs}h ${mins}m` : `${mins}m`
}

function formatDistance(meters: number): string {
  return `${(meters / 1609.34).toFixed(1)} mi`
}
</script>

<template>
  <div class="map-container">
    <LMap :zoom="10" :center="center" :use-global-leaflet="false">
      <LTileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution="&copy; OpenStreetMap contributors"
      />

      <!-- Route polylines -->
      <LPolyline
        v-for="dr in sortedRoutes"
        :key="`route-${dr.route.route_id}`"
        :lat-lngs="dr.points"
        :color="dr.route.color"
        :weight="dr.route.route_id === store.selectedRouteId ? 5 : 3"
        :opacity="dr.route.route_id === store.selectedRouteId ? 0.9 : 0.35"
        :dash-array="dr.route.route_id === store.selectedRouteId ? undefined : '8 6'"
      >
        <LPopup>
          <div class="popup">
            <strong>{{ dr.route.name }}</strong>
            <div v-if="dr.route.distance_m" class="popup-road">
              {{ dr.route.distance_display || formatDistance(dr.route.distance_m) }} ·
              {{ dr.route.travel_time_display || formatDuration(dr.route.duration_s) }}
            </div>
          </div>
        </LPopup>
      </LPolyline>

      <!-- Mountain pass markers (emoji) -->
      <LMarker
        v-for="p in passMarkers"
        :key="`pass-${p.id}`"
        :lat-lng="[p.latitude!, p.longitude!]"
        :icon="passIcon(p)"
      >
        <LPopup>
          <div class="popup">
            <strong>⛰️ {{ p.name }}</strong>
            <div class="popup-road">{{ p.elevation_ft }}' elev</div>
            <div v-if="p.air_temperature" class="pass-temp">
              🌡️ {{ p.air_temperature }}°F
            </div>
            <div class="popup-badges">
              <span v-if="p.closure_status === 'CLOSED'" class="popup-tag popup-tag--danger">🚫 CLOSED</span>
              <span v-else-if="p.closure_status === 'OPEN'" class="popup-tag popup-tag--open">🟢 OPEN</span>
              <span v-if="p.surface_status" class="popup-tag">🛣️ {{ p.surface_status }}</span>
            </div>
            <div v-if="p.wind_speed" class="popup-notes">
              💨 {{ p.wind_speed }} mph {{ p.wind_direction }}
              <span v-if="p.wind_gust">(gusts {{ p.wind_gust }})</span>
            </div>
            <div v-if="p.visibility" class="popup-notes">
              👁️ Visibility: {{ p.visibility }}
            </div>
          </div>
        </LPopup>
      </LMarker>

      <!-- Snow plow markers (emoji) -->
      <LMarker
        v-for="plow in plowMarkers"
        :key="`plow-${plow.id}`"
        :lat-lng="[plow.latitude!, plow.longitude!]"
        :icon="emojiIcon('🚜', 24)"
      >
        <LPopup>
          <div class="popup">
            <strong>🚜 Snow Plow</strong>
            <div class="popup-road">{{ plow.name }}</div>
            <div v-if="plow.speed != null" class="popup-notes">
              🏎️ {{ plow.speed }} mph
            </div>
            <div v-if="plow.last_updated" class="popup-notes">
              🕐 {{ plow.last_updated }}
            </div>
          </div>
        </LPopup>
      </LMarker>

      <!-- Camera markers (emoji) -->
      <LMarker
        v-for="capture in cameraMarkers"
        :key="`cam-${capture.camera_id}`"
        :lat-lng="[capture.latitude!, capture.longitude!]"
        :icon="cameraIcon(capture)"
      >
        <LPopup>
          <div class="popup">
            <strong>📷 {{ capture.location }}</strong>
            <br />
            <span class="popup-road">{{ capture.roadway }} {{ capture.direction }}</span>
            <div class="popup-badges">
              <span v-if="capture.has_snow" class="popup-tag popup-tag--danger">❄️ Snow</span>
              <span v-if="capture.has_car" class="popup-tag">🚗 Cars</span>
              <span v-if="capture.has_truck" class="popup-tag">🚛 Trucks</span>
              <span v-if="capture.has_animal" class="popup-tag popup-tag--warning">🦌 Animals</span>
            </div>
            <p v-if="capture.analysis_notes" class="popup-notes">{{ capture.analysis_notes }}</p>
            <img
              v-if="capture.image_url"
              :src="capture.image_url"
              class="popup-image"
              loading="lazy"
            />
          </div>
        </LPopup>
      </LMarker>
    </LMap>

    <!-- Route legend -->
    <div v-if="store.routes.length > 0" class="route-legend">
      <div
        v-for="r in store.routes"
        :key="r.route_id"
        class="legend-item"
        :class="{ 'legend-item--selected': r.route_id === store.selectedRouteId }"
        @click="store.selectRoute(r.route_id)"
      >
        <span class="legend-swatch" :style="{ backgroundColor: r.color }"></span>
        <span class="legend-label">{{ r.name }}</span>
        <span v-if="r.duration_s" class="legend-time">
          {{ r.travel_time_display || formatDuration(r.duration_s) }}
        </span>
      </div>
      <div class="legend-item legend-item--icons">
        <span>📷 cam</span>
        <span>⛰️ pass</span>
        <span v-if="plowMarkers.length">🚜 plow</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.map-container {
  width: 100%;
  height: 420px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--color-border);
  position: relative;
}

@media (min-width: 768px) {
  .map-container {
    height: 520px;
  }
}

/* Remove default leaflet icon background/border for our emoji markers */
:deep(.emoji-marker) {
  background: none !important;
  border: none !important;
  display: flex;
  align-items: center;
  justify-content: center;
}

.popup {
  max-width: 280px;
  font-size: 0.85rem;
}

.popup-road {
  color: #6b7280;
  font-size: 0.75rem;
}

.popup-badges {
  margin: 0.35rem 0;
  display: flex;
  gap: 0.25rem;
  flex-wrap: wrap;
}

.popup-tag {
  display: inline-block;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  font-size: 0.65rem;
  font-weight: 600;
  background: #e5e7eb;
  color: #374151;
}

.popup-tag--danger {
  background: #fee2e2;
  color: #dc2626;
}

.popup-tag--warning {
  background: #fef9c3;
  color: #ca8a04;
}

.popup-tag--open {
  background: #dcfce7;
  color: #16a34a;
}

.pass-temp {
  font-size: 1.1rem;
  font-weight: 700;
  margin: 0.2rem 0;
}

.popup-notes {
  margin: 0.3rem 0;
  font-size: 0.75rem;
  color: #6b7280;
  line-height: 1.3;
}

.popup-image {
  width: 100%;
  max-height: 150px;
  object-fit: cover;
  border-radius: 4px;
  margin-top: 0.3rem;
}

/* Route legend overlay */
.route-legend {
  position: absolute;
  bottom: 0.5rem;
  left: 0.5rem;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(8px);
  border-radius: 8px;
  padding: 0.5rem 0.65rem;
  font-size: 0.75rem;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  cursor: pointer;
  padding: 0.15rem 0.3rem;
  border-radius: 4px;
  transition: background-color 0.15s;
}

.legend-item:hover {
  background: rgba(0, 0, 0, 0.05);
}

.legend-item--selected {
  background: rgba(0, 0, 0, 0.08);
  font-weight: 600;
}

.legend-item--icons {
  display: flex;
  gap: 0.5rem;
  font-size: 0.7rem;
  color: #6b7280;
  cursor: default;
  padding-top: 0.2rem;
  border-top: 1px solid #e5e7eb;
  margin-top: 0.1rem;
}

.legend-swatch {
  width: 18px;
  height: 4px;
  border-radius: 2px;
  flex-shrink: 0;
}

.legend-label {
  font-weight: 500;
  color: #374151;
}

.legend-time {
  color: #6b7280;
  margin-left: auto;
  font-variant-numeric: tabular-nums;
}
</style>

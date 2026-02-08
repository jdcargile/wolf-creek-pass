<script setup lang="ts">
import { computed } from 'vue'
import { LMap, LTileLayer, LPolyline, LMarker, LPopup, LCircleMarker } from '@vue-leaflet/vue-leaflet'
import 'leaflet/dist/leaflet.css'
import { useCycleStore } from '@/stores/cycle'
import type { CaptureRecord, Event as TrafficEvent, Route } from '@/types'

const store = useCycleStore()

// Decode Google encoded polyline
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

// Decoded polylines for all routes
interface DecodedRoute {
  route: Route
  points: [number, number][]
}

const decodedRoutes = computed<DecodedRoute[]>(() => {
  return store.routes
    .filter((r) => r.polyline)
    .map((r) => ({ route: r, points: decodePolyline(r.polyline) }))
})

// Map center (middle of primary route or default Utah)
const center = computed(() => {
  const primary = decodedRoutes.value[0]
  if (primary && primary.points.length > 0) {
    const mid = Math.floor(primary.points.length / 2)
    return primary.points[mid] as [number, number]
  }
  return [40.45, -111.3] as [number, number]
})

// Camera markers
const cameraMarkers = computed(() => {
  if (!store.currentCycle?.captures) return []
  return store.currentCycle.captures.filter(
    (c) => c.latitude != null && c.longitude != null,
  )
})

// Event markers
const eventMarkers = computed(() => {
  if (!store.currentCycle?.events) return []
  return store.currentCycle.events.filter(
    (e) => e.latitude != null && e.longitude != null,
  )
})

function cameraColor(capture: CaptureRecord): string {
  if (capture.has_snow) return '#dc2626'
  if (capture.has_animal) return '#ca8a04'
  return '#16a34a'
}

function eventColor(event: TrafficEvent): string {
  if (event.is_full_closure) return '#dc2626'
  if (event.event_type === 'accidentsAndIncidents') return '#ea580c'
  return '#f59e0b'
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

      <!-- Route polylines (render alternate routes first, primary on top) -->
      <LPolyline
        v-for="(dr, i) in [...decodedRoutes].reverse()"
        :key="`route-${dr.route.route_id}`"
        :lat-lngs="dr.points"
        :color="dr.route.color"
        :weight="i === decodedRoutes.length - 1 ? 5 : 3"
        :opacity="i === decodedRoutes.length - 1 ? 0.9 : 0.5"
        :dash-array="i === decodedRoutes.length - 1 ? undefined : '8 6'"
      >
        <LPopup>
          <div class="popup">
            <strong>{{ dr.route.name }}</strong>
            <div v-if="dr.route.distance_m" class="popup-road">
              {{ formatDistance(dr.route.distance_m) }} &middot;
              {{ formatDuration(dr.route.duration_in_traffic_s || dr.route.duration_s) }}
            </div>
          </div>
        </LPopup>
      </LPolyline>

      <!-- Camera markers -->
      <LCircleMarker
        v-for="capture in cameraMarkers"
        :key="`cam-${capture.camera_id}`"
        :lat-lng="[capture.latitude!, capture.longitude!]"
        :radius="8"
        :color="cameraColor(capture)"
        :fill-color="cameraColor(capture)"
        :fill-opacity="0.8"
      >
        <LPopup>
          <div class="popup">
            <strong>{{ capture.location }}</strong>
            <br />
            <span class="popup-road">{{ capture.roadway }} {{ capture.direction }}</span>
            <div class="popup-badges">
              <span v-if="capture.has_snow" class="popup-tag popup-tag--danger">Snow</span>
              <span v-if="capture.has_car" class="popup-tag">Cars</span>
              <span v-if="capture.has_truck" class="popup-tag">Trucks</span>
              <span v-if="capture.has_animal" class="popup-tag popup-tag--warning">Animals</span>
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
      </LCircleMarker>

      <!-- Event markers -->
      <LCircleMarker
        v-for="event in eventMarkers"
        :key="`evt-${event.id}`"
        :lat-lng="[event.latitude!, event.longitude!]"
        :radius="6"
        :color="eventColor(event)"
        :fill-color="eventColor(event)"
        :fill-opacity="0.9"
      >
        <LPopup>
          <div class="popup">
            <strong>{{ event.event_type }}</strong>
            <br />
            <span class="popup-road">{{ event.roadway_name }} {{ event.direction }}</span>
            <p class="popup-notes">{{ event.description }}</p>
            <span v-if="event.is_full_closure" class="popup-tag popup-tag--danger">Full Closure</span>
          </div>
        </LPopup>
      </LCircleMarker>
    </LMap>

    <!-- Route legend -->
    <div v-if="store.routes.length > 0" class="route-legend">
      <div
        v-for="r in store.routes"
        :key="r.route_id"
        class="legend-item"
      >
        <span class="legend-swatch" :style="{ backgroundColor: r.color }"></span>
        <span class="legend-label">{{ r.name }}</span>
        <span v-if="r.duration_s" class="legend-time">
          {{ formatDuration(r.duration_in_traffic_s || r.duration_s) }}
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.map-container {
  width: 100%;
  height: 400px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--color-border);
  position: relative;
}

@media (min-width: 768px) {
  .map-container {
    height: 500px;
  }
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
  border-radius: 3px;
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
  background: rgba(255, 255, 255, 0.92);
  border-radius: 6px;
  padding: 0.4rem 0.6rem;
  font-size: 0.75rem;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.4rem;
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

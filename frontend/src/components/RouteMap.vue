<script setup lang="ts">
import { computed, watch } from 'vue'
import { LMap, LTileLayer, LPolyline, LMarker, LPopup, LCircleMarker } from '@vue-leaflet/vue-leaflet'
import 'leaflet/dist/leaflet.css'
import { useCycleStore } from '@/stores/cycle'
import type { CaptureRecord, Event as TrafficEvent } from '@/types'

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

// Route polyline
const routePoints = computed(() => {
  if (!store.currentCycle?.route?.polyline) return []
  return decodePolyline(store.currentCycle.route.polyline)
})

// Map center (middle of route or default Utah)
const center = computed<[number, number]>(() => {
  if (routePoints.value.length > 0) {
    const mid = Math.floor(routePoints.value.length / 2)
    return routePoints.value[mid]
  }
  return [40.45, -111.3]
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
</script>

<template>
  <div class="map-container">
    <LMap :zoom="10" :center="center" :use-global-leaflet="false">
      <LTileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution="&copy; OpenStreetMap contributors"
      />

      <!-- Route polyline -->
      <LPolyline
        v-if="routePoints.length"
        :lat-lngs="routePoints"
        :color="'#3b82f6'"
        :weight="4"
        :opacity="0.8"
      />

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
  </div>
</template>

<style scoped>
.map-container {
  width: 100%;
  height: 400px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--color-border);
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
</style>

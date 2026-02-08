/** Pinia store for managing the current capture cycle state. */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { CycleData, CycleSummary, Route, MountainPass, SnowPlow, CaptureRecord, WeatherStation } from '@/types'
import { fetchCycleIndex, fetchCycleData, fetchLatestCycle } from '@/composables/useApi'

/** Weather station names we care about (must match UDOT exactly, case-insensitive). */
const WEATHER_STATION_NAMES = new Set([
  'i-80 @ parleys summit',
  'sr-35 @ wolf creek',
  'sr-35 @ wolf creek pass',
])

export const useCycleStore = defineStore('cycle', () => {
  // State
  const currentCycle = ref<CycleData | null>(null)
  const allCycles = ref<CycleSummary[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const selectedRouteId = ref<string | null>(null)

  // Map focus: set to fly the map to a lat/lng. Incremented counter forces reactivity.
  const mapFocus = ref<{ lat: number; lng: number; zoom: number; _seq: number } | null>(null)

  // --- Core getters ---
  const hasData = computed(() => currentCycle.value !== null)
  const routes = computed<Route[]>(() => currentCycle.value?.routes ?? [])

  // Selected route (defaults to first route)
  const selectedRoute = computed<Route | null>(() => {
    if (!routes.value.length) return null
    if (selectedRouteId.value) {
      return routes.value.find((r) => r.route_id === selectedRouteId.value) ?? routes.value[0]
    }
    return routes.value[0]
  })

  // --- Route-filtered getters ---

  const travelTimeMin = computed(() => {
    const r = selectedRoute.value
    if (!r) return null
    return r.duration_s ? Math.round(r.duration_s / 60) : null
  })

  const travelTimeDisplay = computed(() => {
    const r = selectedRoute.value
    return r?.travel_time_display || null
  })

  const distanceDisplay = computed(() => {
    const r = selectedRoute.value
    return r?.distance_display || null
  })

  const distanceMiles = computed(() => {
    const r = selectedRoute.value
    if (!r) return null
    return r.distance_m ? (r.distance_m / 1609.34).toFixed(1) : null
  })

  // All passes from the cycle data
  const passes = computed<MountainPass[]>(() => currentCycle.value?.passes ?? [])

  // All plows from the cycle data
  const plows = computed<SnowPlow[]>(() => currentCycle.value?.plows ?? [])
  const plowCount = computed(() => plows.value.length)

  // All captures from the cycle data
  const captures = computed<CaptureRecord[]>(() => currentCycle.value?.captures ?? [])

  // Filtered weather stations (only the 3 we care about)
  const weather = computed<WeatherStation[]>(() => {
    const all = currentCycle.value?.weather ?? []
    return all.filter((w) => WEATHER_STATION_NAMES.has(w.station_name.toLowerCase()))
  })

  // Camera and snow counts
  const cameraCount = computed(() => currentCycle.value?.cycle.cameras_processed ?? 0)
  const snowCount = computed(() => currentCycle.value?.cycle.snow_count ?? 0)

  // Wolf Creek pass helpers
  const wolfCreekPass = computed<MountainPass | null>(() =>
    passes.value.find((p) => p.name.toLowerCase().includes('wolf creek')) ?? null,
  )
  const wolfCreekClosed = computed(
    () => wolfCreekPass.value?.closure_status?.toUpperCase() === 'CLOSED',
  )

  // --- Actions ---

  let _focusSeq = 0

  function selectRoute(routeId: string | null) {
    selectedRouteId.value = routeId
  }

  function flyTo(lat: number, lng: number, zoom: number = 14) {
    _focusSeq++
    mapFocus.value = { lat, lng, zoom, _seq: _focusSeq }
  }

  async function loadLatest() {
    loading.value = true
    error.value = null
    try {
      currentCycle.value = await fetchLatestCycle()
      // Auto-select first route
      if (currentCycle.value?.routes?.length && !selectedRouteId.value) {
        selectedRouteId.value = currentCycle.value.routes[0].route_id
      }
    } catch (e: any) {
      error.value = e.message || 'Failed to load data'
    } finally {
      loading.value = false
    }
  }

  async function loadCycle(cycleId: string) {
    loading.value = true
    error.value = null
    try {
      currentCycle.value = await fetchCycleData(cycleId)
      // Auto-select first route
      if (currentCycle.value?.routes?.length && !selectedRouteId.value) {
        selectedRouteId.value = currentCycle.value.routes[0].route_id
      }
    } catch (e: any) {
      error.value = e.message || 'Failed to load cycle'
    } finally {
      loading.value = false
    }
  }

  async function loadIndex() {
    try {
      const index = await fetchCycleIndex()
      allCycles.value = index.cycles
    } catch (e: any) {
      console.warn('Failed to load cycle index:', e.message)
    }
  }

  return {
    // State
    currentCycle,
    allCycles,
    loading,
    error,
    selectedRouteId,
    mapFocus,
    // Getters
    hasData,
    routes,
    selectedRoute,
    travelTimeMin,
    travelTimeDisplay,
    distanceDisplay,
    distanceMiles,
    passes,
    plows,
    plowCount,
    captures,
    weather,
    cameraCount,
    snowCount,
    wolfCreekPass,
    wolfCreekClosed,
    // Actions
    selectRoute,
    flyTo,
    loadLatest,
    loadCycle,
    loadIndex,
  }
})

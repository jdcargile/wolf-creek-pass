/** Pinia store for managing the current capture cycle state. */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { CycleData, CycleSummary, Route, MountainPass, SnowPlow, CaptureRecord } from '@/types'
import { fetchCycleIndex, fetchCycleData, fetchLatestCycle } from '@/composables/useApi'

export const useCycleStore = defineStore('cycle', () => {
  // State
  const currentCycle = ref<CycleData | null>(null)
  const allCycles = ref<CycleSummary[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const selectedRouteId = ref<string | null>(null)

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
    const s = r.duration_in_traffic_s ?? r.duration_s
    return s ? Math.round(s / 60) : null
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

  function selectRoute(routeId: string | null) {
    selectedRouteId.value = routeId
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
    // Getters
    hasData,
    routes,
    selectedRoute,
    travelTimeMin,
    distanceMiles,
    passes,
    plows,
    plowCount,
    captures,
    cameraCount,
    snowCount,
    wolfCreekPass,
    wolfCreekClosed,
    // Actions
    selectRoute,
    loadLatest,
    loadCycle,
    loadIndex,
  }
})

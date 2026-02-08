/** Pinia store for managing the current capture cycle state. */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { CycleData, CycleSummary, Route } from '@/types'
import { fetchCycleIndex, fetchCycleData, fetchLatestCycle } from '@/composables/useApi'

export const useCycleStore = defineStore('cycle', () => {
  // State
  const currentCycle = ref<CycleData | null>(null)
  const allCycles = ref<CycleSummary[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const hasData = computed(() => currentCycle.value !== null)
  const routes = computed<Route[]>(() => currentCycle.value?.routes ?? [])
  const primaryRoute = computed<Route | null>(() => routes.value[0] ?? null)
  const snowCount = computed(() => currentCycle.value?.cycle.snow_count ?? 0)
  const cameraCount = computed(() => currentCycle.value?.cycle.cameras_processed ?? 0)
  const travelTimeMin = computed(() => {
    const s = currentCycle.value?.cycle.travel_time_s
    return s ? Math.round(s / 60) : null
  })
  const distanceMiles = computed(() => {
    const m = currentCycle.value?.cycle.distance_m
    return m ? (m / 1609.34).toFixed(1) : null
  })

  // Actions
  async function loadLatest() {
    loading.value = true
    error.value = null
    try {
      currentCycle.value = await fetchLatestCycle()
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
    currentCycle,
    allCycles,
    loading,
    error,
    hasData,
    routes,
    primaryRoute,
    snowCount,
    cameraCount,
    travelTimeMin,
    distanceMiles,
    loadLatest,
    loadCycle,
    loadIndex,
  }
})

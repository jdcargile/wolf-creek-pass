/** Pinia store for SensorPush cabin sensor data. */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { SensorData } from '@/types/sensorpush'
import { fetchSensorPushSummary, fetchSensorPushHistory } from '@/composables/useReolinkApi'

export const useSensorPushStore = defineStore('sensorpush', () => {
  // ── State ────────────────────────────────────────────────────────────────
  const sensors = ref<SensorData[]>([])
  const loading = ref(false)
  const loadingHistory = ref(false)
  const error = ref<string | null>(null)

  // ── Derived ──────────────────────────────────────────────────────────────
  const hasData = computed(() => sensors.value.length > 0)

  // ── Actions ──────────────────────────────────────────────────────────────

  /** Fast load — current readings only (~3s). */
  async function loadSummary() {
    loading.value = true
    error.value = null
    try {
      const data = await fetchSensorPushSummary()
      sensors.value = data.sensors
    } catch (e: any) {
      error.value = e.message || 'Failed to load sensor data'
      sensors.value = []
    } finally {
      loading.value = false
    }
  }

  /** Slow load — 7-day history with charts + ranges (cached on backend). */
  async function loadHistory() {
    loadingHistory.value = true
    try {
      const data = await fetchSensorPushHistory()
      // Merge history into existing sensors (preserves current readings
      // that are already displayed while enriching with ranges + charts).
      sensors.value = data.sensors
    } catch (e: any) {
      // Don't overwrite the summary — charts just won't appear
      console.warn('SensorPush history load failed:', e.message)
    } finally {
      loadingHistory.value = false
    }
  }

  return {
    sensors,
    loading,
    loadingHistory,
    error,
    hasData,
    loadSummary,
    loadHistory,
  }
})

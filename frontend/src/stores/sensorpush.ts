/** Pinia store for SensorPush cabin sensor data. */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { SensorData } from '@/types/sensorpush'
import { fetchSensorPushData } from '@/composables/useReolinkApi'

export const useSensorPushStore = defineStore('sensorpush', () => {
  // ── State ────────────────────────────────────────────────────────────────
  const sensors = ref<SensorData[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ── Derived ──────────────────────────────────────────────────────────────
  const hasData = computed(() => sensors.value.length > 0)

  // ── Actions ──────────────────────────────────────────────────────────────
  async function load() {
    loading.value = true
    error.value = null
    try {
      const data = await fetchSensorPushData()
      sensors.value = data.sensors
    } catch (e: any) {
      error.value = e.message || 'Failed to load sensor data'
      sensors.value = []
    } finally {
      loading.value = false
    }
  }

  return {
    sensors,
    loading,
    error,
    hasData,
    load,
  }
})

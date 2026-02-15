/** Pinia store for Reolink cabin camera snapshots. */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ReolinkCamera, ReolinkSnapshot } from '@/types/reolink'
import { fetchReolinkSnapshots } from '@/composables/useReolinkApi'
import { todayMountain, mountainHour } from '@/utils/time'

/** Extract the Mountain Time hour (0-23) from an ISO timestamp string. */
function hourOf(ts: string): number {
  return mountainHour(ts)
}

export const useReolinkStore = defineStore('reolink', () => {
  // ── State ────────────────────────────────────────────────────────────────
  const cameras = ref<ReolinkCamera[]>([])
  const selectedDate = ref(todayMountain())
  const selectedHour = ref<number | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const playing = ref(false)

  // ── Derived ──────────────────────────────────────────────────────────────

  /** Sorted, deduplicated hours that have at least one snapshot across all cameras. */
  const availableHours = computed<number[]>(() => {
    const hours = new Set<number>()
    for (const cam of cameras.value) {
      for (const snap of cam.snapshots) {
        hours.add(hourOf(snap.timestamp))
      }
    }
    return [...hours].sort((a, b) => a - b)
  })

  /** True when we have data to display. */
  const hasData = computed(() => cameras.value.length > 0 && availableHours.value.length > 0)

  /** The snapshot for each camera at the currently selected hour. */
  const currentSnapshots = computed<Map<string, ReolinkSnapshot | null>>(() => {
    const map = new Map<string, ReolinkSnapshot | null>()
    for (const cam of cameras.value) {
      if (selectedHour.value === null) {
        map.set(cam.id, null)
        continue
      }
      // Find the snapshot closest to the selected hour
      const match = cam.snapshots.find((s) => hourOf(s.timestamp) === selectedHour.value)
      map.set(cam.id, match ?? null)
    }
    return map
  })

  /** Weather data from the first camera that has it at the selected hour. */
  const weatherAtSelectedTime = computed(() => {
    for (const [, snap] of currentSnapshots.value) {
      if (snap?.weather && Object.keys(snap.weather).length > 0) {
        return snap.weather
      }
    }
    return null
  })

  /** Total snapshots across all cameras for the selected date. */
  const totalSnapshots = computed(() =>
    cameras.value.reduce((sum, cam) => sum + cam.snapshots.length, 0),
  )

  // ── Actions ──────────────────────────────────────────────────────────────

  async function loadDate(date: string) {
    loading.value = true
    error.value = null
    playing.value = false
    try {
      const data = await fetchReolinkSnapshots(date)
      cameras.value = data.cameras
      selectedDate.value = data.date

      // Default to the latest available hour
      const hours = availableHours.value
      selectedHour.value = hours.length > 0 ? hours[hours.length - 1]! : null
    } catch (e: any) {
      error.value = e.message || 'Failed to load cabin cameras'
      cameras.value = []
      selectedHour.value = null
    } finally {
      loading.value = false
    }
  }

  function setHour(hour: number) {
    selectedHour.value = hour
  }

  function nextHour() {
    const hours = availableHours.value
    if (!hours.length) return
    const idx = hours.indexOf(selectedHour.value ?? -1)
    if (idx < hours.length - 1) {
      selectedHour.value = hours[idx + 1] ?? hours[0]!
    } else {
      selectedHour.value = hours[0]! // wrap around
    }
  }

  function prevHour() {
    const hours = availableHours.value
    if (!hours.length) return
    const idx = hours.indexOf(selectedHour.value ?? -1)
    if (idx > 0) {
      selectedHour.value = hours[idx - 1] ?? hours[hours.length - 1]!
    } else {
      selectedHour.value = hours[hours.length - 1]! // wrap around
    }
  }

  let playTimer: ReturnType<typeof setInterval> | null = null

  function togglePlay() {
    if (playing.value) {
      playing.value = false
      if (playTimer) {
        clearInterval(playTimer)
        playTimer = null
      }
    } else {
      playing.value = true
      playTimer = setInterval(() => {
        const hours = availableHours.value
        const idx = hours.indexOf(selectedHour.value ?? -1)
        if (idx >= hours.length - 1) {
          // Reached end — stop
          playing.value = false
          if (playTimer) {
            clearInterval(playTimer)
            playTimer = null
          }
        } else {
          nextHour()
        }
      }, 1500)
    }
  }

  function stopPlay() {
    playing.value = false
    if (playTimer) {
      clearInterval(playTimer)
      playTimer = null
    }
  }

  return {
    // State
    cameras,
    selectedDate,
    selectedHour,
    loading,
    error,
    playing,
    // Getters
    availableHours,
    hasData,
    currentSnapshots,
    weatherAtSelectedTime,
    totalSnapshots,
    // Actions
    loadDate,
    setHour,
    nextHour,
    prevHour,
    togglePlay,
    stopPlay,
  }
})

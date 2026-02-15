<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useReolinkStore } from '@/stores/reolink'
import ReolinkTimeSlider from '@/components/ReolinkTimeSlider.vue'
import ReolinkCameraCard from '@/components/ReolinkCameraCard.vue'

const store = useReolinkStore()

onMounted(() => {
  store.loadDate(store.selectedDate)
})

/** Reload when the date picker changes. */
function onDateChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.value) {
    store.loadDate(input.value)
  }
}

/** Navigate to previous day. */
function prevDay() {
  const d = new Date(store.selectedDate + 'T12:00:00Z')
  d.setUTCDate(d.getUTCDate() - 1)
  store.loadDate(d.toISOString().slice(0, 10))
}

/** Navigate to next day. */
function nextDay() {
  const d = new Date(store.selectedDate + 'T12:00:00Z')
  d.setUTCDate(d.getUTCDate() + 1)
  const today = new Date().toISOString().slice(0, 10)
  const next = d.toISOString().slice(0, 10)
  if (next <= today) {
    store.loadDate(next)
  }
}

/** Weather summary for the selected time. */
function fmtTemp(t: number | undefined): string {
  return t !== undefined ? `${Math.round(t)}` : '--'
}

/** Stop playback when component is unmounted. */
watch(
  () => store.playing,
  () => {},
  { flush: 'post' },
)
</script>

<template>
  <section class="reolink-section">
    <!-- Section header -->
    <div class="section-header">
      <h2>Cabin Cameras</h2>
      <div class="date-controls">
        <button class="date-nav" @click="prevDay" title="Previous day" aria-label="Previous day">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <path d="M10.5 3L5.5 8l5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
        <input
          type="date"
          class="date-picker"
          :value="store.selectedDate"
          :max="new Date().toISOString().slice(0, 10)"
          @change="onDateChange"
        />
        <button
          class="date-nav"
          @click="nextDay"
          :disabled="store.selectedDate >= new Date().toISOString().slice(0, 10)"
          title="Next day"
          aria-label="Next day"
        >
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <path d="M5.5 3l5 5-5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="store.loading" class="reolink-status">Loading cabin cameras...</div>

    <!-- Error -->
    <div v-else-if="store.error" class="reolink-status reolink-status--error">
      {{ store.error }}
    </div>

    <!-- Content -->
    <template v-else-if="store.hasData">
      <!-- Weather summary bar -->
      <div v-if="store.weatherAtSelectedTime" class="weather-bar">
        <span class="weather-item">
          {{ fmtTemp(store.weatherAtSelectedTime.temperature_f) }}°F
        </span>
        <span v-if="store.weatherAtSelectedTime.weather_description" class="weather-item weather-item--desc">
          {{ store.weatherAtSelectedTime.weather_description }}
        </span>
        <span v-if="store.weatherAtSelectedTime.wind_speed_mph" class="weather-item">
          Wind {{ Math.round(store.weatherAtSelectedTime.wind_speed_mph!) }} mph
        </span>
        <span v-if="store.weatherAtSelectedTime.snowfall_in" class="weather-item">
          Snow {{ store.weatherAtSelectedTime.snowfall_in }}"
        </span>
        <span v-if="store.weatherAtSelectedTime.cloud_cover_pct !== undefined" class="weather-item">
          Cloud {{ Math.round(store.weatherAtSelectedTime.cloud_cover_pct!) }}%
        </span>
      </div>

      <!-- Time slider -->
      <ReolinkTimeSlider />

      <!-- Camera grid -->
      <div class="camera-grid">
        <ReolinkCameraCard
          v-for="cam in store.cameras"
          :key="cam.id"
          :camera="cam"
          :snapshot="store.currentSnapshots.get(cam.id) ?? null"
        />
      </div>

      <!-- Snapshot count footer -->
      <div class="section-footer">
        {{ store.totalSnapshots }} snapshots across {{ store.cameras.length }} cameras
      </div>
    </template>

    <!-- No data -->
    <div v-else class="reolink-status">
      No cabin camera data for {{ store.selectedDate }}.
    </div>
  </section>
</template>

<style scoped>
.reolink-section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

/* ── Header ───────────────────────────────────────────────────────────── */

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.section-header h2 {
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0;
}

.date-controls {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.date-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-surface);
  color: var(--color-text-muted);
  cursor: pointer;
  transition: all 0.15s;
}

.date-nav:hover:not(:disabled) {
  border-color: var(--color-border-hover);
  color: var(--color-text);
}

.date-nav:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.date-picker {
  font-family: inherit;
  font-size: 0.8rem;
  padding: 0.3rem 0.5rem;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-surface);
  color: var(--color-text);
  cursor: pointer;
  outline: none;
  transition: border-color 0.15s;
}

.date-picker:focus {
  border-color: var(--color-info);
}

/* ── Weather bar ──────────────────────────────────────────────────────── */

.weather-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1rem;
  padding: 0.5rem 0.75rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.weather-item:first-child {
  font-weight: 600;
  font-size: 0.85rem;
  color: var(--color-text);
}

.weather-item--desc {
  font-style: italic;
}

/* ── Camera grid ──────────────────────────────────────────────────────── */

.camera-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 0.75rem;
}

/* ── Status / Footer ──────────────────────────────────────────────────── */

.reolink-status {
  text-align: center;
  padding: 2rem 1rem;
  color: var(--color-text-muted);
  font-size: 0.9rem;
}

.reolink-status--error {
  color: var(--color-danger);
}

.section-footer {
  text-align: center;
  font-size: 0.7rem;
  color: var(--color-text-muted);
  padding-top: 0.25rem;
}
</style>

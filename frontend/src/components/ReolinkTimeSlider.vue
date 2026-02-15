<script setup lang="ts">
import { computed, ref } from 'vue'
import { useReolinkStore } from '@/stores/reolink'

const store = useReolinkStore()

const ALL_HOURS = Array.from({ length: 24 }, (_, i) => i)

/** Format hour as 12-hour label: "12a", "3a", "6a", "12p", etc. */
function shortLabel(h: number): string {
  if (h === 0) return '12a'
  if (h === 12) return '12p'
  return h < 12 ? `${h}a` : `${h - 12}p`
}

/** Format hour for the current-time display: "2:00 PM" */
function fullLabel(h: number): string {
  const suffix = h >= 12 ? 'PM' : 'AM'
  const h12 = h === 0 ? 12 : h > 12 ? h - 12 : h
  return `${h12}:00 ${suffix}`
}

/** Whether this hour is a labeled tick (every 3 hours). */
function isLabeledTick(h: number): boolean {
  return h % 3 === 0
}

/** Whether a given hour has available data. */
function hasData(h: number): boolean {
  return store.availableHours.includes(h)
}

/** Percentage position for a given hour along the track. */
function pct(h: number): string {
  return `${(h / 23) * 100}%`
}

/** Thumb position as a percentage. */
const thumbPosition = computed(() => {
  if (store.selectedHour === null) return '0%'
  return pct(store.selectedHour)
})

/** Click on the track to jump to the nearest available hour. */
const trackRef = ref<HTMLDivElement | null>(null)

function onTrackClick(e: MouseEvent) {
  if (!trackRef.value || !store.availableHours.length) return
  const rect = trackRef.value.getBoundingClientRect()
  const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
  const targetHour = Math.round(ratio * 23)

  // Snap to nearest available hour
  const hours = store.availableHours
  let best: number = hours[0]!
  let bestDist = Math.abs(targetHour - best)
  for (const h of hours) {
    const dist = Math.abs(targetHour - h)
    if (dist < bestDist) {
      best = h
      bestDist = dist
    }
  }
  store.setHour(best)
}

/** Keyboard navigation on the track. */
function onKeydown(e: KeyboardEvent) {
  if (e.key === 'ArrowRight' || e.key === 'ArrowUp') {
    e.preventDefault()
    store.nextHour()
  } else if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') {
    e.preventDefault()
    store.prevHour()
  } else if (e.key === ' ') {
    e.preventDefault()
    store.togglePlay()
  }
}

/** Dragging state. */
const dragging = ref(false)

function onThumbDown(e: MouseEvent | TouchEvent) {
  e.preventDefault()
  dragging.value = true
  const moveHandler = (ev: MouseEvent | TouchEvent) => onDragMove(ev)
  const upHandler = () => {
    dragging.value = false
    window.removeEventListener('mousemove', moveHandler)
    window.removeEventListener('touchmove', moveHandler)
    window.removeEventListener('mouseup', upHandler)
    window.removeEventListener('touchend', upHandler)
  }
  window.addEventListener('mousemove', moveHandler)
  window.addEventListener('touchmove', moveHandler)
  window.addEventListener('mouseup', upHandler)
  window.addEventListener('touchend', upHandler)
}

function onDragMove(e: MouseEvent | TouchEvent) {
  if (!trackRef.value || !store.availableHours.length) return
  const clientX = 'touches' in e ? e.touches[0]!.clientX : e.clientX
  const rect = trackRef.value.getBoundingClientRect()
  const ratio = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width))
  const targetHour = Math.round(ratio * 23)

  const hours = store.availableHours
  let best: number = hours[0]!
  let bestDist = Math.abs(targetHour - best)
  for (const h of hours) {
    const dist = Math.abs(targetHour - h)
    if (dist < bestDist) {
      best = h
      bestDist = dist
    }
  }
  store.setHour(best)
}
</script>

<template>
  <div class="time-slider" :class="{ 'time-slider--disabled': !store.availableHours.length }">
    <!-- Current time display -->
    <div class="time-display" v-if="store.selectedHour !== null">
      {{ fullLabel(store.selectedHour) }}
    </div>

    <!-- Controls row -->
    <div class="slider-controls">
      <!-- Prev button -->
      <button
        class="slider-btn"
        @click="store.prevHour()"
        :disabled="!store.availableHours.length"
        title="Previous snapshot"
        aria-label="Previous snapshot"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
          <path d="M10.5 3L5.5 8l5 5" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>

      <!-- Track -->
      <div
        ref="trackRef"
        class="slider-track"
        tabindex="0"
        role="slider"
        :aria-valuenow="store.selectedHour ?? 0"
        aria-valuemin="0"
        aria-valuemax="23"
        :aria-valuetext="store.selectedHour !== null ? fullLabel(store.selectedHour) : 'No selection'"
        @click="onTrackClick"
        @keydown="onKeydown"
      >
        <!-- Day/night gradient background -->
        <div class="track-gradient"></div>

        <!-- Hour ticks -->
        <div class="track-ticks">
          <div
            v-for="h in ALL_HOURS"
            :key="h"
            class="tick"
            :class="{
              'tick--labeled': isLabeledTick(h),
              'tick--has-data': hasData(h),
            }"
            :style="{ left: pct(h) }"
          >
            <div class="tick-mark"></div>
            <span v-if="isLabeledTick(h)" class="tick-label">{{ shortLabel(h) }}</span>
          </div>
        </div>

        <!-- Availability dots -->
        <div class="track-dots">
          <div
            v-for="h in store.availableHours"
            :key="h"
            class="dot"
            :class="{ 'dot--active': h === store.selectedHour }"
            :style="{ left: pct(h) }"
          ></div>
        </div>

        <!-- Thumb -->
        <div
          v-if="store.selectedHour !== null"
          class="thumb"
          :class="{ 'thumb--dragging': dragging }"
          :style="{ left: thumbPosition }"
          @mousedown="onThumbDown"
          @touchstart="onThumbDown"
        ></div>
      </div>

      <!-- Next button -->
      <button
        class="slider-btn"
        @click="store.nextHour()"
        :disabled="!store.availableHours.length"
        title="Next snapshot"
        aria-label="Next snapshot"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
          <path d="M5.5 3l5 5-5 5" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>

      <!-- Play / Pause button -->
      <button
        class="slider-btn slider-btn--play"
        @click="store.togglePlay()"
        :disabled="!store.availableHours.length"
        :title="store.playing ? 'Pause' : 'Play through day'"
        :aria-label="store.playing ? 'Pause' : 'Play'"
      >
        <!-- Play icon -->
        <svg v-if="!store.playing" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
          <path d="M4 2.5v11l9-5.5z"/>
        </svg>
        <!-- Pause icon -->
        <svg v-else width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
          <rect x="3" y="2" width="3.5" height="12" rx="0.5"/>
          <rect x="9.5" y="2" width="3.5" height="12" rx="0.5"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.time-slider {
  user-select: none;
}

.time-slider--disabled {
  opacity: 0.4;
  pointer-events: none;
}

/* ── Current time display ─────────────────────────────────────────────── */

.time-display {
  text-align: center;
  font-size: 1.4rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: var(--color-heading);
  margin-bottom: 0.5rem;
  font-variant-numeric: tabular-nums;
}

/* ── Controls row ─────────────────────────────────────────────────────── */

.slider-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.slider-btn {
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
  flex-shrink: 0;
}

.slider-btn:hover:not(:disabled) {
  border-color: var(--color-border-hover);
  color: var(--color-text);
  background: var(--color-surface-elevated);
}

.slider-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.slider-btn--play {
  margin-left: 0.25rem;
}

/* ── Track ────────────────────────────────────────────────────────────── */

.slider-track {
  flex: 1;
  position: relative;
  height: 40px;
  cursor: pointer;
  outline: none;
  border-radius: 8px;
}

.slider-track:focus-visible {
  box-shadow: 0 0 0 2px var(--color-info);
  border-radius: 8px;
}

.track-gradient {
  position: absolute;
  top: 10px;
  left: 0;
  right: 0;
  height: 6px;
  border-radius: 3px;
  background: linear-gradient(
    to right,
    #1e293b 0%,       /* midnight — deep navy */
    #1e293b 15%,       /* 3:30am */
    #475569 22%,       /* 5am — pre-dawn */
    #f59e0b 28%,       /* 6:30am — sunrise gold */
    #93c5fd 38%,       /* 9am — morning blue */
    #bfdbfe 50%,       /* noon — bright sky */
    #93c5fd 62%,       /* 3pm — afternoon */
    #f59e0b 73%,       /* 5:30pm — sunset gold */
    #475569 80%,       /* 7pm — dusk */
    #1e293b 88%,       /* 9pm */
    #1e293b 100%       /* midnight */
  );
  opacity: 0.6;
}

/* ── Ticks ────────────────────────────────────────────────────────────── */

.track-ticks {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 100%;
}

.tick {
  position: absolute;
  transform: translateX(-50%);
}

.tick-mark {
  width: 1px;
  height: 8px;
  background: var(--color-border);
  margin: 6px auto 0;
}

.tick--labeled .tick-mark {
  height: 12px;
  background: var(--color-text-muted);
  margin-top: 3px;
}

.tick-label {
  display: block;
  font-size: 0.55rem;
  color: var(--color-text-muted);
  text-align: center;
  margin-top: 1px;
  font-variant-numeric: tabular-nums;
}

/* ── Availability dots ────────────────────────────────────────────────── */

.track-dots {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 100%;
  pointer-events: none;
}

.dot {
  position: absolute;
  top: 8px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-info);
  transform: translateX(-50%);
  opacity: 0.5;
  transition: all 0.2s;
}

.dot--active {
  opacity: 1;
  width: 8px;
  height: 8px;
  top: 7px;
  background: var(--color-info);
  box-shadow: 0 0 6px rgba(37, 99, 235, 0.5);
}

/* ── Thumb ────────────────────────────────────────────────────────────── */

.thumb {
  position: absolute;
  top: 4px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--color-info);
  border: 2px solid var(--color-surface-elevated);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);
  transform: translateX(-50%);
  cursor: grab;
  transition: transform 0.1s, box-shadow 0.15s;
  z-index: 2;
}

.thumb:hover {
  transform: translateX(-50%) scale(1.15);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
}

.thumb--dragging {
  cursor: grabbing;
  transform: translateX(-50%) scale(1.25);
  box-shadow: 0 2px 12px rgba(37, 99, 235, 0.4);
}
</style>

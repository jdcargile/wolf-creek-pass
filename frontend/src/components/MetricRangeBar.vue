<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  min: number
  max: number
  current: number
  unit: string
  precision: number
}>()

/** Format a value with the configured precision and unit. */
function fmt(val: number): string {
  return `${val.toFixed(props.precision)}${props.unit}`
}

/** Percentage position of the current value within the min–max range. */
const currentPct = computed(() => {
  if (props.min === props.max) return 50
  const pct = ((props.current - props.min) / (props.max - props.min)) * 100
  return Math.max(0, Math.min(100, pct))
})

/** Whether the range is meaningful (min !== max). */
const hasRange = computed(() => Math.abs(props.max - props.min) > 0.001)
</script>

<template>
  <div class="range-bar">
    <!-- Min label -->
    <span class="range-label range-label--min">{{ fmt(min) }}</span>

    <!-- Track -->
    <div class="range-track">
      <!-- Filled range -->
      <div class="range-fill"></div>

      <!-- Current value dot -->
      <div
        class="range-dot"
        :style="{ left: `${currentPct}%` }"
        :title="fmt(current)"
      >
        <!-- Current value tooltip -->
        <span class="range-current-label">{{ fmt(current) }}</span>
      </div>
    </div>

    <!-- Max label -->
    <span class="range-label range-label--max">{{ fmt(max) }}</span>
  </div>
</template>

<style scoped>
.range-bar {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  height: 24px;
}

/* ── Labels ───────────────────────────────────────────────────────────── */

.range-label {
  font-size: 0.65rem;
  color: var(--color-text-muted);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  min-width: 3.2rem;
}

.range-label--min {
  text-align: right;
}

.range-label--max {
  text-align: left;
}

/* ── Track ────────────────────────────────────────────────────────────── */

.range-track {
  flex: 1;
  position: relative;
  height: 6px;
  min-width: 60px;
}

.range-fill {
  position: absolute;
  inset: 0;
  border-radius: 3px;
  background: linear-gradient(
    to right,
    var(--color-info-bg) 0%,
    var(--color-info) 50%,
    var(--color-info-bg) 100%
  );
  opacity: 0.4;
}

/* ── Dot ──────────────────────────────────────────────────────────────── */

.range-dot {
  position: absolute;
  top: 50%;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--color-info);
  border: 1.5px solid var(--color-surface-elevated);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  transform: translate(-50%, -50%);
  z-index: 1;
}

.range-current-label {
  position: absolute;
  bottom: calc(100% + 4px);
  left: 50%;
  transform: translateX(-50%);
  font-size: 0.6rem;
  font-weight: 600;
  color: var(--color-text);
  white-space: nowrap;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.15s;
}

.range-bar:hover .range-current-label {
  opacity: 1;
}
</style>

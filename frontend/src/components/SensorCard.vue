<script setup lang="ts">
import { computed } from 'vue'
import type { SensorData, MetricConfig, SensorRanges, SensorCurrent } from '@/types/sensorpush'
import { METRIC_CONFIGS } from '@/types/sensorpush'
import MetricRangeBar from '@/components/MetricRangeBar.vue'

const props = defineProps<{
  sensor: SensorData
}>()

/** Look up a metric value from the current reading by key name. */
function readCurrent(key: keyof SensorRanges): number | undefined {
  const c = props.sensor.current
  if (!c) return undefined
  return c[key as keyof SensorCurrent] as number | undefined
}

/** Filter to only metrics this sensor actually reports. */
const availableMetrics = computed<MetricConfig[]>(() =>
  METRIC_CONFIGS.filter((m) => {
    const inRange =
      props.sensor.range_24h[m.key] !== undefined ||
      props.sensor.range_12h[m.key] !== undefined
    const inCurrent = readCurrent(m.key) !== undefined
    return inRange || inCurrent
  }),
)

/** Get the current value for a metric. */
function currentVal(metric: MetricConfig): number | null {
  const val = readCurrent(metric.key)
  return val !== undefined ? val : null
}

/** Format a current value with its unit. */
function fmtCurrent(metric: MetricConfig): string {
  const val = currentVal(metric)
  if (val === null) return '--'
  return `${val.toFixed(metric.precision)}${metric.unit}`
}

/** Format the primary current reading (temperature). */
const currentTemp = computed(() => {
  if (!props.sensor.current?.temperature) return null
  return Math.round(props.sensor.current.temperature)
})

/** Format the last-updated timestamp. */
const lastUpdated = computed(() => {
  if (!props.sensor.current?.timestamp) return ''
  const d = new Date(props.sensor.current.timestamp)
  return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
})
</script>

<template>
  <div class="sensor-card">
    <!-- Header -->
    <div class="card-header">
      <div class="card-name">{{ sensor.name }}</div>
      <div class="card-headline" v-if="currentTemp !== null">
        {{ currentTemp }}°F
      </div>
    </div>

    <!-- Metric groups — each metric has a header row, then stacked 12h/24h bars -->
    <div class="metric-list" v-if="availableMetrics.length">
      <div
        v-for="metric in availableMetrics"
        :key="metric.key"
        class="metric-group"
      >
        <!-- Metric header: label + current value -->
        <div class="metric-header">
          <span class="metric-label">{{ metric.label }}</span>
          <span class="metric-current">{{ fmtCurrent(metric) }}</span>
        </div>

        <!-- 12h bar -->
        <div class="metric-bar-row" v-if="sensor.range_12h[metric.key]">
          <span class="period-label">12h</span>
          <MetricRangeBar
            :min="sensor.range_12h[metric.key]!.min"
            :max="sensor.range_12h[metric.key]!.max"
            :current="currentVal(metric) ?? sensor.range_12h[metric.key]!.max"
            :unit="metric.unit"
            :precision="metric.precision"
          />
        </div>

        <!-- 24h bar -->
        <div class="metric-bar-row" v-if="sensor.range_24h[metric.key]">
          <span class="period-label">24h</span>
          <MetricRangeBar
            :min="sensor.range_24h[metric.key]!.min"
            :max="sensor.range_24h[metric.key]!.max"
            :current="currentVal(metric) ?? sensor.range_24h[metric.key]!.max"
            :unit="metric.unit"
            :precision="metric.precision"
          />
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div class="card-footer">
      <span v-if="lastUpdated">Updated {{ lastUpdated }}</span>
      <span>{{ sensor.reading_count }} readings</span>
    </div>
  </div>
</template>

<style scoped>
.sensor-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 0.85rem;
  transition: transform 0.15s, box-shadow 0.15s;
}

.sensor-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

/* ── Header ───────────────────────────────────────────────────────────── */

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 0.65rem;
}

.card-name {
  font-weight: 600;
  font-size: 0.9rem;
}

.card-headline {
  font-size: 1.4rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

/* ── Metric list ──────────────────────────────────────────────────────── */

.metric-list {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.metric-group {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

/* Metric header: label on left, current value on right */
.metric-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.metric-label {
  font-size: 0.7rem;
  color: var(--color-text-muted);
  font-weight: 500;
}

.metric-current {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--color-text);
  font-variant-numeric: tabular-nums;
}

/* Bar row: period label + full-width range bar */
.metric-bar-row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.period-label {
  font-size: 0.55rem;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  width: 1.8rem;
  flex-shrink: 0;
  text-align: right;
}

/* ── Footer ───────────────────────────────────────────────────────────── */

.card-footer {
  display: flex;
  justify-content: space-between;
  margin-top: 0.65rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--color-border);
  font-size: 0.65rem;
  color: var(--color-text-muted);
}
</style>

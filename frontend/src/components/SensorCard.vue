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
  // Keys on SensorCurrent match SensorRanges (temperature, humidity, …)
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

    <!-- Metric rows with 12h / 24h range bars -->
    <div class="metric-table" v-if="availableMetrics.length">
      <!-- Column headers -->
      <div class="metric-row metric-row--header">
        <span class="metric-label"></span>
        <span class="metric-period">12h</span>
        <span class="metric-period">24h</span>
      </div>

      <div
        v-for="metric in availableMetrics"
        :key="metric.key"
        class="metric-row"
      >
        <span class="metric-label">{{ metric.label }}</span>

        <!-- 12h range bar -->
        <div class="metric-bar">
          <MetricRangeBar
            v-if="sensor.range_12h[metric.key]"
            :min="sensor.range_12h[metric.key]!.min"
            :max="sensor.range_12h[metric.key]!.max"
            :current="currentVal(metric) ?? sensor.range_12h[metric.key]!.max"
            :unit="metric.unit"
            :precision="metric.precision"
          />
          <span v-else class="metric-na">--</span>
        </div>

        <!-- 24h range bar -->
        <div class="metric-bar">
          <MetricRangeBar
            v-if="sensor.range_24h[metric.key]"
            :min="sensor.range_24h[metric.key]!.min"
            :max="sensor.range_24h[metric.key]!.max"
            :current="currentVal(metric) ?? sensor.range_24h[metric.key]!.max"
            :unit="metric.unit"
            :precision="metric.precision"
          />
          <span v-else class="metric-na">--</span>
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

/* ── Metric table ─────────────────────────────────────────────────────── */

.metric-table {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.metric-row {
  display: grid;
  grid-template-columns: 5.5rem 1fr 1fr;
  align-items: center;
  gap: 0.5rem;
}

.metric-row--header {
  margin-bottom: 0.1rem;
}

.metric-label {
  font-size: 0.7rem;
  color: var(--color-text-muted);
  font-weight: 500;
}

.metric-period {
  font-size: 0.6rem;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  text-align: center;
}

.metric-bar {
  min-width: 0;
}

.metric-na {
  font-size: 0.65rem;
  color: var(--color-text-muted);
  text-align: center;
  display: block;
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

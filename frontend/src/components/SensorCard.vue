<script setup lang="ts">
import { computed } from 'vue'
import type { SensorData, SensorAverages, MetricConfig, SensorRanges, SensorCurrent, SensorTimeSeries } from '@/types/sensorpush'
import { METRIC_CONFIGS } from '@/types/sensorpush'
import MetricRangeBar from '@/components/MetricRangeBar.vue'
import SparklineChart from '@/components/SparklineChart.vue'
import { formatTime } from '@/utils/time'

const props = defineProps<{
  sensor: SensorData
  loadingHistory?: boolean
}>()

/** Look up a metric value from the current reading by key name. */
function readCurrent(key: keyof SensorRanges): number | undefined {
  const c = props.sensor.current
  if (!c) return undefined
  return c[key as keyof SensorCurrent] as number | undefined
}

/** Whether range/chart data has been populated (history loaded). */
const hasHistory = computed(() => {
  return Object.keys(props.sensor.range_24h).length > 0
    || Object.keys(props.sensor.range_12h).length > 0
})

/**
 * Filter to only metrics this sensor actually reports.
 * During summary-only phase, use current readings to determine which metrics exist.
 * Once history arrives, also include metrics that have range data.
 */
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

/** Check if a metric has time series data for charting. */
function hasTimeSeries(metric: MetricConfig): boolean {
  const series = props.sensor.time_series?.[metric.key as keyof SensorTimeSeries]
  return !!series && series.length >= 2
}

/** Format the primary current reading (temperature) with 1 decimal. */
const currentTemp = computed(() => {
  const t = props.sensor.current?.temperature
  if (t == null) return null
  return t.toFixed(1)
})

/** Format the last-updated timestamp in Mountain Time. */
const lastUpdated = computed(() => {
  if (!props.sensor.current?.timestamp) return ''
  return formatTime(props.sensor.current.timestamp)
})

/**
 * Build a compact daily average string: "74°F / 39%" or "65°F / 51% / 23.0in".
 * Only includes metrics this sensor actually has averages for.
 * Order follows METRIC_CONFIGS but only temp, humidity, pressure for brevity.
 */
const dailyAvg = computed(() => {
  const avg = props.sensor.avg_24h
  if (!avg) return ''

  const parts: string[] = []
  // Show only the 3 key metrics in the compact header line
  const show: { key: keyof SensorAverages; unit: string; precision: number }[] = [
    { key: 'temperature', unit: '°F', precision: 0 },
    { key: 'humidity', unit: '%', precision: 0 },
    { key: 'barometric_pressure', unit: 'in', precision: 1 },
  ]
  for (const { key, unit, precision } of show) {
    const val = avg[key]
    if (val != null) {
      parts.push(`${val.toFixed(precision)}${unit}`)
    }
  }
  return parts.join(' / ')
})
</script>

<template>
  <div class="sensor-card">
    <!-- Header -->
    <div class="card-header">
      <div class="card-header-left">
        <div class="card-name">{{ sensor.name }}</div>
        <div class="card-meta" v-if="lastUpdated">Last reading: {{ lastUpdated }}</div>
      </div>
      <div class="card-header-right">
        <div class="card-headline" v-if="currentTemp !== null">
          {{ currentTemp }}°F
        </div>
        <div class="card-meta" v-if="dailyAvg">Daily Avg: {{ dailyAvg }}</div>
        <div class="card-meta shimmer-text" v-else-if="loadingHistory">Daily Avg: ---</div>
      </div>
    </div>

    <!-- Metric groups — each metric has a header row, range bars, and chart -->
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

        <!-- History loaded: show range bars + charts -->
        <template v-if="hasHistory">
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

          <!-- 7-day sparkline chart -->
          <div
            class="metric-chart"
            v-if="hasTimeSeries(metric)"
          >
            <span class="period-label chart-label">7d</span>
            <SparklineChart
              :data="sensor.time_series[metric.key as keyof SensorTimeSeries]!"
              :color="metric.color"
              :unit="metric.unit"
              :precision="metric.precision"
            />
          </div>
        </template>

        <!-- History loading: skeleton placeholders -->
        <template v-else-if="loadingHistory">
          <div class="metric-bar-row">
            <span class="period-label">12h</span>
            <div class="skeleton skeleton-bar"></div>
          </div>
          <div class="metric-bar-row">
            <span class="period-label">24h</span>
            <div class="skeleton skeleton-bar"></div>
          </div>
          <div class="metric-chart">
            <span class="period-label chart-label">7d</span>
            <div class="skeleton skeleton-chart"></div>
          </div>
        </template>
      </div>
    </div>

    <!-- Footer -->
    <div class="card-footer">
      <span v-if="hasHistory">{{ sensor.reading_count }} readings (7d)</span>
      <span v-else-if="loadingHistory" class="shimmer-text">Loading history...</span>
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
  align-items: flex-start;
  margin-bottom: 0.65rem;
}

.card-header-left {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}

.card-header-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.1rem;
}

.card-name {
  font-weight: 600;
  font-size: 0.9rem;
}

.card-meta {
  font-size: 0.65rem;
  color: var(--color-text-muted);
  font-variant-numeric: tabular-nums;
}

.card-headline {
  font-size: 1.4rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  line-height: 1;
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

/* Chart row: same layout as bar rows */
.metric-chart {
  display: flex;
  align-items: flex-start;
  gap: 0.4rem;
  margin-top: 0.15rem;
}

.chart-label {
  padding-top: 0.2rem;
}

/* ── Skeleton loading placeholders ─────────────────────────────────────── */

.skeleton {
  background: linear-gradient(90deg, var(--color-border) 25%, transparent 50%, var(--color-border) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 4px;
}

.skeleton-bar {
  height: 12px;
  flex: 1;
}

.skeleton-chart {
  height: 40px;
  flex: 1;
}

.shimmer-text {
  animation: shimmer-opacity 1.5s infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@keyframes shimmer-opacity {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
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

<script setup lang="ts">
/**
 * SparklineChart — lightweight SVG sparkline with area fill.
 *
 * Renders a time series as a smooth SVG path with optional area fill.
 * No external charting library required.
 */
import { computed, ref } from 'vue'
import type { TimeSeriesPoint } from '@/types/sensorpush'
import { formatShortDate, formatDateTime } from '@/utils/time'

const props = defineProps<{
  /** Array of [iso_timestamp, value] points, sorted chronologically. */
  data: TimeSeriesPoint[]
  /** CSS color for the line and area fill. */
  color: string
  /** Unit suffix for tooltip display. */
  unit: string
  /** Decimal precision for tooltip values. */
  precision: number
  /** Chart height in pixels. */
  height?: number
}>()

const chartHeight = computed(() => props.height ?? 64)
const chartWidth = 320
const padding = { top: 4, right: 4, bottom: 16, left: 4 }

const plotW = chartWidth - padding.left - padding.right
const plotH = computed(() => chartHeight.value - padding.top - padding.bottom)

/** Parse timestamps to numeric epoch for x-axis scaling. */
const parsed = computed(() =>
  props.data.map(([ts, val]) => ({
    t: new Date(ts).getTime(),
    v: val,
    ts,
  })),
)

const xMin = computed(() => (parsed.value.length ? parsed.value[0]!.t : 0))
const xMax = computed(() => (parsed.value.length ? parsed.value[parsed.value.length - 1]!.t : 1))
const yMin = computed(() => {
  if (!parsed.value.length) return 0
  return Math.min(...parsed.value.map((p) => p.v))
})
const yMax = computed(() => {
  if (!parsed.value.length) return 1
  return Math.max(...parsed.value.map((p) => p.v))
})

/** Map a data point to SVG coordinates. */
function toSvg(t: number, v: number): { x: number; y: number } {
  const xRange = xMax.value - xMin.value || 1
  const yRange = yMax.value - yMin.value || 1
  return {
    x: padding.left + ((t - xMin.value) / xRange) * plotW,
    y: padding.top + plotH.value - ((v - yMin.value) / yRange) * plotH.value,
  }
}

/** SVG path for the line. */
const linePath = computed(() => {
  if (parsed.value.length < 2) return ''
  return parsed.value
    .map((p, i) => {
      const { x, y } = toSvg(p.t, p.v)
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
})

/** SVG path for the area fill (line + close to bottom). */
const areaPath = computed(() => {
  if (parsed.value.length < 2) return ''
  const bottomY = padding.top + plotH.value
  const first = toSvg(parsed.value[0]!.t, parsed.value[0]!.v)
  const last = toSvg(
    parsed.value[parsed.value.length - 1]!.t,
    parsed.value[parsed.value.length - 1]!.v,
  )
  return `${linePath.value} L${last.x.toFixed(1)},${bottomY} L${first.x.toFixed(1)},${bottomY} Z`
})

/** X-axis date labels (show ~3-5 evenly spaced dates). */
const xLabels = computed(() => {
  if (parsed.value.length < 2) return []
  const count = 5
  const step = (parsed.value.length - 1) / (count - 1)
  const labels: { x: number; text: string }[] = []
  for (let i = 0; i < count; i++) {
    const idx = Math.round(i * step)
    const p = parsed.value[idx]!
    const { x } = toSvg(p.t, p.v)
    labels.push({ x, text: formatShortDate(p.ts) })
  }
  return labels
})

/** Tooltip state. */
const hoverIdx = ref<number | null>(null)
const hoverX = ref(0)
const hoverY = ref(0)

const tooltipText = computed(() => {
  if (hoverIdx.value === null) return ''
  const p = parsed.value[hoverIdx.value]!
  const time = formatDateTime(p.ts)
  return `${p.v.toFixed(props.precision)}${props.unit} — ${time}`
})

function onMouseMove(event: MouseEvent) {
  const svg = (event.currentTarget as SVGSVGElement)
  const rect = svg.getBoundingClientRect()
  const mouseX = event.clientX - rect.left
  // Find nearest point
  let closest = 0
  let closestDist = Infinity
  for (let i = 0; i < parsed.value.length; i++) {
    const { x } = toSvg(parsed.value[i]!.t, parsed.value[i]!.v)
    const dist = Math.abs(x - mouseX)
    if (dist < closestDist) {
      closestDist = dist
      closest = i
    }
  }
  hoverIdx.value = closest
  const pt = toSvg(parsed.value[closest]!.t, parsed.value[closest]!.v)
  hoverX.value = pt.x
  hoverY.value = pt.y
}

function onMouseLeave() {
  hoverIdx.value = null
}
</script>

<template>
  <div class="sparkline-container">
    <svg
      :width="chartWidth"
      :height="chartHeight"
      :viewBox="`0 0 ${chartWidth} ${chartHeight}`"
      class="sparkline-svg"
      @mousemove="onMouseMove"
      @mouseleave="onMouseLeave"
    >
      <!-- Area fill -->
      <path
        v-if="areaPath"
        :d="areaPath"
        :fill="color"
        fill-opacity="0.1"
      />
      <!-- Line -->
      <path
        v-if="linePath"
        :d="linePath"
        :stroke="color"
        stroke-width="1.5"
        fill="none"
        stroke-linejoin="round"
        stroke-linecap="round"
      />
      <!-- X-axis labels -->
      <text
        v-for="(label, i) in xLabels"
        :key="i"
        :x="label.x"
        :y="chartHeight - 2"
        class="sparkline-x-label"
        text-anchor="middle"
      >
        {{ label.text }}
      </text>
      <!-- Hover crosshair + dot -->
      <template v-if="hoverIdx !== null">
        <line
          :x1="hoverX"
          :y1="padding.top"
          :x2="hoverX"
          :y2="padding.top + plotH"
          stroke="currentColor"
          stroke-opacity="0.2"
          stroke-width="1"
          stroke-dasharray="2,2"
        />
        <circle
          :cx="hoverX"
          :cy="hoverY"
          r="3"
          :fill="color"
          stroke="var(--color-surface)"
          stroke-width="1.5"
        />
      </template>
    </svg>
    <!-- Tooltip -->
    <div
      v-if="hoverIdx !== null"
      class="sparkline-tooltip"
      :style="{ left: `${hoverX}px` }"
    >
      {{ tooltipText }}
    </div>
  </div>
</template>

<style scoped>
.sparkline-container {
  position: relative;
  width: 100%;
  max-width: 320px;
}

.sparkline-svg {
  width: 100%;
  height: auto;
  display: block;
  cursor: crosshair;
}

.sparkline-x-label {
  font-size: 8px;
  fill: var(--color-text-muted);
  user-select: none;
}

.sparkline-tooltip {
  position: absolute;
  top: -24px;
  transform: translateX(-50%);
  background: var(--color-surface-elevated, #1a1a1a);
  color: var(--color-text);
  font-size: 0.6rem;
  font-variant-numeric: tabular-nums;
  padding: 2px 6px;
  border-radius: 4px;
  white-space: nowrap;
  pointer-events: none;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);
  z-index: 10;
}
</style>

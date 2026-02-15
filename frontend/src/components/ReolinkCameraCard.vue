<script setup lang="ts">
import { computed } from 'vue'
import type { ReolinkCamera, ReolinkSnapshot } from '@/types/reolink'

const props = defineProps<{
  camera: ReolinkCamera
  snapshot: ReolinkSnapshot | null
}>()

/** Map detection labels to color classes. */
const LABEL_COLORS: Record<string, string> = {
  person: 'badge--person',
  car: 'badge--vehicle',
  truck: 'badge--vehicle',
  bus: 'badge--vehicle',
  motorcycle: 'badge--vehicle',
  bicycle: 'badge--vehicle',
  dog: 'badge--animal',
  cat: 'badge--animal',
  bird: 'badge--animal',
  bear: 'badge--animal',
  deer: 'badge--animal',
  horse: 'badge--animal',
  cow: 'badge--animal',
  sheep: 'badge--animal',
  elk: 'badge--animal',
}

function badgeClass(label: string): string {
  return LABEL_COLORS[label.toLowerCase()] || 'badge--other'
}

/** Format confidence as a percentage. */
function fmtConf(c: number): string {
  return `${Math.round(c * 100)}%`
}

import { formatTime } from '@/utils/time'

/** Format the snapshot timestamp as a short time string in Mountain Time. */
const timeLabel = computed(() => {
  if (!props.snapshot) return ''
  return formatTime(props.snapshot.timestamp)
})

/** Total snapshot count for this camera. */
const snapshotCount = computed(() => props.camera.snapshots.length)
</script>

<template>
  <div class="reolink-card" :class="{ 'reolink-card--empty': !snapshot }">
    <!-- Image area -->
    <div class="card-image">
      <img
        v-if="snapshot?.image_url"
        :src="snapshot.image_url"
        :alt="`${camera.name} at ${timeLabel}`"
        loading="lazy"
      />
      <div v-else class="image-placeholder">
        <span>No snapshot</span>
      </div>

      <!-- Detection badges overlay -->
      <div v-if="snapshot?.detections?.length" class="badge-overlay">
        <span
          v-for="(det, i) in snapshot.detections"
          :key="i"
          class="det-badge"
          :class="badgeClass(det.label)"
        >
          {{ det.label }} {{ fmtConf(det.confidence) }}
        </span>
      </div>
    </div>

    <!-- Info bar -->
    <div class="card-info">
      <div class="card-name">{{ camera.name }}</div>
      <div class="card-meta">
        <span v-if="timeLabel" class="card-time">{{ timeLabel }}</span>
        <span class="card-count">{{ snapshotCount }} today</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.reolink-card {
  background: var(--color-surface);
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--color-border);
  transition: transform 0.15s, box-shadow 0.15s;
}

.reolink-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.reolink-card--empty {
  opacity: 0.6;
}

/* ── Image ────────────────────────────────────────────────────────────── */

.card-image {
  position: relative;
  overflow: hidden;
}

.card-image img {
  width: 100%;
  height: 190px;
  object-fit: cover;
  display: block;
  transition: opacity 0.3s ease;
}

.image-placeholder {
  width: 100%;
  height: 190px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface-elevated);
  color: var(--color-text-muted);
  font-size: 0.8rem;
}

/* ── Detection badge overlay ──────────────────────────────────────────── */

.badge-overlay {
  position: absolute;
  bottom: 6px;
  left: 6px;
  right: 6px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.det-badge {
  font-size: 0.6rem;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  line-height: 1.3;
}

.badge--person {
  background: rgba(59, 130, 246, 0.85);
  color: #fff;
}

.badge--vehicle {
  background: rgba(16, 185, 129, 0.85);
  color: #fff;
}

.badge--animal {
  background: rgba(245, 158, 11, 0.85);
  color: #fff;
}

.badge--other {
  background: rgba(107, 114, 128, 0.85);
  color: #fff;
}

/* ── Info bar ─────────────────────────────────────────────────────────── */

.card-info {
  padding: 0.6rem 0.75rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-name {
  font-weight: 600;
  font-size: 0.85rem;
}

.card-meta {
  display: flex;
  gap: 0.5rem;
  font-size: 0.7rem;
  color: var(--color-text-muted);
}

.card-time {
  font-variant-numeric: tabular-nums;
}

.card-count {
  opacity: 0.7;
}
</style>

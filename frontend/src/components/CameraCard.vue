<script setup lang="ts">
import type { CaptureRecord } from '@/types'

defineProps<{
  capture: CaptureRecord
}>()

const emit = defineEmits<{
  click: []
}>()
</script>

<template>
  <div class="camera-card" :class="{ 'camera-card--snow': capture.has_snow }" @click="emit('click')" style="cursor: pointer">
    <div class="camera-image">
      <img
        v-if="capture.image_url"
        :src="capture.image_url"
        :alt="`Camera ${capture.camera_id} - ${capture.location}`"
        loading="lazy"
      />
      <div v-else class="camera-image-placeholder">No Image</div>
      <!-- Floating snow/animal badge on image -->
      <span v-if="capture.has_snow" class="camera-floating-badge camera-floating-badge--snow">❄️</span>
      <span v-else-if="capture.has_animal" class="camera-floating-badge camera-floating-badge--animal">🦌</span>
    </div>
    <div class="camera-info">
      <div class="camera-location">
        {{ capture.location || 'Unknown' }}
      </div>
      <div class="camera-road">
        {{ capture.roadway }} {{ capture.direction }}
      </div>
      <div class="camera-badges">
        <span v-if="capture.has_snow" class="cam-badge cam-badge--danger">Snow</span>
        <span v-if="capture.has_car" class="cam-badge cam-badge--info">Cars</span>
        <span v-if="capture.has_truck" class="cam-badge cam-badge--info">Trucks</span>
        <span v-if="capture.has_animal" class="cam-badge cam-badge--warning">Animals</span>
        <span v-if="!capture.has_snow && !capture.has_car && !capture.has_truck && !capture.has_animal" class="cam-badge cam-badge--clear">Clear</span>
      </div>
      <div class="camera-notes" v-if="capture.analysis_notes">
        {{ capture.analysis_notes }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.camera-card {
  background: var(--color-surface);
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--color-border);
  transition: transform 0.15s, box-shadow 0.15s;
}

.camera-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.camera-card--snow {
  border-color: var(--color-danger);
  box-shadow: 0 0 0 1px var(--color-danger);
}

.camera-image {
  position: relative;
}

.camera-image img {
  width: 100%;
  height: 170px;
  object-fit: cover;
  display: block;
}

.camera-image-placeholder {
  width: 100%;
  height: 170px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f3f4f6;
  color: #9ca3af;
  font-size: 0.9rem;
}

.camera-floating-badge {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  font-size: 1.5rem;
  filter: drop-shadow(0 1px 3px rgba(0, 0, 0, 0.4));
  animation: pulse-badge 2s ease-in-out infinite;
}

@keyframes pulse-badge {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.15); }
}

.camera-info {
  padding: 0.75rem;
}

.camera-location {
  font-weight: 600;
  font-size: 0.9rem;
  margin-bottom: 0.15rem;
}

.camera-road {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  margin-bottom: 0.5rem;
}

.camera-badges {
  display: flex;
  gap: 0.35rem;
  flex-wrap: wrap;
  margin-bottom: 0.4rem;
}

.cam-badge {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border-radius: 6px;
  font-size: 0.7rem;
  font-weight: 600;
}

.cam-badge--danger {
  background: #fee2e2;
  color: #dc2626;
}

.cam-badge--warning {
  background: #fef9c3;
  color: #ca8a04;
}

.cam-badge--info {
  background: #dbeafe;
  color: #2563eb;
}

.cam-badge--clear {
  background: #dcfce7;
  color: #16a34a;
}

.camera-notes {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  line-height: 1.3;
}
</style>

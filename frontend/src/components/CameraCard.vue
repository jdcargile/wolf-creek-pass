<script setup lang="ts">
import type { CaptureRecord } from '@/types'
import ConditionBadge from './ConditionBadge.vue'

defineProps<{
  capture: CaptureRecord
}>()
</script>

<template>
  <div class="camera-card" :class="{ 'camera-card--snow': capture.has_snow }">
    <div class="camera-image">
      <img
        v-if="capture.image_url"
        :src="capture.image_url"
        :alt="`Camera ${capture.camera_id} - ${capture.location}`"
        loading="lazy"
      />
      <div v-else class="camera-image-placeholder">No Image</div>
    </div>
    <div class="camera-info">
      <div class="camera-location">
        {{ capture.location || 'Unknown' }}
      </div>
      <div class="camera-road">
        {{ capture.roadway }} {{ capture.direction }}
      </div>
      <div class="camera-badges">
        <ConditionBadge label="Snow" :active="capture.has_snow" variant="danger" />
        <ConditionBadge label="Cars" :active="capture.has_car" variant="info" />
        <ConditionBadge label="Trucks" :active="capture.has_truck" variant="info" />
        <ConditionBadge label="Animals" :active="capture.has_animal" variant="warning" />
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
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--color-border);
  transition: box-shadow 0.2s;
}

.camera-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.camera-card--snow {
  border-color: var(--color-danger);
}

.camera-image img {
  width: 100%;
  height: 160px;
  object-fit: cover;
  display: block;
}

.camera-image-placeholder {
  width: 100%;
  height: 160px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f3f4f6;
  color: #9ca3af;
  font-size: 0.85rem;
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

.camera-notes {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  line-height: 1.3;
}
</style>

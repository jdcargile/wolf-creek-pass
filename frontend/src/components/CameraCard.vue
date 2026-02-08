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
  <div class="camera-card" @click="emit('click')" style="cursor: pointer">
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
}
</style>

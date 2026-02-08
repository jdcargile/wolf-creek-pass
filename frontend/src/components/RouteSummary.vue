<script setup lang="ts">
import { useCycleStore } from '@/stores/cycle'

const store = useCycleStore()
</script>

<template>
  <div class="route-summary" v-if="store.hasData">
    <div class="stat">
      <span class="stat-value">{{ store.distanceMiles }}</span>
      <span class="stat-label">miles</span>
    </div>
    <div class="stat">
      <span class="stat-value">{{ store.travelTimeMin ?? '--' }}</span>
      <span class="stat-label">min drive</span>
    </div>
    <div class="stat">
      <span class="stat-value">{{ store.cameraCount }}</span>
      <span class="stat-label">cameras</span>
    </div>
    <div class="stat" :class="{ 'stat-danger': store.snowCount > 0 }">
      <span class="stat-value">{{ store.snowCount }}</span>
      <span class="stat-label">snow</span>
    </div>
    <div class="stat" v-if="store.currentCycle?.events.length">
      <span class="stat-value">{{ store.currentCycle.events.length }}</span>
      <span class="stat-label">events</span>
    </div>
  </div>
</template>

<style scoped>
.route-summary {
  display: flex;
  gap: 1rem;
  padding: 0.75rem 1rem;
  background: var(--color-surface);
  border-radius: 8px;
  overflow-x: auto;
  flex-wrap: wrap;
}

.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 60px;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-text);
}

.stat-label {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-danger .stat-value {
  color: var(--color-danger);
}
</style>

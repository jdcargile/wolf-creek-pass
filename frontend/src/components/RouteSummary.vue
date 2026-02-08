<script setup lang="ts">
import { useCycleStore } from '@/stores/cycle'

const store = useCycleStore()
</script>

<template>
  <div class="route-summary" v-if="store.hasData">
    <!-- Wolf Creek status badge -->
    <div class="stat" v-if="store.wolfCreekPass">
      <span
        class="stat-value stat-badge"
        :class="store.wolfCreekClosed ? 'stat-badge--closed' : 'stat-badge--open'"
      >
        {{ store.wolfCreekClosed ? 'CLOSED' : 'OPEN' }}
      </span>
      <span class="stat-label">wolf creek</span>
    </div>
    <div class="stat" v-if="store.wolfCreekPass?.air_temperature">
      <span class="stat-value">{{ store.wolfCreekPass.air_temperature }}&deg;</span>
      <span class="stat-label">pass temp</span>
    </div>
    <div class="stat" v-if="store.selectedRoute">
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
    <div class="stat" v-if="store.plowCount > 0">
      <span class="stat-value stat-plow">{{ store.plowCount }}</span>
      <span class="stat-label">plows</span>
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

.stat-badge {
  font-size: 0.85rem;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  letter-spacing: 0.05em;
}

.stat-badge--open {
  background: #dcfce7;
  color: #16a34a;
}

.stat-badge--closed {
  background: #fee2e2;
  color: #dc2626;
}

.stat-plow {
  color: #d97706;
}
</style>

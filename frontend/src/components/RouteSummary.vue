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
      <span class="stat-value">{{ store.wolfCreekPass.air_temperature }}°</span>
      <span class="stat-label">pass temp</span>
    </div>
    <div class="stat" v-if="store.selectedRoute">
      <span class="stat-value">{{ store.distanceDisplay || store.distanceMiles + ' mi' }}</span>
      <span class="stat-label">distance</span>
    </div>
    <div class="stat">
      <span class="stat-value">{{ store.travelTimeDisplay || (store.travelTimeMin ? store.travelTimeMin + 'm' : '--') }}</span>
      <span class="stat-label">drive time</span>
    </div>
    <div class="stat">
      <span class="stat-value">{{ store.cameraCount }}</span>
      <span class="stat-label">cameras</span>
    </div>
    <div class="stat" :class="{ 'stat-danger': store.snowCount > 0 }">
      <span class="stat-value">{{ store.snowCount }}</span>
      <span class="stat-label">{{ store.snowCount > 0 ? 'snow!' : 'clear' }}</span>
    </div>
    <div class="stat" v-if="store.plowCount > 0">
      <span class="stat-value stat-plow">{{ store.plowCount }}</span>
      <span class="stat-label">plows out</span>
    </div>
  </div>
</template>

<style scoped>
.route-summary {
  display: flex;
  gap: 0.75rem;
  padding: 0.85rem 1rem;
  background: var(--color-surface);
  border-radius: 12px;
  overflow-x: auto;
  flex-wrap: wrap;
  border: 1px solid var(--color-border);
}

.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 70px;
  padding: 0.25rem 0.5rem;
  border-radius: 8px;
  transition: background 0.15s;
}

.stat:hover {
  background: rgba(0, 0, 0, 0.03);
}

.stat-value {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--color-text);
  white-space: nowrap;
}

.stat-label {
  font-size: 0.65rem;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-top: 0.1rem;
}

.stat-danger .stat-value {
  color: var(--color-danger);
}

.stat-badge {
  font-size: 0.85rem;
  padding: 0.15rem 0.5rem;
  border-radius: 6px;
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

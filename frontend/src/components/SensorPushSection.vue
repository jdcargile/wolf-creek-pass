<script setup lang="ts">
import { onMounted } from 'vue'
import { useSensorPushStore } from '@/stores/sensorpush'
import SensorCard from '@/components/SensorCard.vue'

const store = useSensorPushStore()

onMounted(async () => {
  // Phase 1: fast summary (current readings, ~3s)
  await store.loadSummary()
  // Phase 2: full 7-day history (charts + ranges, slow but cached on backend)
  store.loadHistory()
})
</script>

<template>
  <section class="sensorpush-section">
    <h2>Cabin Sensors</h2>

    <!-- Loading (initial summary) -->
    <div v-if="store.loading" class="sp-status">Loading sensor data...</div>

    <!-- Error -->
    <div v-else-if="store.error" class="sp-status sp-status--error">
      {{ store.error }}
    </div>

    <!-- Content -->
    <template v-else-if="store.hasData">
      <div class="sensor-grid">
        <SensorCard
          v-for="sensor in store.sensors"
          :key="sensor.id"
          :sensor="sensor"
          :loading-history="store.loadingHistory"
        />
      </div>
    </template>

    <!-- No data -->
    <div v-else class="sp-status">
      No sensor data available.
    </div>
  </section>
</template>

<style scoped>
.sensorpush-section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.sensorpush-section h2 {
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0;
}

.sensor-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 0.75rem;
}

.sp-status {
  text-align: center;
  padding: 2rem 1rem;
  color: var(--color-text-muted);
  font-size: 0.9rem;
}

.sp-status--error {
  color: var(--color-danger);
}
</style>

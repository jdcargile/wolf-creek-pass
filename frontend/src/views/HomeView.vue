<script setup lang="ts">
import { onMounted } from 'vue'
import { useCycleStore } from '@/stores/cycle'
import RouteSummary from '@/components/RouteSummary.vue'
import CycleSelector from '@/components/CycleSelector.vue'
import RouteMap from '@/components/RouteMap.vue'
import CameraCard from '@/components/CameraCard.vue'

const store = useCycleStore()

onMounted(async () => {
  await Promise.all([store.loadLatest(), store.loadIndex()])
})
</script>

<template>
  <main class="dashboard">
    <!-- Header -->
    <header class="dashboard-header">
      <div class="header-top">
        <h1>Wolf Creek Pass</h1>
        <CycleSelector v-if="store.allCycles.length > 0" />
      </div>
      <p class="subtitle" v-if="store.primaryRoute">
        {{ store.primaryRoute.origin }} &rarr; {{ store.primaryRoute.destination }}
      </p>
    </header>

    <!-- Loading / Error -->
    <div v-if="store.loading" class="status-message">Loading...</div>
    <div v-else-if="store.error" class="status-message status-error">
      {{ store.error }}
      <p>Run <code>poe monitor:once</code> to generate data.</p>
    </div>

    <!-- Dashboard content -->
    <template v-else-if="store.hasData">
      <!-- Route summary bar -->
      <RouteSummary />

      <!-- Interactive map -->
      <RouteMap />

      <!-- Weather conditions -->
      <section v-if="store.currentCycle?.weather?.length" class="weather-section">
        <h2>Weather Stations</h2>
        <div class="weather-grid">
          <div
            v-for="w in store.currentCycle.weather"
            :key="w.id"
            class="weather-card"
          >
            <div class="weather-name">{{ w.station_name }}</div>
            <div class="weather-temp" v-if="w.air_temperature">
              {{ w.air_temperature }}&deg;F
            </div>
            <div class="weather-detail" v-if="w.surface_status">
              Surface: {{ w.surface_status }}
            </div>
            <div class="weather-detail" v-if="w.wind_speed_avg">
              Wind: {{ w.wind_speed_avg }} mph {{ w.wind_direction }}
            </div>
            <div class="weather-detail" v-if="w.precipitation">
              Precip: {{ w.precipitation }}
            </div>
          </div>
        </div>
      </section>

      <!-- Road conditions -->
      <section v-if="store.currentCycle?.conditions?.length" class="conditions-section">
        <h2>Road Conditions</h2>
        <div class="conditions-list">
          <div
            v-for="c in store.currentCycle.conditions"
            :key="c.id"
            class="condition-item"
            :class="{ 'condition-item--warn': c.road_condition.toLowerCase() !== 'dry' }"
          >
            <span class="condition-road">{{ c.roadway_name }}</span>
            <span class="condition-status">{{ c.road_condition }}</span>
            <span class="condition-weather" v-if="c.weather_condition">{{ c.weather_condition }}</span>
          </div>
        </div>
      </section>

      <!-- Camera grid -->
      <section class="cameras-section">
        <h2>Cameras ({{ store.currentCycle?.captures.length }})</h2>
        <div class="camera-grid">
          <CameraCard
            v-for="capture in store.currentCycle?.captures"
            :key="capture.camera_id"
            :capture="capture"
          />
        </div>
      </section>

      <!-- Events -->
      <section v-if="store.currentCycle?.events?.length" class="events-section">
        <h2>Traffic Events</h2>
        <div class="events-list">
          <div
            v-for="event in store.currentCycle.events"
            :key="event.id"
            class="event-item"
            :class="{ 'event-item--closure': event.is_full_closure }"
          >
            <span class="event-type">{{ event.event_type }}</span>
            <span class="event-road">{{ event.roadway_name }} {{ event.direction }}</span>
            <p class="event-desc">{{ event.description }}</p>
          </div>
        </div>
      </section>
    </template>

    <!-- No data -->
    <div v-else class="status-message">
      No data available. Run <code>poe monitor:once</code> to generate your first capture.
    </div>

    <!-- Footer -->
    <footer class="dashboard-footer">
      <span v-if="store.currentCycle">
        Last updated: {{ new Date(store.currentCycle.cycle.completed_at).toLocaleString() }}
      </span>
    </footer>
  </main>
</template>

<style scoped>
.dashboard {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.dashboard-header {
  margin-bottom: 0.5rem;
}

.header-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.75rem;
}

h1 {
  font-size: 1.5rem;
  font-weight: 700;
  margin: 0;
}

.subtitle {
  font-size: 0.85rem;
  color: var(--color-text-muted);
  margin: 0.25rem 0 0;
}

h2 {
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0 0 0.5rem;
}

.status-message {
  text-align: center;
  padding: 3rem 1rem;
  color: var(--color-text-muted);
  font-size: 1rem;
}

.status-error {
  color: var(--color-danger);
}

code {
  background: #f3f4f6;
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  font-size: 0.85rem;
}

/* Camera grid */
.camera-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 1rem;
}

/* Weather grid */
.weather-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 0.75rem;
}

.weather-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 0.75rem;
}

.weather-name {
  font-weight: 600;
  font-size: 0.85rem;
  margin-bottom: 0.25rem;
}

.weather-temp {
  font-size: 1.25rem;
  font-weight: 700;
}

.weather-detail {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

/* Road conditions */
.conditions-list {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.condition-item {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  padding: 0.5rem 0.75rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  font-size: 0.85rem;
}

.condition-item--warn {
  border-color: var(--color-danger);
  background: #fef2f2;
}

.condition-road {
  font-weight: 600;
  flex: 1;
}

.condition-status {
  font-weight: 500;
}

.condition-weather {
  color: var(--color-text-muted);
}

/* Events */
.events-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.event-item {
  padding: 0.75rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 6px;
}

.event-item--closure {
  border-color: var(--color-danger);
  background: #fef2f2;
}

.event-type {
  font-weight: 600;
  font-size: 0.85rem;
  text-transform: capitalize;
  margin-right: 0.5rem;
}

.event-road {
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

.event-desc {
  font-size: 0.8rem;
  margin: 0.25rem 0 0;
  color: var(--color-text-muted);
  line-height: 1.3;
}

/* Footer */
.dashboard-footer {
  text-align: center;
  padding: 1rem 0;
  font-size: 0.75rem;
  color: var(--color-text-muted);
}
</style>

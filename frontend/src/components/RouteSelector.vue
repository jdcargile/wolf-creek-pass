<script setup lang="ts">
import { useCycleStore } from '@/stores/cycle'

const store = useCycleStore()

function onSelect(event: globalThis.Event) {
  const target = event.target as HTMLSelectElement
  store.selectRoute(target.value || null)
}

function formatDuration(seconds: number): string {
  const hrs = Math.floor(seconds / 3600)
  const mins = Math.round((seconds % 3600) / 60)
  return hrs > 0 ? `${hrs}h ${mins}m` : `${mins}m`
}
</script>

<template>
  <div class="route-selector" v-if="store.routes.length > 0">
    <label for="route-select">Route:</label>
    <select id="route-select" @change="onSelect" :value="store.selectedRouteId ?? ''">
      <option
        v-for="route in store.routes"
        :key="route.route_id"
        :value="route.route_id"
      >
        {{ route.name }}
        <template v-if="route.duration_s">
          — {{ formatDuration(route.duration_in_traffic_s || route.duration_s) }}
        </template>
      </option>
    </select>
  </div>
</template>

<style scoped>
.route-selector {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

label {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-text-muted);
  white-space: nowrap;
}

select {
  padding: 0.4rem 0.6rem;
  border-radius: 6px;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 0.85rem;
  min-width: 200px;
  max-width: 100%;
}
</style>

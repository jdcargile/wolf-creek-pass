<script setup lang="ts">
import { useCycleStore } from '@/stores/cycle'

const store = useCycleStore()

function onSelect(event: globalThis.Event) {
  const target = event.target as HTMLSelectElement
  const cycleId = target.value
  if (cycleId) {
    store.loadCycle(cycleId)
  }
}

import { formatDateTime } from '@/utils/time'

function formatCycleLabel(cycleId: string, cameras: number, snow: number): string {
  const label = formatDateTime(cycleId)
  const snowTag = snow > 0 ? ` -- ${snow} snow` : ''
  return `${label} (${cameras} cams${snowTag})`
}
</script>

<template>
  <div class="cycle-selector">
    <label for="cycle-select">Capture Cycle:</label>
    <select id="cycle-select" @change="onSelect">
      <option
        v-for="cycle in store.allCycles"
        :key="cycle.cycle_id"
        :value="cycle.cycle_id"
        :selected="cycle.cycle_id === store.currentCycle?.cycle.cycle_id"
      >
        {{ formatCycleLabel(cycle.cycle_id, cycle.cameras_processed, cycle.snow_count) }}
      </option>
    </select>
  </div>
</template>

<style scoped>
.cycle-selector {
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

<script setup lang="ts">
defineProps<{
  label: string
  active: boolean | null
  variant?: 'danger' | 'warning' | 'info' | 'default'
}>()
</script>

<template>
  <span
    v-if="active"
    class="badge"
    :class="`badge-${variant || 'default'}`"
  >
    {{ label }}
  </span>
</template>

<style scoped>
.badge {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.badge-danger {
  background: #fee2e2;
  color: #dc2626;
}

.badge-warning {
  background: #fef9c3;
  color: #ca8a04;
}

.badge-info {
  background: #dbeafe;
  color: #2563eb;
}

.badge-default {
  background: #f3f4f6;
  color: #6b7280;
}
</style>

<script setup lang="ts">
import { RouterView } from 'vue-router'
import { isAuthenticated, refreshAuthState } from '@/composables/useAuth'
import LoginScreen from '@/components/LoginScreen.vue'

// Re-check token on app mount (e.g. token may have expired since last visit)
refreshAuthState()
</script>

<template>
  <LoginScreen v-if="!isAuthenticated" />
  <RouterView v-else />
</template>

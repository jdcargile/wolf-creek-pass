<script setup lang="ts">
import { ref } from 'vue'
import { login } from '@/composables/useAuth'

const passphrase = ref('')
const errorMsg = ref('')
const loading = ref(false)

async function onSubmit() {
  if (!passphrase.value.trim()) return
  loading.value = true
  errorMsg.value = ''
  const err = await login(passphrase.value.trim())
  loading.value = false
  if (err) {
    errorMsg.value = err
    passphrase.value = ''
  }
}
</script>

<template>
  <div class="login-backdrop">
    <!-- Mountain silhouette layers -->
    <div class="mountain-bg">
      <svg class="mountains" viewBox="0 0 1440 320" preserveAspectRatio="none">
        <path
          d="M0,320 L0,240 Q120,160 240,200 Q360,100 480,180 Q600,60 720,140 Q840,40 960,120 Q1080,80 1200,160 Q1320,100 1440,180 L1440,320 Z"
          fill="rgba(255,255,255,0.04)"
        />
        <path
          d="M0,320 L0,260 Q180,180 360,220 Q540,140 720,200 Q900,120 1080,180 Q1260,140 1440,220 L1440,320 Z"
          fill="rgba(255,255,255,0.06)"
        />
      </svg>
    </div>

    <!-- Login card -->
    <form class="login-card" @submit.prevent="onSubmit">
      <div class="login-title">Wolf Creek Pass</div>
      <div class="login-subtitle">Cabin Dashboard</div>

      <input
        v-model="passphrase"
        type="password"
        class="login-input"
        placeholder="Passphrase"
        autocomplete="current-password"
        autofocus
        :disabled="loading"
      />

      <button
        type="submit"
        class="login-btn"
        :disabled="loading || !passphrase.trim()"
      >
        {{ loading ? 'Verifying...' : 'Enter' }}
      </button>

      <div v-if="errorMsg" class="login-error">{{ errorMsg }}</div>
    </form>
  </div>
</template>

<style scoped>
.login-backdrop {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(165deg, #0f172a 0%, #1e293b 40%, #334155 100%);
  overflow: hidden;
}

/* ── Mountain background ──────────────────────────────────────────────── */

.mountain-bg {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 40%;
  pointer-events: none;
}

.mountains {
  width: 100%;
  height: 100%;
}

/* ── Login card ───────────────────────────────────────────────────────── */

.login-card {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  width: 320px;
  max-width: 90vw;
  padding: 2.5rem 2rem;
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.login-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #f1f5f9;
  letter-spacing: -0.02em;
}

.login-subtitle {
  font-size: 0.8rem;
  color: #94a3b8;
  margin-top: -0.5rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.login-input {
  width: 100%;
  padding: 0.75rem 1rem;
  font-family: inherit;
  font-size: 0.9rem;
  color: #f1f5f9;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.login-input::placeholder {
  color: #64748b;
}

.login-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}

.login-input:disabled {
  opacity: 0.5;
}

.login-btn {
  width: 100%;
  padding: 0.75rem;
  font-family: inherit;
  font-size: 0.9rem;
  font-weight: 600;
  color: #fff;
  background: #3b82f6;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s, transform 0.1s;
}

.login-btn:hover:not(:disabled) {
  background: #2563eb;
}

.login-btn:active:not(:disabled) {
  transform: scale(0.98);
}

.login-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.login-error {
  font-size: 0.8rem;
  color: #f87171;
  text-align: center;
}
</style>

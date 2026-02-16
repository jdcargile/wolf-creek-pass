/** Fetch helpers for the cabin dashboard API (Lambda Function URL). */

import type { ReolinkResponse } from '@/types/reolink'
import type { SensorPushResponse } from '@/types/sensorpush'
import { getToken, clearToken } from '@/composables/useAuth'

const BASE_URL = import.meta.env.VITE_REOLINK_API_URL || ''

function apiUrl(params: Record<string, string>): string {
  if (!BASE_URL) {
    throw new Error('VITE_REOLINK_API_URL is not configured')
  }
  const qs = new URLSearchParams(params).toString()
  return `${BASE_URL.replace(/\/+$/, '')}?${qs}`
}

/** Build fetch headers with Authorization if a token exists. */
function authHeaders(): HeadersInit {
  const headers: Record<string, string> = {}
  const token = getToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

/** Fetch with auth. Clears token on 401 so the login screen re-appears. */
async function authFetch(url: string): Promise<Response> {
  const resp = await fetch(url, { headers: authHeaders() })
  if (resp.status === 401) {
    clearToken()
    throw new Error('Session expired — please log in again')
  }
  return resp
}

export async function fetchReolinkSnapshots(date: string): Promise<ReolinkResponse> {
  const resp = await authFetch(apiUrl({ date }))
  if (!resp.ok) {
    throw new Error(`Reolink API error: ${resp.status} ${resp.statusText}`)
  }
  return resp.json()
}

/** Fetch current sensor readings only (fast, ~3s). */
export async function fetchSensorPushSummary(): Promise<SensorPushResponse> {
  const resp = await authFetch(apiUrl({ action: 'sensorpush' }))
  if (!resp.ok) {
    throw new Error(`SensorPush API error: ${resp.status} ${resp.statusText}`)
  }
  return resp.json()
}

/** Fetch full 7-day history with time series + ranges (slow first load, cached). */
export async function fetchSensorPushHistory(): Promise<SensorPushResponse> {
  const resp = await authFetch(apiUrl({ action: 'sensorpush', history: '1' }))
  if (!resp.ok) {
    throw new Error(`SensorPush API error: ${resp.status} ${resp.statusText}`)
  }
  return resp.json()
}

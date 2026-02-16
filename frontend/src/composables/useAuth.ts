/**
 * Authentication composable — manages session token in localStorage.
 *
 * Token format: ``<expiry_hex>.<hmac_hex>`` (stateless, verified server-side).
 * Stored in localStorage so it persists across "Add to Home Screen" sessions.
 */

import { ref } from 'vue'

const TOKEN_KEY = 'wcp_auth_token'
const API_BASE = import.meta.env.VITE_REOLINK_API_URL || ''

/** Reactive flag — true when a valid (not-expired) token exists in localStorage. */
export const isAuthenticated = ref(checkToken())

/** Read the stored token (or null). */
export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

/** Store a token and update the reactive flag. */
export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
  isAuthenticated.value = true
}

/** Clear the token and update the reactive flag. */
export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
  isAuthenticated.value = false
}

/**
 * Client-side token validity check.
 * Parses the expiry from the hex prefix and compares to now.
 * The server does the authoritative check — this just avoids
 * showing the dashboard briefly before a 401.
 */
function checkToken(): boolean {
  const token = localStorage.getItem(TOKEN_KEY)
  if (!token) return false
  const parts = token.split('.', 2)
  if (parts.length !== 2) return false
  try {
    const expiry = parseInt(parts[0]!, 16)
    return Date.now() / 1000 < expiry
  } catch {
    return false
  }
}

/** Re-check the token (e.g. on app mount). */
export function refreshAuthState(): void {
  isAuthenticated.value = checkToken()
}

/**
 * Attempt login with a passphrase.
 * Returns null on success, or an error message string on failure.
 */
export async function login(passphrase: string): Promise<string | null> {
  const url = API_BASE ? `${API_BASE}/?action=auth` : '/?action=auth'
  try {
    const resp = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ passphrase }),
    })
    const data = await resp.json()
    if (resp.ok && data.token) {
      setToken(data.token)
      return null
    }
    return data.error || 'Login failed'
  } catch (e: any) {
    return e.message || 'Network error'
  }
}

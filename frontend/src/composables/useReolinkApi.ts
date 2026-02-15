/** Fetch helper for the Reolink snapshot API (Lambda Function URL). */

import type { ReolinkResponse } from '@/types/reolink'

const BASE_URL = import.meta.env.VITE_REOLINK_API_URL || ''

export async function fetchReolinkSnapshots(date: string): Promise<ReolinkResponse> {
  if (!BASE_URL) {
    throw new Error('VITE_REOLINK_API_URL is not configured')
  }

  // Strip any trailing slash, append query param
  const url = `${BASE_URL.replace(/\/+$/, '')}?date=${encodeURIComponent(date)}`
  const resp = await fetch(url)

  if (!resp.ok) {
    throw new Error(`Reolink API error: ${resp.status} ${resp.statusText}`)
  }

  return resp.json()
}

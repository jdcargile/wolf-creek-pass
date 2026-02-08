/** Fetch helpers for loading cycle data from JSON files. */

import type { CycleData, CycleIndex } from '@/types'

// In dev mode, load from local output dir. In production, from S3.
const BASE_URL = import.meta.env.VITE_DATA_URL || '/data'

export async function fetchCycleIndex(): Promise<CycleIndex> {
  const resp = await fetch(`${BASE_URL}/index.json`)
  if (!resp.ok) throw new Error(`Failed to load cycle index: ${resp.status}`)
  return resp.json()
}

export async function fetchCycleData(cycleId: string): Promise<CycleData> {
  const safeId = cycleId.replace(/:/g, '-')
  const resp = await fetch(`${BASE_URL}/cycle-${safeId}.json`)
  if (!resp.ok) throw new Error(`Failed to load cycle ${cycleId}: ${resp.status}`)
  return resp.json()
}

export async function fetchLatestCycle(): Promise<CycleData> {
  const resp = await fetch(`${BASE_URL}/latest.json`)
  if (!resp.ok) throw new Error(`Failed to load latest cycle: ${resp.status}`)
  return resp.json()
}

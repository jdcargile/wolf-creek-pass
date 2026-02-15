/**
 * Mountain Time (America/Denver) utilities.
 *
 * All dashboard times are displayed in Mountain Time regardless of the
 * viewer's browser timezone.  The cabin, cameras, and sensors are all
 * in the Hanna, UT area (Mountain Time).
 */

export const TIMEZONE = 'America/Denver'

/** Extract the hour (0-23) in Mountain Time from an ISO timestamp string. */
export function mountainHour(ts: string): number {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: TIMEZONE,
    hour: 'numeric',
    hour12: false,
  }).formatToParts(new Date(ts))
  const hourPart = parts.find((p) => p.type === 'hour')
  // Intl hour12:false returns "24" for midnight in some engines; normalise.
  const raw = parseInt(hourPart?.value ?? '0', 10)
  return raw === 24 ? 0 : raw
}

/** Return today's date as YYYY-MM-DD in Mountain Time. */
export function todayMountain(): string {
  const now = new Date()
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: TIMEZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(now)
  // en-CA locale formats as YYYY-MM-DD
  return parts
}

/** Format an ISO timestamp as a short time: "7:00 AM" in Mountain Time. */
export function formatTime(ts: string): string {
  return new Date(ts).toLocaleTimeString('en-US', {
    timeZone: TIMEZONE,
    hour: 'numeric',
    minute: '2-digit',
  })
}

/** Format an ISO timestamp as date + time: "Feb 15, 7:00 AM" in Mountain Time. */
export function formatDateTime(ts: string): string {
  return new Date(ts).toLocaleString('en-US', {
    timeZone: TIMEZONE,
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

/** Format an ISO timestamp as a short date: "2/15" in Mountain Time. */
export function formatShortDate(ts: string): string {
  return new Date(ts).toLocaleDateString('en-US', {
    timeZone: TIMEZONE,
    month: 'numeric',
    day: 'numeric',
  })
}

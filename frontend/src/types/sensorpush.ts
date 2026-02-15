/** TypeScript interfaces for the SensorPush sensor API. */

export interface MetricRange {
  min: number
  max: number
}

export interface SensorCurrent {
  timestamp: string
  temperature?: number
  humidity?: number
  dewpoint?: number
  barometric_pressure?: number
  vpd?: number
}

export interface SensorRanges {
  temperature?: MetricRange
  humidity?: MetricRange
  dewpoint?: MetricRange
  barometric_pressure?: MetricRange
  vpd?: MetricRange
}

/** A single data point in a time series: [ISO timestamp, value]. */
export type TimeSeriesPoint = [string, number]

/** Per-metric time series data for charting. */
export interface SensorTimeSeries {
  temperature?: TimeSeriesPoint[]
  humidity?: TimeSeriesPoint[]
  dewpoint?: TimeSeriesPoint[]
  barometric_pressure?: TimeSeriesPoint[]
  vpd?: TimeSeriesPoint[]
}

export interface SensorData {
  id: string
  name: string
  current: SensorCurrent | null
  range_12h: SensorRanges
  range_24h: SensorRanges
  reading_count: number
  time_series: SensorTimeSeries
}

export interface SensorPushResponse {
  sensors: SensorData[]
}

/** Metric display configuration. */
export interface MetricConfig {
  key: keyof SensorRanges
  label: string
  unit: string
  precision: number
  /** Color for the chart line/area. */
  color: string
}

export const METRIC_CONFIGS: MetricConfig[] = [
  { key: 'temperature', label: 'Temperature', unit: '°F', precision: 1, color: '#ef4444' },
  { key: 'humidity', label: 'Humidity', unit: '%', precision: 1, color: '#3b82f6' },
  { key: 'dewpoint', label: 'Dewpoint', unit: '°F', precision: 1, color: '#8b5cf6' },
  { key: 'barometric_pressure', label: 'Pressure', unit: ' inHg', precision: 2, color: '#f59e0b' },
  { key: 'vpd', label: 'VPD', unit: ' kPa', precision: 2, color: '#10b981' },
]

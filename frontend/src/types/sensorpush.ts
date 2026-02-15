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

export interface SensorData {
  id: string
  name: string
  current: SensorCurrent | null
  range_12h: SensorRanges
  range_24h: SensorRanges
  reading_count: number
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
}

export const METRIC_CONFIGS: MetricConfig[] = [
  { key: 'temperature', label: 'Temperature', unit: '°F', precision: 1 },
  { key: 'humidity', label: 'Humidity', unit: '%', precision: 1 },
  { key: 'dewpoint', label: 'Dewpoint', unit: '°F', precision: 1 },
  { key: 'barometric_pressure', label: 'Pressure', unit: ' inHg', precision: 2 },
  { key: 'vpd', label: 'VPD', unit: ' kPa', precision: 2 },
]

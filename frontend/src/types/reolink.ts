/** TypeScript interfaces for the Reolink camera snapshot API. */

export interface ReolinkDetection {
  label: string
  confidence: number
}

export interface ReolinkWeather {
  temperature_f?: number
  apparent_temperature_f?: number
  relative_humidity_pct?: number
  is_day?: boolean
  precipitation_in?: number
  rain_in?: number
  snowfall_in?: number
  snow_depth_ft?: number
  cloud_cover_pct?: number
  pressure_msl_hpa?: number
  wind_speed_mph?: number
  wind_direction_deg?: number
  wind_gusts_mph?: number
  weather_code?: number
  weather_description?: string
}

export interface ReolinkSnapshot {
  timestamp: string
  image_url: string | null
  interesting: boolean
  detections: ReolinkDetection[]
  weather: ReolinkWeather
}

export interface ReolinkCamera {
  id: string
  name: string
  snapshots: ReolinkSnapshot[]
}

export interface ReolinkResponse {
  date: string
  cameras: ReolinkCamera[]
}

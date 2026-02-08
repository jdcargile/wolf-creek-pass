/** TypeScript interfaces matching the Python Pydantic models. */

export interface CycleSummary {
  cycle_id: string
  started_at: string
  completed_at: string
  cameras_processed: number
  snow_count: number
  event_count: number
  travel_time_s: number | null
  distance_m: number | null
}

export interface CaptureRecord {
  camera_id: number
  cycle_id: string
  captured_at: string
  image_key: string
  image_url?: string
  has_snow: boolean | null
  has_car: boolean | null
  has_truck: boolean | null
  has_animal: boolean | null
  analysis_notes: string
  roadway: string | null
  direction: string | null
  location: string | null
  latitude: number | null
  longitude: number | null
}

export interface Route {
  origin: string
  destination: string
  polyline: string
  distance_m: number
  duration_s: number
  duration_in_traffic_s: number | null
}

export interface RoadCondition {
  id: number
  roadway_name: string
  road_condition: string
  weather_condition: string
  restriction: string
  encoded_polyline: string
  last_updated: number
}

export interface Event {
  id: string
  event_type: string
  event_sub_type: string
  roadway_name: string
  direction: string
  description: string
  severity: string
  latitude: number | null
  longitude: number | null
  is_full_closure: boolean
}

export interface WeatherStation {
  id: number
  station_name: string
  air_temperature: string
  surface_temp: string
  surface_status: string
  wind_speed_avg: string
  wind_speed_gust: string
  wind_direction: string
  precipitation: string
  relative_humidity: string
}

export interface CycleData {
  cycle: CycleSummary
  route: Route | null
  captures: CaptureRecord[]
  conditions: RoadCondition[]
  events: Event[]
  weather: WeatherStation[]
}

export interface CycleIndex {
  cycles: CycleSummary[]
  count: number
}

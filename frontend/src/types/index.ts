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
  route_id: string
  name: string
  color: string
  share_id: string
  origin: string
  destination: string
  polyline: string
  distance_m: number
  duration_s: number
  has_closure: boolean
  has_conditions: boolean
  travel_time_display: string
  distance_display: string
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

export interface MountainPass {
  id: number
  name: string
  roadway: string
  elevation_ft: string
  latitude: number | null
  longitude: number | null
  station_name: string
  air_temperature: string
  wind_speed: string
  wind_gust: string
  wind_direction: string
  surface_temp: string
  surface_status: string
  visibility: string
  forecasts: string
  closure_status: string
  closure_description: string
  seasonal_route_name: string
  seasonal_closure_title: string
}

export interface SnowPlow {
  id: number
  name: string
  latitude: number | null
  longitude: number | null
  heading: number | null
  speed: number | null
  last_updated: string
}

export interface CycleData {
  cycle: CycleSummary
  routes: Route[]
  captures: CaptureRecord[]
  conditions: RoadCondition[]
  events: Event[]
  weather: WeatherStation[]
  passes: MountainPass[]
  plows: SnowPlow[]
}

export interface CycleIndex {
  cycles: CycleSummary[]
  count: number
}

# Wolf Creek Pass v2 -- Implementation Plan

## Overview

Rework of the traffic camera monitor into a full route-aware road conditions dashboard.

**Route:** 3814 Sweet Vera Ln, Riverton UT 84065 --> 14852 North Fork Rd, Hanna UT 84031
(I-15 south --> US-189/US-40 through Heber --> SR-35 over Wolf Creek Pass --> Hanna)

**Goal:** Every hour, capture all UDOT camera images along the route, analyze them with Claude Vision, enrich with road conditions/events/weather/plows, and publish an interactive mobile-friendly dashboard with an interactive map showing the route, camera locations, and conditions.

## Architecture

```
EventBridge (hourly cron)
        |
        v
   AWS Lambda (Python, container image)
        |
        +--> Google Directions API (route + travel time)
        +--> UDOT API (cameras, conditions, events, weather, plows)
        +--> Anthropic API (Claude Vision image analysis)
        |
        +--> DynamoDB (all structured data, single-table)
        +--> S3 /images/   (camera JPEGs)
        +--> S3 /data/     (JSON data files for Vue)
        +--> S3 /app/      (Vue SPA static files)
```

### Data Flow

1. Lambda fires hourly via EventBridge
2. Calls Google Directions API for route polyline + travel time
3. Fetches ALL UDOT cameras, filters by proximity to route (~2km buffer)
4. Downloads camera images, uploads to S3
5. Analyzes each image with Claude Vision
6. Fetches UDOT road conditions, events, weather stations, mountain passes, snow plows
7. Writes all structured data to DynamoDB
8. Exports JSON data files to S3 for the Vue frontend
9. Vue SPA (hosted on S3) fetches JSON + images and renders the dashboard

### Local Development

LocalStack emulates DynamoDB + S3 locally via Docker. Same boto3 code, just a different endpoint URL (`http://localhost:4566`). Controlled by `AWS_ENDPOINT_URL` env var.

## Tech Stack

### Backend (Python)
- **Python 3.11+**
- **boto3** -- AWS SDK (DynamoDB, S3)
- **anthropic** -- Claude Vision API
- **googlemaps** -- Google Directions API
- **requests** -- UDOT API calls
- **click** -- CLI framework
- **pydantic / pydantic-settings** -- Data models + settings
- **rich** -- CLI output
- **polyline** -- Decode Google encoded polylines
- **schedule** -- Local hourly scheduler

### Frontend (Vue 3 + TypeScript)
- **Vue 3** -- Composition API
- **TypeScript** -- Type safety
- **Vite** -- Build tool + dev server
- **Vue Router** -- Page routing
- **Pinia** -- State management
- **Leaflet.js** -- Interactive maps (via @vue-leaflet/vue-leaflet)

### Infrastructure (AWS CDK, Python)
- **DynamoDB** -- Single-table design, always-free tier (25GB, 25 RCU/WCU)
- **S3** -- Images, JSON data files, Vue static hosting
- **Lambda** -- Container image, Python runtime
- **EventBridge** -- Hourly cron trigger
- **SSM Parameter Store** -- API keys (deployed)
- **CDK (Python)** -- Infrastructure as code

### Local Dev
- **LocalStack** -- Emulates DynamoDB + S3 locally
- **poethepoet** -- Task runner

## DynamoDB Single-Table Design

| PK | SK | GSI1PK | GSI1SK | Data |
|----|-----|--------|--------|------|
| `CAMERA#123` | `META` | `CAMERA` | `123` | Camera metadata (roadway, location, lat/lng, distance from route) |
| `CAMERA#123` | `CAPTURE#2026-02-07T23:00:00` | `CYCLE#2026-02-07T23:00:00` | `CAMERA#123` | Analysis result, S3 image key, snow/car/truck/animal bools, notes |
| `ROUTE#riverton-hanna` | `META` | -- | -- | Polyline, distance_m, duration_s |
| `ROUTE#riverton-hanna` | `CYCLE#2026-02-07T23:00:00` | `CYCLE#2026-02-07T23:00:00` | `ROUTE` | Cycle summary (cameras processed, overall conditions, travel time) |
| `CONDITION#sr-35` | `2026-02-07T23:00:00` | `CYCLE#2026-02-07T23:00:00` | `CONDITION` | Road condition, weather condition, surface status |
| `EVENT#12345` | `META` | `CYCLE#2026-02-07T23:00:00` | `EVENT` | Incident type, severity, description, lat/lng, roadway |
| `WEATHER#station-name` | `2026-02-07T23:00:00` | `CYCLE#2026-02-07T23:00:00` | `WEATHER` | Air temp, surface temp, wind, precip, humidity |
| `PLOW#vehicle-id` | `2026-02-07T23:00:00` | `CYCLE#2026-02-07T23:00:00` | `PLOW` | Lat/lng, bearing, encoded polyline (recent track) |

**GSI1** enables: "Give me everything from capture cycle X" -- one query returns all cameras, conditions, events, weather, plows for that cycle.

**Key access patterns:**
- All captures for a camera: PK=`CAMERA#123`, SK begins_with `CAPTURE#`
- Full cycle data: GSI1PK=`CYCLE#2026-02-07T23:00:00`
- List all cycles: GSI1PK begins_with `CYCLE#`, SK=`ROUTE` (cycle summaries only)
- Camera metadata: PK=`CAMERA#123`, SK=`META`

## API Costs

Runs every 3 hours (~240 cycles/month). Uses Haiku 3.5 with SHA-256 image hash dedup
(skips Claude if camera image unchanged — typically 30-50% cache hit rate).

| Service | Usage | Monthly Cost |
|---------|-------|-------------|
| Google Directions API | ~240 requests/month (every 3hr) | **$0** (free tier: 10,000/month) |
| Anthropic Claude Haiku | ~240 cycles x ~15 cameras x ~60% new = ~2,160 images | **~$2-3** ($0.80/$4 per MTok) |
| UDOT API | ~240 cycles x 6 endpoints = ~1,440 calls | **$0** (free, rate limited 10/min) |
| DynamoDB | ~5,000 writes + ~15,000 reads/month | **$0** (always-free tier) |
| S3 | ~2-5 GB images/month | **$0.23/GB** (~$1/month) |
| Lambda | ~240 invocations x ~60s each | **$0** (free tier: 400K GB-sec) |
| EventBridge | 240 events/month | **$0** (free) |
| **Total** | | **~$3-4/month** |

## File Structure

```
wolf-creek-pass/
  # Python backend
  models.py                   # Pydantic models (Camera, Route, Capture, Condition, etc.)
  settings.py                 # Pydantic settings (env vars, local vs AWS config)
  traffic_cam_monitor.py      # CLI entry point + capture cycle orchestrator
  route.py                    # Google Directions API + haversine camera matching
  udot.py                     # All UDOT API calls (cameras, conditions, events, weather, plows)
  analyze.py                  # Claude Vision image analysis
  storage.py                  # Storage abstraction (DynamoDB+S3 or SQLite+filesystem)
  export.py                   # Generate JSON data files for Vue frontend
  query_data.py               # CLI query tool

  # Vue frontend
  frontend/
    package.json
    tsconfig.json
    vite.config.ts
    index.html
    src/
      App.vue
      main.ts
      router/
        index.ts              # Vue Router config
      stores/
        cycle.ts              # Pinia store -- current cycle state
      composables/
        useApi.ts             # Fetch helpers (get cycles, get route data)
      components/
        RouteMap.vue          # Leaflet interactive map with route + markers
        CameraCard.vue        # Camera image + condition badges
        CycleSelector.vue     # Historical cycle dropdown
        ConditionBadge.vue    # Color-coded status badges (snow, clear, etc.)
        RouteSummary.vue      # Distance, travel time, overall conditions
        EventMarker.vue       # Incident/construction map marker
      views/
        Dashboard.vue         # Main view -- map + camera grid + route summary
      types/
        index.ts              # TypeScript interfaces (mirrors Pydantic models)
      assets/
        main.css              # Mobile-first responsive styles

  # AWS CDK infrastructure
  infra/
    app.py                    # CDK app entry point
    stack.py                  # WolfCreekPassStack (DynamoDB, S3, Lambda, EventBridge, IAM)
  cdk.json                    # CDK config

  # Config + packaging
  Dockerfile                  # Lambda container image
  pyproject.toml              # Python deps + poe tasks
  .env.example                # Local dev environment variables
  PLAN.md                     # This file
  REQUIREMENTS.md             # Original requirements
  README.md                   # Project docs
```

## Poe Tasks

```
poe monitor              # Run capture cycle locally (LocalStack)
poe monitor --once       # Single capture cycle
poe query                # CLI query (recent captures)
poe dev                  # Start Vue dev server (Vite, hot reload)
poe build                # Build Vue for production
poe deploy               # Build Vue + cdk deploy (full stack)
poe cdk-deploy           # Deploy AWS infra only
poe cdk-diff             # Preview infra changes
poe localstack-up        # Start LocalStack
poe localstack-down      # Stop LocalStack
```

## Implementation Phases

### Phase 1: Project Scaffolding
- [ ] Vue 3 + TypeScript project (`frontend/`) via `npm create vue@latest`
- [ ] CDK project (`infra/`) via `cdk init`
- [ ] Update `pyproject.toml` with new deps (boto3, googlemaps, polyline, jinja2)
- [ ] Update `.env.example` with all required env vars
- [ ] Add `GOOGLE_MAPS_API_KEY` to `.env.example`
- [ ] Set up LocalStack Docker Compose

### Phase 2: Storage Abstraction
- [ ] Define storage Protocol (interface) in `storage.py`
- [ ] Implement `DynamoStorage` (DynamoDB + S3)
- [ ] Implement `SQLiteStorage` (local SQLite + filesystem, for offline fallback)
- [ ] Controlled by `STORAGE_BACKEND` env var (`dynamo` or `sqlite`)

### Phase 3: Route Planning
- [ ] `route.py` -- call Google Directions API (Riverton --> Hanna)
- [ ] Decode route polyline into lat/lng points
- [ ] Haversine distance calculation for camera-to-route matching
- [ ] Filter UDOT cameras within ~2km of route
- [ ] Store route geometry + matched cameras

### Phase 4: UDOT API Expansion
- [ ] `udot.py` -- fetch all 9 UDOT endpoints
- [ ] Cameras (existing, refactored)
- [ ] Road conditions (surface + weather per segment)
- [ ] Events/incidents (accidents, construction, closures)
- [ ] Weather stations (temp, wind, precip near route)
- [ ] Mountain passes (Wolf Creek Pass specifically)
- [ ] Snow plows (real-time positions near route)
- [ ] Message signs (DMS, may contain travel times)
- [ ] Alerts (system-wide advisories)
- [ ] Filter all data by proximity to route

### Phase 5: Refactor Monitor
- [ ] `traffic_cam_monitor.py` -- route-aware capture cycle orchestrator
- [ ] On each cycle: get route, match cameras, download images, analyze, fetch conditions
- [ ] `analyze.py` -- extracted Claude Vision logic
- [ ] `export.py` -- generate JSON data files for Vue (per-cycle + index)
- [ ] Upload JSON + images to S3

### Phase 6: Vue Frontend -- Layout + Map
- [ ] `Dashboard.vue` -- mobile-first responsive layout (CSS grid/flexbox)
- [ ] `RouteMap.vue` -- Leaflet.js interactive map
- [ ] Draw route polyline on map
- [ ] Camera markers (color-coded: green=clear, yellow=caution, red=snow/incident)
- [ ] Click marker --> popup with camera image + analysis
- [ ] Event/incident markers
- [ ] Snow plow positions

### Phase 7: Vue Frontend -- Data + Components
- [ ] `useApi.ts` -- fetch JSON data files from S3
- [ ] `cycle.ts` Pinia store -- manage current cycle state
- [ ] `CameraCard.vue` -- image thumbnail + condition badges + notes
- [ ] `ConditionBadge.vue` -- color-coded snow/car/animal badges
- [ ] `RouteSummary.vue` -- distance, travel time, overall conditions bar
- [ ] `CycleSelector.vue` -- dropdown to browse historical capture cycles
- [ ] `EventMarker.vue` -- incident details in map popup

### Phase 8: CDK Infrastructure
- [ ] `infra/stack.py` -- WolfCreekPassStack
- [ ] DynamoDB table (single-table + GSI1)
- [ ] S3 bucket (images, data JSON, Vue static files, static website hosting)
- [ ] Lambda function (container image from Dockerfile)
- [ ] EventBridge rule (hourly cron)
- [ ] IAM roles and policies
- [ ] SSM parameters for API keys
- [ ] `Dockerfile` -- Lambda container image with Python deps

### Phase 9: LocalStack Integration
- [ ] Docker Compose for LocalStack
- [ ] Seed script to create DynamoDB table + S3 bucket locally
- [ ] Verify full capture cycle works against LocalStack
- [ ] `poe localstack-up` / `poe localstack-down` tasks

### Phase 10: Deploy + Test
- [ ] `poe deploy` -- build Vue + cdk deploy
- [ ] Verify Lambda fires on schedule
- [ ] Verify S3 static site serves Vue app
- [ ] Test on mobile browser
- [ ] Verify historical cycle browsing works

## UDOT API Reference

Rate limit: 10 calls per 60 seconds. All endpoints return ALL records (no server-side filtering).

| Endpoint | URL | Key Data |
|----------|-----|----------|
| Cameras | `/api/v2/get/cameras` | Id, Roadway, Direction, Location, Lat/Lng, Views[].Url |
| Road Conditions | `/api/v2/get/roadconditions` | RoadCondition, WeatherCondition, EncodedPolyline |
| Events | `/api/v2/get/event` | EventType, Description, Severity, Lat/Lng, IsFullClosure |
| Weather Stations | `/api/v2/get/weatherstations` | AirTemp, SurfaceTemp, SurfaceStatus, Wind, Precip |
| Mountain Passes | `/api/v2/get/mountainpasses` | Name, SeasonalInfo, AirTemp, SurfaceStatus, Visibility |
| Snow Plows | `/api/v2/get/servicevehicles` | Lat/Lng, Bearing, EncodedPolyline (track) |
| Message Signs | `/api/v2/get/messagesigns` | Messages (may contain travel times), Lat/Lng |
| Alerts | `/api/v2/get/alerts` | Message, Regions, HighImportance |
| Rest Areas | `/api/v2/get/restareas` | Name, Location, CarStalls, TruckStalls |

## Notes

- UDOT API has NO routing, travel time, or geographic filtering. All filtering is client-side.
- Google Directions API provides route polyline + traffic-aware travel time. Free tier covers ~10,000 requests/month.
- DynamoDB always-free tier: 25GB storage, 25 RCU/25 WCU. More than enough.
- S3 is the only ongoing cost after free tier expires (~$0.023/GB/month for images).
- Claude Vision cost minimized via: Haiku 3.5 (not Sonnet), 3hr schedule (not hourly), SHA-256 image hash dedup (skip unchanged images). Estimated ~$2-3/month.

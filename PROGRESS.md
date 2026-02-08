# Wolf Creek Pass v2 -- Progress Tracker

> See PLAN.md for the full implementation plan.
> This file tracks what's been done, what's in progress, and what's next.

## Status: Phases 1-9 COMPLETE -- Ready for Phase 10 (Deploy + Test)

### Phase 1: Project Scaffolding (DONE)

- [x] PLAN.md written with full architecture, DynamoDB schema, file structure, costs
- [x] `.env.example` updated with all required env vars (Anthropic, UDOT, Google Maps, AWS)
- [x] Existing codebase refactored: Click CLI, Pydantic models, Rich output, poethepoet, uv
- [x] Fixed media type detection bug (magic bytes instead of file extension)
- [x] Fixed deprecated `imghdr` module
- [x] Flattened Click CLI (`poe monitor` not `poe monitor monitor`)
- [x] Vue 3 + TypeScript frontend scaffolding (`frontend/`)
  - Vue Router, Pinia, ESLint, Prettier configured
  - Leaflet.js + @vue-leaflet/vue-leaflet + @types/leaflet installed
- [x] CDK infrastructure scaffolding (`infra/`)
  - WolfCreekPassStack: DynamoDB, S3, Lambda, EventBridge, SSM params
  - Single-table design with GSI1 for cycle queries
- [x] `pyproject.toml` v0.2.0 with new deps (boto3, googlemaps, polyline, aws-cdk-lib, constructs)
- [x] LocalStack Docker Compose (`docker-compose.yml`)
- [x] `.gitignore` for all artifacts (Python, Node, CDK, SQLite, images, .env)
- [x] All poe tasks registered (monitor, query, dev, build, localstack-up/down, cdk-deploy/diff)
- [x] `uv sync` + `npm install` verified working
- [x] Vue TypeScript compilation verified (vue-tsc --noEmit passes)

### Phase 2: Storage Abstraction (DONE)

- [x] `settings.py` extracted from models.py
  - All env vars: API keys, storage backend, AWS config, route origin/destination, camera buffer
  - Pydantic Settings with `.env` file support
- [x] `models.py` expanded with all data types
  - Camera, CaptureRecord, CycleSummary, Route, RoadCondition, Event, WeatherStation, AnalysisResult
  - CaptureRecord includes denormalized camera info (for DynamoDB single-table)
- [x] `storage.py` with Protocol interface + two implementations
  - `Storage` Protocol: 16 methods (cameras, captures, routes, cycles, conditions, events, weather, images)
  - `SQLiteStorage`: 7 tables, full CRUD, local filesystem for images
  - `DynamoStorage`: single-table design with GSI1, S3 for images, LocalStack auto-init
  - `create_storage(settings)` factory function
- [x] SQLiteStorage verified: full round-trip tests pass
- [x] DynamoStorage implemented (will be tested with LocalStack in Phase 9)

### Phase 3: Route Planning (DONE)

- [x] `route.py` -- Google Directions API (Riverton -> Hanna)
- [x] Polyline decoding via `polyline` library
- [x] `haversine_km` distance calculation
- [x] `min_distance_to_route` for proximity checks
- [x] `filter_cameras_by_route` with configurable buffer (default 2km)
- [x] Cameras sorted by position along route

### Phase 4: UDOT API Expansion (DONE)

- [x] `udot.py` -- all UDOT endpoints:
  - Cameras: `fetch_all_cameras`, `fetch_route_cameras`
  - Road conditions: `fetch_road_conditions`, `fetch_route_conditions`
  - Events: `fetch_events`, `fetch_route_events`
  - Weather: `fetch_weather_stations`, `fetch_route_weather`
  - Mountain passes: `fetch_mountain_pass_info`
  - Alerts: `fetch_alerts`
  - Snow plows: `fetch_snow_plows`, `fetch_route_plows`
- [x] All endpoints have route-filtered variants using haversine proximity

### Phase 5: Refactor Monitor (DONE)

- [x] `analyze.py` -- Claude Vision analysis extracted
  - Magic-byte media type detection
  - Works on raw bytes (no file dependency)
  - Structured prompt for snow/cars/trucks/animals
- [x] `traffic_cam_monitor.py` -- route-aware orchestrator
  - Full capture cycle: route -> cameras -> download -> analyze -> conditions/events/weather -> store -> export
  - Click CLI with `--once` flag and hourly schedule loop
- [x] `export.py` -- JSON export for Vue frontend
  - Per-cycle JSON files + latest.json + index.json
- [x] `query_data.py` -- rewritten with storage abstraction
  - 5 subcommands: recent, cycles, route, snow, animals
  - Rich tables for display

### Phase 6-7: Vue Frontend (DONE)

- [x] TypeScript types (`src/types/index.ts`) mirroring all Pydantic models
- [x] `useApi.ts` composable (fetch from JSON files, configurable via `VITE_DATA_URL`)
- [x] `cycle.ts` Pinia store (state, computed getters, load actions)
- [x] Components:
  - `RouteMap.vue` -- Leaflet map, polyline route, color-coded camera markers, event markers, popups with images
  - `CameraCard.vue` -- camera image, location, condition badges, analysis notes
  - `CycleSelector.vue` -- dropdown to switch capture cycles
  - `ConditionBadge.vue` -- reusable pill badge with danger/warning/info/default variants
  - `RouteSummary.vue` -- horizontal stat bar (miles, drive time, cameras, snow, events)
- [x] `HomeView.vue` -- full dashboard: header, route summary, map, weather grid, conditions, cameras, events, footer
- [x] `App.vue` rewritten (stripped boilerplate, simple RouterView shell)
- [x] `base.css` -- project design tokens (light/dark mode, surfaces, borders, text, semantic colors)
- [x] `main.css` -- minimal app styles importing base.css
- [x] `router/index.ts` simplified (single route, no About page)
- [x] Vite config: custom plugin to serve `../output/data/` at `/data` during dev
- [x] `vue-tsc --noEmit` passes (zero type errors)
- [x] `npm run build` passes (production build: ~117KB app JS + ~149KB Leaflet)

### Phase 8: CDK Infrastructure (DONE)

- [x] `handler.py` -- Lambda entry point
  - Reads API keys from SSM Parameter Store at runtime
  - Sets env vars so `Settings` picks them up via pydantic-settings
  - Calls `run_capture_cycle(settings)` for a single cycle
- [x] `Dockerfile` -- Lambda container image
  - Based on `public.ecr.aws/lambda/python:3.12`
  - Installs all Python deps, copies application code
  - Handler: `handler.lambda_handler`
- [x] `.dockerignore` -- excludes frontend, infra, dev artifacts
- [x] `export.py` updated -- writes JSON to S3 when `STORAGE_BACKEND=dynamo`
  - `_write_json()` helper: local filesystem (sqlite) or S3 `data/` prefix (dynamo)
  - `export_cycle_to_file()` and `export_cycle_index()` now accept `settings` param
- [x] `traffic_cam_monitor.py` updated -- passes `settings` to export functions
- [x] CDK stack (`infra/infra/infra_stack.py`) updated:
  - Lambda gets SSM read permissions for all 3 API key params
  - S3 BucketDeployment for Vue frontend (`frontend/dist/` -> S3 root)
  - `prune=False` so data/ and images/ aren't deleted on redeploy
  - SPA error fallback (`index.html` for both index and error doc)
  - CfnOutputs: WebsiteUrl, BucketName, TableName
- [x] `cdk.json` updated -- uses `uv run --group dev` to invoke CDK app
- [x] `pyproject.toml` -- added `cdk-synth` and `deploy` poe tasks
- [x] `cdk synth` passes -- full CloudFormation template verified

### Phase 9: LocalStack Integration (DONE)

- [x] `poe localstack-up` starts LocalStack (Docker Compose, DynamoDB + S3)
- [x] DynamoStorage auto-creates table + bucket on `init()`
- [x] Full round-trip verified against LocalStack:
  - Camera save/retrieve
  - Capture save/retrieve (with snow/car/animal flags)
  - Cycle save/retrieve
  - Image save to S3 + URL generation
- [x] S3 JSON export verified:
  - `data/cycle-{id}.json` -- per-cycle data
  - `data/latest.json` -- most recent cycle
  - `data/index.json` -- all cycles
  - Content verified: cycle_id, captures array, has_snow flags all correct
- [x] `.env.example` updated with better defaults + LocalStack instructions
  - Default to `sqlite` (no Docker needed for basic dev)
  - Commented-out LocalStack config ready to uncomment
  - VITE_DATA_URL instructions for LocalStack/production

### Phase 10: Deploy + Test (NEXT)

- [ ] `poe deploy` -- build Vue + cdk deploy
- [ ] Set SSM parameter values via AWS CLI
- [ ] Verify Lambda fires on schedule
- [ ] Verify S3 static site serves Vue app
- [ ] Test on mobile browser
- [ ] Verify historical cycle browsing works

---

## Phase Summary

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Project Scaffolding | DONE |
| 2 | Storage Abstraction (DynamoDB + SQLite) | DONE |
| 3 | Route Planning (Google Directions API) | DONE |
| 4 | UDOT API Expansion (all endpoints) | DONE |
| 5 | Refactor Monitor (route-aware orchestrator) | DONE |
| 6 | Vue Frontend -- Layout + Map | DONE |
| 7 | Vue Frontend -- Data + Components | DONE |
| 8 | CDK Infrastructure | DONE |
| 9 | LocalStack Integration | DONE |
| 10 | Deploy + Test | Next |

---

## Session Log

### 2026-02-07 (Session 1)
- Came up to speed on existing codebase
- Refactored: Click, Pydantic, Rich, poethepoet, uv, python-dotenv
- Fixed bugs: media type detection, deprecated imghdr, CLI group nesting
- Researched UDOT API (9 endpoints, no routing/travel time)
- Researched Google Directions API pricing ($0 for our usage)
- Made architecture decisions: AWS, DynamoDB, Vue 3 + TypeScript, CDK, LocalStack
- Wrote PLAN.md
- Completed Phase 1 scaffolding
- Completed Phase 2 storage abstraction
- Completed Phase 3 route planning
- Completed Phase 4 UDOT API expansion
- Completed Phase 5 monitor refactor
- Completed Phase 6-7 Vue frontend (types, store, composables, 5 components, dashboard)

### 2026-02-07 (Session 2)
- Initial git commit (57 files, 10k+ lines -- nothing had been committed!)
- Finished frontend cleanup:
  - Rewrote App.vue (stripped Vue boilerplate)
  - Rewrote base.css with project design tokens (light/dark mode)
  - Rewrote main.css (minimal, project-specific)
  - Simplified router (removed About route)
  - Added Vite dev server plugin to serve output/data/ at /data
  - Fixed RouteMap.vue TypeScript error (computed type assertion)
- Fixed npm rollup-darwin-arm64 issue (force installed native module)
- Verified: vue-tsc passes, npm run build passes
- Completed Phase 8 CDK infrastructure:
  - Created handler.py (Lambda entry point, SSM param reading)
  - Created Dockerfile (Lambda container, Python 3.12)
  - Created .dockerignore
  - Updated export.py for S3 output support
  - Updated CDK stack: SSM perms, S3 BucketDeployment, CfnOutputs
  - Updated cdk.json for uv-based invocation
  - Added poe tasks: cdk-synth, deploy
  - Verified cdk synth passes clean
- Completed Phase 9 LocalStack integration:
  - Started LocalStack via docker compose
  - Verified DynamoDB + S3 auto-provisioning
  - Full round-trip: camera, capture, cycle, image save/retrieve
  - S3 JSON export: cycle files, latest.json, index.json all verified
  - Updated .env.example with LocalStack instructions

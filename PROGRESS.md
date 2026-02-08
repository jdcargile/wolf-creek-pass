# Wolf Creek Pass v2 -- Progress Tracker

> See PLAN.md for the full implementation plan.
> This file tracks what's been done, what's in progress, and what's next.

## Status: Phase 2 COMPLETE -- Ready for Phase 3

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
- [x] SQLiteStorage verified: full round-trip tests pass (camera, capture, cycle, route, condition, event, weather)
- [x] DynamoStorage implemented (will be tested with LocalStack in Phase 9)
- [x] Existing CLIs (traffic_cam_monitor.py, query_data.py) still import and work

### Phase 3: Route Planning (NEXT)

- [ ] `route.py` -- Google Directions API (Riverton --> Hanna)
- [ ] Decode route polyline into lat/lng points
- [ ] Haversine distance calculation for camera-to-route matching
- [ ] Filter UDOT cameras within ~2km of route

### Phase 4-10: See PLAN.md

---

## Phase Summary

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Project Scaffolding | DONE |
| 2 | Storage Abstraction (DynamoDB + SQLite) | DONE |
| 3 | Route Planning (Google Directions API) | Next |
| 4 | UDOT API Expansion (all endpoints) | Not Started |
| 5 | Refactor Monitor (route-aware orchestrator) | Not Started |
| 6 | Vue Frontend -- Layout + Map | Not Started |
| 7 | Vue Frontend -- Data + Components | Not Started |
| 8 | CDK Infrastructure | Not Started |
| 9 | LocalStack Integration | Not Started |
| 10 | Deploy + Test | Not Started |

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
- Completed Phase 1 scaffolding:
  - Vue 3 + TypeScript (Vite, Router, Pinia, Leaflet)
  - CDK stack (DynamoDB, S3, Lambda, EventBridge)
  - Docker Compose (LocalStack)
  - Updated pyproject.toml to v0.2.0 with all new deps
  - .gitignore, poe tasks, verification complete
- Completed Phase 2 storage abstraction:
  - settings.py, expanded models.py, storage.py
  - SQLiteStorage + DynamoStorage + Protocol + factory
  - Full round-trip tests passing for SQLiteStorage

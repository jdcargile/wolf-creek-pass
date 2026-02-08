# Wolf Creek Pass

Monitors SR-35 traffic cameras hourly via the UDOT API, analyzes images with Claude Vision for road conditions (snow, vehicles, animals), and stores results in SQLite.

## Setup

Requires Python 3.11+.

```bash
uv sync
cp .env.example .env
# Fill in your API keys in .env
```

## Usage

### Monitor

Fetches camera images, analyzes them, and stores results. Runs hourly by default.

```bash
uv run python traffic_cam_monitor.py          # Run on a loop (hourly)
uv run python traffic_cam_monitor.py --once    # Single capture cycle, then exit
```

### Query

Query the captured data. Defaults to `recent` if no subcommand is given.

```bash
uv run python query_data.py                   # Recent captures (default)
uv run python query_data.py recent -n 50      # Recent, limit 50
uv run python query_data.py snow              # 24-hour snow summary
uv run python query_data.py animals           # Animal sightings
```

### Poe Tasks

```bash
poe monitor        # Start the hourly monitor
poe query          # Recent captures
poe query-snow     # Snow summary
poe query-animals  # Animal sightings
```

## Stack

- **CLI**: Click
- **Data validation / settings**: Pydantic + pydantic-settings (loads `.env`)
- **Vision analysis**: Anthropic (Claude Vision)
- **Output**: Rich (styled tables)
- **Storage**: SQLite (`traffic_cams.db`) + local image files (`images/`)
- **Scheduling**: `schedule` library

## TODO

- [ ] Deploy to cloud platform -- evaluate GitHub Actions cron, Azure Function Timer Trigger, or other. Currently requires running locally.
- [ ] Pick a hosted DB to replace SQLite if deploying to ephemeral runners
- [ ] Initial git commit + .gitignore

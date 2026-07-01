# MCP Servers

This folder contains the MCP servers used to centralize each external
integration. The Flask app never talks to Google or Open-Meteo directly -
it goes through `providers/` (see [`providers/README.md`](/providers) if
present, or `providers/__init__.py`), and the adapters in `providers/` are
thin wrappers around the same code these MCP servers expose as tools. That
means one implementation serves two consumers: the web app (in-process,
with caching) and any MCP-aware agent/client (via the tools below).

## `server.py` - Google integrations
### Tools exposed
- `geocode_address(query)`
- `reverse_geocode(lat, lon)`

### Run locally
```bash
python -m mcp_server.server
```

### Environment variables
- `GOOGLE_MAPS_API_KEY`: required
- `GOOGLE_GEOCODING_BASE_URL`, `GOOGLE_PLACES_NEARBY_BASE_URL`, `GOOGLE_PLACES_AUTOCOMPLETE_BASE_URL`: optional overrides for tests/mocks

## `weather_server.py` - Open-Meteo integrations
### Tools exposed
- `get_marine_conditions(lat, lon)` -> wave_height, wave_direction, wave_period
- `get_forecast_conditions(lat, lon)` -> wind_speed, wind_direction, temperature_c, precipitation, weather_code

### Run locally
```bash
python -m mcp_server.weather_server
```

No environment variables required (Open-Meteo does not need an API key today).

## Why this structure matters for swapping providers later
- The Flask app depends only on the interfaces in `providers/ports.py`.
- `providers/google.py` and `providers/openmeteo.py` are the only files that
  know about Google/Open-Meteo specifically, and they're the same code these
  MCP servers call into.
- Replacing an API (e.g. moving off Google Places, or from Open-Meteo to a
  paid marine data provider) means: write a new adapter implementing the
  matching Protocol in `providers/ports.py`, register it in
  `providers/registry.py`, flip the relevant env var
  (`MARINE_PROVIDER` / `FORECAST_PROVIDER` / `GEOCODING_PROVIDER` /
  `PLACES_PROVIDER`), and optionally add a matching MCP tool here. Flask
  routes, `services/`, and `ranking/` never need to change.

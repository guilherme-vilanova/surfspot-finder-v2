"""MCP server exposing the same Open-Meteo provider code used by the Flask app.

providers/openmeteo.py has no dependency on Flask or on this file - this
server just puts an MCP tool interface in front of it, so any MCP-aware
client/agent (not just this web app) can ask "what are the waves/wind doing
at this coordinate right now". Caching is intentionally NOT applied here
(unlike the web app, which wraps these providers in services/caching.py) to
keep this server a thin, stateless pass-through; add it back here too if
this server ends up serving high-traffic agent workloads.
"""

from mcp.server.fastmcp import FastMCP

from providers.openmeteo import OpenMeteoForecastProvider, OpenMeteoMarineProvider

mcp = FastMCP("surfspot-weather")
marine_provider = OpenMeteoMarineProvider()
forecast_provider = OpenMeteoForecastProvider()


@mcp.tool()
def get_marine_conditions(lat: float, lon: float):
    """Get current wave height (m), wave direction (deg) and wave period (s) at a coordinate."""
    return marine_provider.get_marine_conditions(lat, lon)


@mcp.tool()
def get_forecast_conditions(lat: float, lon: float):
    """Get current wind speed/direction, temperature, precipitation and weather code at a coordinate."""
    return forecast_provider.get_forecast_conditions(lat, lon)


if __name__ == "__main__":
    mcp.run()

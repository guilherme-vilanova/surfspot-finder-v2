"""Port interfaces for external data providers.

These are the contracts the rest of the app is allowed to depend on. Anything
that talks to a real external API (Open-Meteo, Google, or a future
replacement) must implement one of these Protocols. Nothing outside
`providers/` should import a concrete HTTP client directly.
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


class ProviderError(Exception):
    """Raised when any external provider (marine, forecast, geocoding, places)
    fails in a way callers should surface as a user-facing message.

    Concrete provider errors (e.g. mcp_server.location_service.LocationServiceError)
    subclass this so calling code can catch `ProviderError` once instead of
    knowing about every provider-specific exception type.
    """


@runtime_checkable
class MarineDataProvider(Protocol):
    name: str

    def get_marine_conditions(self, lat: float, lon: float) -> Dict[str, Optional[float]]:
        """Return wave_height (m), wave_direction (deg), wave_period (s)."""


@runtime_checkable
class ForecastProvider(Protocol):
    name: str

    def get_forecast_conditions(self, lat: float, lon: float) -> Dict[str, Optional[float]]:
        """Return wind_speed, wind_direction, temperature_c, precipitation, weather_code."""


@runtime_checkable
class GeocodingProvider(Protocol):
    name: str

    def geocode_address(self, query: str) -> Dict[str, Any]:
        """Resolve free-text into formatted_address/lat/lon/place_id."""

    def reverse_geocode(self, lat: float, lon: float) -> Dict[str, Any]:
        """Resolve coordinates into formatted_address/lat/lon/place_id."""


@runtime_checkable
class PlacesProvider(Protocol):
    name: str

    def find_nearby_beaches(self, lat: float, lon: float, radius_km: float) -> List[Dict[str, Any]]:
        """Discover nearby beaches within radius_km of (lat, lon)."""

    def autocomplete_places(self, query: str) -> List[Dict[str, Any]]:
        """Return location autocomplete suggestions for free-text query."""

"""Google adapters: geocoding and places, implementing providers.ports.

The actual HTTP/session logic lives in mcp_server/ (google_client.py +
location_service.py), which is also exposed directly as MCP tools in
mcp_server/server.py. That means the same Google integration code is usable
both in-process by the Flask app (through this thin adapter) and by any MCP
client/agent that talks to mcp_server/server.py - one implementation, two
consumers.

This module is the translation boundary: GoogleLocationService raises
LocationServiceError (its own exception, so mcp_server/ stays usable
standalone without depending on providers/), and here we re-raise it as
providers.ports.ProviderError so the rest of the app only has to catch one
exception type regardless of which provider is active.
"""

from typing import Any, Dict, List, Optional

from mcp_server.location_service import GoogleLocationService, LocationServiceError

from .ports import ProviderError

__all__ = ["GoogleGeocodingProvider", "GooglePlacesProvider"]


class GoogleGeocodingProvider:
    """Implements providers.ports.GeocodingProvider via GoogleLocationService."""

    name = "google"

    def __init__(self, location_service: Optional[GoogleLocationService] = None):
        self.location_service = location_service or GoogleLocationService.from_env()

    def geocode_address(self, query: str) -> Dict[str, Any]:
        try:
            return self.location_service.geocode_address(query)
        except LocationServiceError as exc:
            raise ProviderError(str(exc)) from exc

    def reverse_geocode(self, lat: float, lon: float) -> Dict[str, Any]:
        try:
            return self.location_service.reverse_geocode(lat, lon)
        except LocationServiceError as exc:
            raise ProviderError(str(exc)) from exc


class GooglePlacesProvider:
    """Implements providers.ports.PlacesProvider via GoogleLocationService."""

    name = "google"

    def __init__(self, location_service: Optional[GoogleLocationService] = None):
        self.location_service = location_service or GoogleLocationService.from_env()

    def find_nearby_beaches(self, lat: float, lon: float, radius_km: float) -> List[Dict[str, Any]]:
        try:
            return self.location_service.find_nearby_beaches(lat, lon, radius_km)
        except LocationServiceError as exc:
            raise ProviderError(str(exc)) from exc

    def autocomplete_places(self, query: str) -> List[Dict[str, Any]]:
        try:
            return self.location_service.autocomplete_places(query)
        except LocationServiceError as exc:
            raise ProviderError(str(exc)) from exc

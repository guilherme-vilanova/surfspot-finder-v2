"""Builds the active set of providers from simple string names.

The names normally come from config/environment variables (see
surfweb/config.py: MARINE_PROVIDER, FORECAST_PROVIDER, GEOCODING_PROVIDER,
PLACES_PROVIDER). To add support for a new API:

1. Write an adapter class implementing the relevant Protocol in ports.py.
2. Register it in the matching dict below.
3. Point the env var at the new name. No other code changes.
"""

from dataclasses import dataclass
from typing import Callable, Dict

from .google import GoogleGeocodingProvider, GooglePlacesProvider
from .openmeteo import OpenMeteoForecastProvider, OpenMeteoMarineProvider
from .openweathermap import OpenWeatherMapForecastProvider
from .ports import ForecastProvider, GeocodingProvider, MarineDataProvider, PlacesProvider


@dataclass(frozen=True)
class ProviderBundle:
    marine: MarineDataProvider
    forecast: ForecastProvider
    geocoding: GeocodingProvider
    places: PlacesProvider


MARINE_PROVIDERS: Dict[str, Callable[[], MarineDataProvider]] = {
    "open_meteo": OpenMeteoMarineProvider,
}

FORECAST_PROVIDERS: Dict[str, Callable[[], ForecastProvider]] = {
    "open_meteo": OpenMeteoForecastProvider,
    "openweathermap": OpenWeatherMapForecastProvider,
}

GEOCODING_PROVIDERS: Dict[str, Callable[[], GeocodingProvider]] = {
    "google": GoogleGeocodingProvider,
}

PLACES_PROVIDERS: Dict[str, Callable[[], PlacesProvider]] = {
    "google": GooglePlacesProvider,
}


def _build(registry, key, kind):
    try:
        factory = registry[key]
    except KeyError as exc:
        available = ", ".join(sorted(registry)) or "none"
        raise ValueError(f"Unknown {kind} provider '{key}'. Available: {available}.") from exc
    return factory()


def build_provider_bundle(
    marine_provider: str = "open_meteo",
    forecast_provider: str = "open_meteo",
    geocoding_provider: str = "google",
    places_provider: str = "google",
) -> ProviderBundle:
    geocoding = _build(GEOCODING_PROVIDERS, geocoding_provider, "geocoding")

    # Google geocoding and places share one underlying location service/session
    # when both are Google-backed, instead of opening two separate clients.
    if places_provider == "google" and geocoding_provider == "google":
        places = GooglePlacesProvider(location_service=geocoding.location_service)
    else:
        places = _build(PLACES_PROVIDERS, places_provider, "places")

    return ProviderBundle(
        marine=_build(MARINE_PROVIDERS, marine_provider, "marine"),
        forecast=_build(FORECAST_PROVIDERS, forecast_provider, "forecast"),
        geocoding=geocoding,
        places=places,
    )

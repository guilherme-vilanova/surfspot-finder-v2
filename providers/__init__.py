"""External data providers, exposed behind small port interfaces (ports.py).

The rest of the app (services/, ranking/) never imports requests-based clients
directly. It only depends on the interfaces in `providers.ports`. Swapping a
backing API later (e.g. Open-Meteo -> Stormglass, Google Places -> Foursquare)
means writing a new adapter class and registering it in `providers.registry`,
without touching services, ranking, or Flask routes.
"""

from .ports import (
    ForecastProvider,
    GeocodingProvider,
    MarineDataProvider,
    PlacesProvider,
    ProviderError,
)
from .registry import ProviderBundle, build_provider_bundle

__all__ = [
    "ForecastProvider",
    "GeocodingProvider",
    "MarineDataProvider",
    "PlacesProvider",
    "ProviderError",
    "ProviderBundle",
    "build_provider_bundle",
]

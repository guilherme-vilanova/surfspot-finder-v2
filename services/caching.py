"""Caching decorators around providers.ports.MarineDataProvider/ForecastProvider.

Keeping caching as a decorator (instead of baking it into the providers or
into app.py) means a provider implementation only ever worries about talking
to its API; whether/how long results get cached is decided here, once, for
any provider that gets plugged in.
"""

from typing import Dict, Optional

from cache.ttl import LayeredCache, get_cache_key

DEFAULT_CACHE_TTL_SECONDS = 600


class CachedMarineProvider:
    name_prefix = "marine"

    def __init__(self, provider, disk_cache, ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS):
        self._provider = provider
        self._cache = LayeredCache("marine", disk_cache, ttl_seconds)

    @property
    def name(self) -> str:
        return self._provider.name

    def get_marine_conditions(self, lat: float, lon: float) -> Dict[str, Optional[float]]:
        key = get_cache_key(lat, lon)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        result = self._provider.get_marine_conditions(lat, lon)
        self._cache.set(key, result)
        return result

    def clear_cache(self):
        self._cache.clear()


class CachedForecastProvider:
    name_prefix = "forecast"

    def __init__(self, provider, disk_cache, ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS):
        self._provider = provider
        self._cache = LayeredCache("forecast", disk_cache, ttl_seconds)

    @property
    def name(self) -> str:
        return self._provider.name

    def get_forecast_conditions(self, lat: float, lon: float) -> Dict[str, Optional[float]]:
        key = get_cache_key(lat, lon)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        result = self._provider.get_forecast_conditions(lat, lon)
        self._cache.set(key, result)
        return result

    def clear_cache(self):
        self._cache.clear()

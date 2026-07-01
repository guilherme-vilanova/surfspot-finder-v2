"""Composition root: wires providers + ranking + caching into request-ready services.

Flask routes only ever touch this container (via current_app.extensions),
never providers/ or ranking/ directly. This is the one place that knows how
everything is plugged together, which is what makes swapping a provider or
the ranking strategy a one-line config change instead of a code change.
"""

from persistent_cache import PersistentTTLCache
from providers import build_provider_bundle
from ranking import build_ranking_strategy
from services.beach_discovery import BeachDiscoveryService
from services.beach_evaluator import BeachEvaluator
from services.caching import CachedForecastProvider, CachedMarineProvider
from services.location_resolver import LocationResolver
from services.search_orchestrator import SearchOrchestrator


class ServiceContainer:
    def __init__(self, config):
        self.config = config
        self.disk_cache = PersistentTTLCache(config.CACHE_PATH)

        self.providers = build_provider_bundle(
            marine_provider=config.MARINE_PROVIDER,
            forecast_provider=config.FORECAST_PROVIDER,
            geocoding_provider=config.GEOCODING_PROVIDER,
            places_provider=config.PLACES_PROVIDER,
        )

        self._cached_marine = CachedMarineProvider(
            self.providers.marine, self.disk_cache, config.CACHE_TTL_SECONDS
        )
        self._cached_forecast = CachedForecastProvider(
            self.providers.forecast, self.disk_cache, config.CACHE_TTL_SECONDS
        )

        ranking_strategy = build_ranking_strategy(config.RANKING_STRATEGY)

        self.location_resolver = LocationResolver(self.providers.geocoding)
        self.beach_discovery_service = BeachDiscoveryService(
            self.providers.places, self.disk_cache, config.CACHE_TTL_SECONDS
        )
        self.beach_evaluator = BeachEvaluator(self._cached_marine, self._cached_forecast, ranking_strategy)
        self.search_orchestrator = SearchOrchestrator(
            self.beach_discovery_service,
            self.beach_evaluator,
            self.disk_cache,
            config.CACHE_TTL_SECONDS,
        )

    def clear_caches(self):
        """Used by tests to isolate cache state between cases."""
        self.beach_discovery_service.clear_cache()
        self.search_orchestrator.clear_cache()
        self._cached_marine.clear_cache()
        self._cached_forecast.clear_cache()

"""Top-level search pipeline: candidate discovery -> parallel evaluation -> ranking -> cache."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from cache.ttl import LayeredCache
from services.beach_evaluator import is_dynamic_beach_source

logger = logging.getLogger(__name__)

MIN_BEACHES_TO_EVALUATE = 12
MAX_BEACHES_TO_EVALUATE = 18
SEARCH_CACHE_NAMESPACE = "search_v2"
DEFAULT_CACHE_TTL_SECONDS = 600
RADIUS_EXPANSION_STEPS = ()


class SearchOrchestrator:
    def __init__(
        self,
        beach_discovery_service,
        beach_evaluator,
        disk_cache,
        cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
        max_workers: int = 8,
    ):
        self.beach_discovery_service = beach_discovery_service
        self.beach_evaluator = beach_evaluator
        self._cache = LayeredCache(SEARCH_CACHE_NAMESPACE, disk_cache, cache_ttl_seconds)
        self.max_workers = max_workers

    def build_beach_rankings(self, origin, max_distance_km, result_limit, skill_level):
        cache_key = (
            round(origin["lat"], 4),
            round(origin["lon"], 4),
            max_distance_km,
            result_limit,
            skill_level,
        )
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        nearby_beaches = self.beach_discovery_service.find_candidate_beaches(origin, max_distance_km)

        if not nearby_beaches:
            final_result = (origin, [])
            self._cache.set(cache_key, final_result)
            return final_result

        evaluation_limit = min(
            max(result_limit * 3, MIN_BEACHES_TO_EVALUATE),
            MAX_BEACHES_TO_EVALUATE,
            len(nearby_beaches),
        )
        beaches_to_evaluate = nearby_beaches[:evaluation_limit]

        results = []
        max_workers = min(self.max_workers, len(beaches_to_evaluate))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.beach_evaluator.evaluate, beach, skill_level): beach
                for beach in beaches_to_evaluate
            }

            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception:
                    beach = futures[future]
                    logger.warning("Unexpected error evaluating %s", beach.get("name"), exc_info=True)

        local_results = [item for item in results if not is_dynamic_beach_source(item.get("source", "local"))]
        dynamic_results = [
            item
            for item in results
            if is_dynamic_beach_source(item.get("source")) and item.get("has_marine_signal", False)
        ]
        results = local_results + dynamic_results

        results.sort(
            key=lambda item: (
                -item["score"],
                -item["wave_score"],
                -item["wind_score"],
                item["distance_km"],
                item["name"],
            )
        )

        final_result = (origin, results[:result_limit])
        self._cache.set(cache_key, final_result)
        return final_result

    def build_rankings_with_radius_fallback(self, origin, max_distance_km, result_limit, skill_level):
        attempted_radius = max_distance_km
        origin_result, beaches = self.build_beach_rankings(origin, attempted_radius, result_limit, skill_level)

        if beaches:
            return origin_result, beaches, attempted_radius, None

        for expanded_radius in RADIUS_EXPANSION_STEPS:
            if expanded_radius <= attempted_radius:
                continue

            origin_result, beaches = self.build_beach_rankings(origin, expanded_radius, result_limit, skill_level)
            if beaches:
                message = (
                    f"No surfable beaches were found within {attempted_radius} km. "
                    f"Showing the nearest options within {expanded_radius} km instead."
                )
                return origin_result, beaches, expanded_radius, message

        return origin_result, beaches, attempted_radius, None

    def clear_cache(self):
        self._cache.clear()

"""Finds candidate beaches near an origin, deduplicated and radius-filtered."""

from math import atan2, cos, radians, sin, sqrt

from cache.ttl import LayeredCache
from surf_metadata import canonical_beach_name

BEACH_DISCOVERY_CACHE_NAMESPACE = "beach_discovery_v2"
DEFAULT_CACHE_TTL_SECONDS = 600


def haversine_km(lat1, lon1, lat2, lon2):
    earth_radius = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return earth_radius * c


class BeachDiscoveryService:
    def __init__(self, places_provider, disk_cache, cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS):
        self.places_provider = places_provider
        self._cache = LayeredCache(BEACH_DISCOVERY_CACHE_NAMESPACE, disk_cache, cache_ttl_seconds)

    def find_candidate_beaches(self, origin, max_distance_km):
        cache_key = (round(origin["lat"], 4), round(origin["lon"], 4), max_distance_km)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        dynamic_beaches = self.places_provider.find_nearby_beaches(
            origin["lat"], origin["lon"], max_distance_km
        )

        if not dynamic_beaches:
            self._cache.set(cache_key, [])
            return []

        combined = {}
        for beach in dynamic_beaches:
            distance_km = haversine_km(origin["lat"], origin["lon"], beach["lat"], beach["lon"])
            if distance_km > max_distance_km:
                continue

            beach_copy = beach.copy()
            beach_copy["distance_km"] = round(distance_km, 1)
            beach_copy.setdefault("source", "local")
            beach_key = canonical_beach_name(beach_copy["name"])
            existing = combined.get(beach_key)

            if existing is None or beach_copy["distance_km"] < existing["distance_km"]:
                combined[beach_key] = beach_copy

        nearby_beaches = sorted(combined.values(), key=lambda beach: (beach["distance_km"], beach["name"]))
        self._cache.set(cache_key, nearby_beaches)
        return nearby_beaches

    def clear_cache(self):
        self._cache.clear()

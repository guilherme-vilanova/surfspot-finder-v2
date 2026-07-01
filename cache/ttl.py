import time
from typing import Any, Dict, Tuple


def get_cache_key(lat: float, lon: float) -> Tuple[float, float]:
    return (round(lat, 4), round(lon, 4))


def cache_get(cache_dict: Dict[Any, Any], key: Any):
    entry = cache_dict.get(key)
    if not entry:
        return None

    expires_at, value = entry
    if time.time() > expires_at:
        del cache_dict[key]
        return None

    return value


def cache_set(cache_dict: Dict[Any, Any], key: Any, value: Any, ttl_seconds: float):
    cache_dict[key] = (time.time() + ttl_seconds, value)


class LayeredCache:
    """In-memory TTL cache backed by a persistent (disk) cache for durability
    across process restarts. Each instance owns one namespace so unrelated
    caches (marine readings vs. search results) never collide and can be
    versioned/cleared independently.
    """

    def __init__(self, namespace: str, disk_cache, default_ttl_seconds: float):
        self.namespace = namespace
        self.disk_cache = disk_cache
        self.default_ttl_seconds = default_ttl_seconds
        self._memory: Dict[Any, Any] = {}

    @staticmethod
    def _disk_key(key):
        return list(key) if isinstance(key, tuple) else key

    def get(self, key: Any):
        memory_value = cache_get(self._memory, key)
        if memory_value is not None:
            return memory_value

        disk_value = self.disk_cache.get(self.namespace, self._disk_key(key))
        if disk_value is not None:
            cache_set(self._memory, key, disk_value, self.default_ttl_seconds)
            return disk_value

        return None

    def set(self, key: Any, value: Any, ttl_seconds: float = None):
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        cache_set(self._memory, key, value, ttl)
        self.disk_cache.set(self.namespace, self._disk_key(key), value, ttl)

    def clear(self):
        self._memory.clear()

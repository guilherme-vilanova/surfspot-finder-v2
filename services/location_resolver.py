"""Resolves a search origin: either browser coordinates or a geocoded text query."""

from providers.ports import ProviderError


def build_coordinate_label(lat, lon):
    return f"Current location ({lat:.4f}, {lon:.4f})"


class LocationResolver:
    def __init__(self, geocoding_provider):
        self.geocoding_provider = geocoding_provider

    def resolve_origin(self, location_query, origin_lat, origin_lon, origin_source, resolved_location_label):
        if origin_lat is not None and origin_lon is not None:
            label = (resolved_location_label or "").strip() or build_coordinate_label(origin_lat, origin_lon)
            source = origin_source or "browser"
            return {
                "name": label,
                "lat": origin_lat,
                "lon": origin_lon,
                "source": source,
            }, None

        query = (location_query or "").strip()
        if not query:
            return None, "Enter a location or use your current location."

        try:
            resolved = self.geocoding_provider.geocode_address(query)
        except ProviderError as exc:
            return None, str(exc)

        return {
            "name": resolved["formatted_address"],
            "lat": resolved["lat"],
            "lon": resolved["lon"],
            "source": origin_source or "manual",
        }, None

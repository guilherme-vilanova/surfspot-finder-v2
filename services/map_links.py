"""Builds Google Maps embed/link URLs for the winning beach card."""

from urllib.parse import quote_plus


def build_beach_map_embed_url(beach, google_maps_api_key):
    place_id = beach.get("place_id")
    if google_maps_api_key and place_id:
        return (
            "https://www.google.com/maps/embed/v1/place"
            f"?key={quote_plus(google_maps_api_key)}&q={quote_plus(f'place_id:{place_id}')}&zoom=12"
        )

    return f"https://maps.google.com/maps?q=loc:{beach['lat']},{beach['lon']}&z=12&output=embed"


def build_beach_google_maps_url(beach):
    place_id = beach.get("place_id")
    if place_id:
        query = f"{beach['name']}, {beach.get('region', 'Brazil')}"
        return (
            "https://www.google.com/maps/search/?api=1"
            f"&query={quote_plus(query)}&query_place_id={quote_plus(place_id)}"
        )

    return f"https://www.google.com/maps/search/?api=1&query={beach['lat']},{beach['lon']}"

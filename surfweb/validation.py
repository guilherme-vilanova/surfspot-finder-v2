"""Server-side validation for anything coming from the request.

The client already constrains most of these (select dropdowns, browser
geolocation), but the server must never trust that - a request can always be
built by hand, and previously a bad `result_limit` would raise an unhandled
ValueError (int(...) on garbage) and return a bare 500.
"""

from typing import Optional


class ValidationError(ValueError):
    """A request parameter failed validation; message is safe to show the user."""


def parse_optional_float(value):
    if value in (None, ""):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_latitude(value) -> Optional[float]:
    lat = parse_optional_float(value)
    if lat is None:
        return None
    if not -90.0 <= lat <= 90.0:
        raise ValidationError("Latitude must be between -90 and 90.")
    return lat


def parse_longitude(value) -> Optional[float]:
    lon = parse_optional_float(value)
    if lon is None:
        return None
    if not -180.0 <= lon <= 180.0:
        raise ValidationError("Longitude must be between -180 and 180.")
    return lon


def clamp_radius_km(value, min_km, max_km, default_km):
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        return default_km

    return max(min_km, min(numeric, max_km))


def parse_result_limit(value, allowed_limits, default_limit):
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        return default_limit

    if numeric not in allowed_limits:
        return default_limit

    return numeric


def parse_skill_level(value, allowed_levels, default_level):
    candidate = (value or "").strip().lower()
    if candidate not in allowed_levels:
        return default_level
    return candidate


def sanitize_location_query(value, max_length: int = 200) -> str:
    text = (value or "").strip()
    # Strip control/non-printable characters a hand-crafted request could send.
    text = "".join(char for char in text if char.isprintable())
    return text[:max_length]

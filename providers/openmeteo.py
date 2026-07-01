"""Open-Meteo adapters: marine (wave) data and weather forecast (wind/temp/rain).

Both classes implement the `providers.ports` Protocols. If this API ever gets
replaced (rate limits, accuracy, pricing), a new adapter implementing the same
two methods can be dropped into `providers/registry.py` and nothing in
services/ or ranking/ needs to change.
"""

from typing import Dict, Optional

import requests

MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

DEFAULT_HTTP_RETRIES = 3
DEFAULT_MARINE_TIMEOUT_SECONDS = 12
DEFAULT_FORECAST_TIMEOUT_SECONDS = 10


def safe_get(url, params, timeout=10, retries=DEFAULT_HTTP_RETRIES):
    """GET with a small retry budget for transient timeouts/network errors."""
    last_error = None

    for _ in range(retries):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.Timeout as exc:
            last_error = exc
        except requests.RequestException as exc:
            last_error = exc

    raise last_error


def _first_value(hourly_dict, key):
    values = hourly_dict.get(key, [])
    return values[0] if values else None


def has_surf_marine_signal(marine: Dict[str, Optional[float]]) -> bool:
    """Whether a marine reading indicates open-ocean surf conditions at all.

    Used to avoid treating landlocked/sheltered "beach" places returned by
    Google Places as real surf spots.
    """
    wave_height = marine.get("wave_height")
    wave_period = marine.get("wave_period")

    if wave_height is None and wave_period is None:
        return False

    if wave_height is not None and wave_height >= 0.4:
        return True

    if wave_period is not None and wave_period >= 5:
        return True

    return False


class OpenMeteoMarineProvider:
    """Implements providers.ports.MarineDataProvider using Open-Meteo Marine API."""

    name = "open_meteo"

    def __init__(
        self,
        base_url: str = MARINE_URL,
        timeout: int = DEFAULT_MARINE_TIMEOUT_SECONDS,
        retries: int = DEFAULT_HTTP_RETRIES,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.retries = retries

    def get_marine_conditions(self, lat: float, lon: float) -> Dict[str, Optional[float]]:
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "wave_height,wave_direction,wave_period",
            "forecast_days": 1,
            "timezone": "auto",
        }

        response = safe_get(self.base_url, params=params, timeout=self.timeout, retries=self.retries)
        hourly = response.json().get("hourly", {})

        return {
            "wave_height": _first_value(hourly, "wave_height"),
            "wave_direction": _first_value(hourly, "wave_direction"),
            "wave_period": _first_value(hourly, "wave_period"),
        }


class OpenMeteoForecastProvider:
    """Implements providers.ports.ForecastProvider using Open-Meteo Forecast API."""

    name = "open_meteo"

    def __init__(
        self,
        base_url: str = FORECAST_URL,
        timeout: int = DEFAULT_FORECAST_TIMEOUT_SECONDS,
        retries: int = DEFAULT_HTTP_RETRIES,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.retries = retries

    def get_forecast_conditions(self, lat: float, lon: float) -> Dict[str, Optional[float]]:
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "wind_speed_10m,wind_direction_10m,temperature_2m,precipitation,weather_code",
            "forecast_days": 1,
            "timezone": "auto",
        }

        response = safe_get(self.base_url, params=params, timeout=self.timeout, retries=self.retries)
        hourly = response.json().get("hourly", {})

        return {
            "wind_speed": _first_value(hourly, "wind_speed_10m"),
            "wind_direction": _first_value(hourly, "wind_direction_10m"),
            "temperature_c": _first_value(hourly, "temperature_2m"),
            "precipitation": _first_value(hourly, "precipitation"),
            "weather_code": _first_value(hourly, "weather_code"),
        }

"""OpenWeatherMap adapter for wind/weather forecast data.

Swapped in for `providers.openmeteo.OpenMeteoForecastProvider` because
Open-Meteo's free/keyless tier rate-limits by *source IP* (600/min,
5,000/hour, 10,000/day). On shared hosting (Render's free plan), that IP is
shared with other tenants, so the app can get 429'd by traffic that has
nothing to do with it. OpenWeatherMap's free tier quota is tied to an *API
key* instead (60 calls/min, 1,000,000/month) - that's what actually fixes
the problem rather than just delaying it.

Implements the same `providers.ports.ForecastProvider` Protocol as
OpenMeteoForecastProvider, so nothing in services/ or ranking/ needs to
change - see providers/registry.py for how it's selected via
FORECAST_PROVIDER=openweathermap. Open-Meteo Marine stays the wave-data
source; it has no comparably-generous free alternative and marine calls are
far lower-volume than forecast calls.
"""

import os
from typing import Dict, Optional

from providers.openmeteo import safe_get
from providers.ports import ProviderError

CURRENT_WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_RETRIES = 3


def _map_condition_code(owm_code: Optional[int]) -> Optional[int]:
    """Translate an OpenWeatherMap condition code into the WMO-style code
    `ranking.presentation.weather_label` already knows how to render, so
    that mapping doesn't need a second copy per forecast provider.

    See https://openweathermap.org/weather-conditions for the OWM code
    ranges (2xx thunderstorm, 3xx drizzle, 5xx rain, 6xx snow, 7xx
    atmosphere/fog-family, 800 clear, 801-804 clouds).
    """
    if owm_code is None:
        return None

    if 200 <= owm_code < 300:
        return 95  # Thunderstorm
    if 300 <= owm_code < 400:
        return 51  # Drizzle
    if 500 <= owm_code < 600:
        return 65 if owm_code in (502, 503, 504, 522, 531) else 61  # Heavy vs. regular rain
    if 600 <= owm_code < 700:
        return 71  # Snow
    if 700 <= owm_code < 800:
        return 45  # Fog/mist/haze/dust family
    if owm_code == 800:
        return 0  # Clear sky
    if owm_code == 801:
        return 1  # Few clouds
    if owm_code == 802:
        return 2  # Scattered clouds
    if owm_code in (803, 804):
        return 3  # Broken/overcast clouds

    return None


class OpenWeatherMapForecastProvider:
    """Implements providers.ports.ForecastProvider using OpenWeatherMap's Current Weather API."""

    name = "openweathermap"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = CURRENT_WEATHER_URL,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        retries: int = DEFAULT_RETRIES,
    ):
        self.api_key = api_key if api_key is not None else os.environ.get("OPENWEATHER_API_KEY", "").strip()
        self.base_url = base_url
        self.timeout = timeout
        self.retries = retries

    def get_forecast_conditions(self, lat: float, lon: float) -> Dict[str, Optional[float]]:
        if not self.api_key:
            raise ProviderError("OPENWEATHER_API_KEY is not configured.")

        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.api_key,
            "units": "metric",
        }

        response = safe_get(self.base_url, params=params, timeout=self.timeout, retries=self.retries)
        payload = response.json()

        wind = payload.get("wind") or {}
        wind_speed_ms = wind.get("speed")
        wind_speed_kmh = wind_speed_ms * 3.6 if wind_speed_ms is not None else None

        rain_mm = (payload.get("rain") or {}).get("1h", (payload.get("rain") or {}).get("3h"))
        snow_mm = (payload.get("snow") or {}).get("1h", (payload.get("snow") or {}).get("3h"))
        precipitation = (rain_mm or 0) + (snow_mm or 0)

        weather_entries = payload.get("weather") or []
        owm_code = weather_entries[0].get("id") if weather_entries else None

        return {
            "wind_speed": wind_speed_kmh,
            "wind_direction": wind.get("deg"),
            "temperature_c": (payload.get("main") or {}).get("temp"),
            "precipitation": precipitation,
            "weather_code": _map_condition_code(owm_code),
        }

"""Turns one beach + its live marine/forecast readings into a scored, display-ready row."""

import logging

from providers.openmeteo import has_surf_marine_signal
from ranking.presentation import (
    classify_color,
    classify_condition,
    degrees_to_cardinal_arrow,
    weather_label,
)

logger = logging.getLogger(__name__)

DEFAULT_WIND_DIRECTIONS = [0, 45, 90, 135, 180, 225, 270, 315]


def is_dynamic_beach_source(source):
    return source == "google_places"


class BeachEvaluator:
    def __init__(self, marine_provider, forecast_provider, ranking_strategy):
        self.marine_provider = marine_provider
        self.forecast_provider = forecast_provider
        self.ranking_strategy = ranking_strategy

    def evaluate(self, beach, skill_level):
        marine = {"wave_height": None, "wave_direction": None, "wave_period": None}
        forecast = {
            "wind_speed": None,
            "wind_direction": None,
            "temperature_c": None,
            "precipitation": None,
            "weather_code": None,
        }
        has_marine_signal = False

        try:
            marine = self.marine_provider.get_marine_conditions(beach["lat"], beach["lon"])
            has_marine_signal = has_surf_marine_signal(marine)
        except Exception:
            logger.warning("Failed to fetch marine conditions for %s", beach.get("name"), exc_info=True)

        should_fetch_forecast = not (is_dynamic_beach_source(beach.get("source")) and not has_marine_signal)
        if should_fetch_forecast:
            try:
                forecast = self.forecast_provider.get_forecast_conditions(beach["lat"], beach["lon"])
            except Exception:
                logger.warning("Failed to fetch forecast conditions for %s", beach.get("name"), exc_info=True)

        breakdown = self.ranking_strategy.score(marine, forecast, beach, skill_level)
        total_score = breakdown.total

        return {
            "name": beach["name"],
            "region": beach.get("region", "Santa Catarina"),
            "source": beach.get("source", "local"),
            "place_id": beach.get("place_id"),
            "lat": beach["lat"],
            "lon": beach["lon"],
            "distance_km": beach["distance_km"],
            "wave_height": marine["wave_height"],
            "wave_direction": marine["wave_direction"],
            "wave_direction_visual": degrees_to_cardinal_arrow(marine["wave_direction"]),
            "wave_period": marine["wave_period"],
            "preferred_swell_label": beach.get("preferred_swell_label", "Any"),
            "wind_speed": forecast["wind_speed"],
            "wind_direction": forecast["wind_direction"],
            "wind_direction_visual": degrees_to_cardinal_arrow(forecast["wind_direction"]),
            "temperature_c": forecast["temperature_c"],
            "precipitation": forecast["precipitation"],
            "weather_code": forecast["weather_code"],
            "weather_label": weather_label(forecast["weather_code"], forecast["precipitation"]),
            "best_wind_label": beach.get("best_wind_label", "Any"),
            "notes": beach.get("notes", "Surf spot in Santa Catarina"),
            "wave_score": breakdown.wave_score,
            "swell_score": breakdown.swell_score,
            "wind_score": breakdown.wind_score,
            "score": total_score,
            "has_marine_signal": has_marine_signal,
            "condition_label": classify_condition(total_score),
            "condition_color": classify_color(total_score),
        }

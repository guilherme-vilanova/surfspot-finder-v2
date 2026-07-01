from dataclasses import dataclass
from typing import Dict, Optional, Protocol, runtime_checkable


@dataclass(frozen=True)
class ScoreBreakdown:
    wave_score: float
    swell_score: float
    wind_score: float

    @property
    def total(self) -> float:
        return self.wave_score + self.swell_score + self.wind_score


@runtime_checkable
class RankingStrategy(Protocol):
    name: str

    def score(
        self,
        marine: Dict[str, Optional[float]],
        forecast: Dict[str, Optional[float]],
        beach: Dict,
        skill_level: str,
    ) -> ScoreBreakdown:
        """Score one beach's current conditions for a given surfer skill level.

        `marine` has wave_height/wave_direction/wave_period.
        `forecast` has wind_speed/wind_direction/temperature_c/precipitation/weather_code.
        `beach` is the beach dict (uses preferred_swell_degrees/best_wind_degrees if present).
        """

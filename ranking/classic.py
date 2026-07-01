"""The original hand-tuned wave/wind/swell heuristic, as its own strategy.

Kept as a single self-contained class implementing RankingStrategy so it can
be replaced or run alongside future scoring models (see ranking/factory.py)
without touching services/, providers/, or Flask routes.
"""

from .ports import ScoreBreakdown

DEFAULT_WIND_DIRECTIONS = [0, 45, 90, 135, 180, 225, 270, 315]


def angle_diff(a: float, b: float) -> float:
    diff = abs(a - b) % 360
    return min(diff, 360 - diff)


class ClassicHeuristicRanking:
    name = "classic"

    def score(self, marine, forecast, beach, skill_level) -> ScoreBreakdown:
        wave_score = self.wave_quality_score(
            marine.get("wave_height"), marine.get("wave_period"), skill_level
        )
        swell_score = self.swell_quality_score(
            marine.get("wave_direction"), beach.get("preferred_swell_degrees")
        )
        wind_score = self.wind_quality_score(
            forecast.get("wind_speed"),
            forecast.get("wind_direction"),
            beach.get("best_wind_degrees", DEFAULT_WIND_DIRECTIONS),
        )
        return ScoreBreakdown(wave_score=wave_score, swell_score=swell_score, wind_score=wind_score)

    @staticmethod
    def wind_quality_score(wind_speed, wind_direction, preferred_directions):
        if wind_speed is None or wind_direction is None:
            return 0

        if not preferred_directions:
            preferred_directions = DEFAULT_WIND_DIRECTIONS

        nearest_diff = min(angle_diff(wind_direction, direction) for direction in preferred_directions)

        score = 0

        if wind_speed < 10:
            score += 3
        elif wind_speed < 18:
            score += 2
        elif wind_speed < 25:
            score += 1

        if nearest_diff <= 30:
            score += 3
        elif nearest_diff <= 60:
            score += 2
        elif nearest_diff <= 90:
            score += 1

        return score

    @staticmethod
    def wave_quality_score(wave_height, wave_period, skill_level):
        if wave_height is None:
            return 0

        score = 0

        if skill_level == "beginner":
            if 0.4 <= wave_height <= 0.9:
                score += 5
            elif 0.9 < wave_height <= 1.1:
                score += 3
            elif 0.25 <= wave_height < 0.4 or 1.1 < wave_height <= 1.3:
                score += 1
            elif 1.3 < wave_height <= 1.5:
                score -= 2
            elif wave_height > 1.5:
                score -= 5
        else:
            if 1.0 <= wave_height <= 2.0:
                score += 5
            elif 0.8 <= wave_height < 1.0 or 2.0 < wave_height <= 2.4:
                score += 3
            elif 0.6 <= wave_height < 0.8 or 2.4 < wave_height <= 3.0:
                score += 1

        if wave_period is not None:
            if wave_period >= 11:
                score += 2
            elif wave_period >= 8:
                score += 1

        return score

    @staticmethod
    def swell_quality_score(wave_direction, preferred_directions):
        if wave_direction is None or not preferred_directions:
            return 0

        nearest_diff = min(angle_diff(wave_direction, direction) for direction in preferred_directions)

        if nearest_diff <= 20:
            return 3
        if nearest_diff <= 45:
            return 2
        if nearest_diff <= 70:
            return 1

        return 0

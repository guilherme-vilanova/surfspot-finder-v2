import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ranking.classic import ClassicHeuristicRanking, angle_diff
from ranking.factory import build_ranking_strategy
from ranking.presentation import (
    classify_color,
    classify_condition,
    degrees_to_cardinal_arrow,
    weather_label,
)


class ClassicHeuristicRankingTests(unittest.TestCase):
    def setUp(self):
        self.strategy = ClassicHeuristicRanking()

    def test_wave_quality_score_favors_small_waves_for_beginners(self):
        self.assertEqual(self.strategy.wave_quality_score(0.6, 10, "beginner"), 6)
        self.assertLess(
            self.strategy.wave_quality_score(2.0, 10, "beginner"),
            self.strategy.wave_quality_score(0.6, 10, "beginner"),
        )

    def test_wave_quality_score_favors_bigger_waves_for_advanced(self):
        self.assertGreater(
            self.strategy.wave_quality_score(1.5, 12, "advanced"),
            self.strategy.wave_quality_score(0.3, 12, "advanced"),
        )

    def test_wind_quality_score_rewards_light_aligned_wind(self):
        self.assertEqual(self.strategy.wind_quality_score(8, 90, [90]), 6)
        self.assertEqual(self.strategy.wind_quality_score(None, 90, [90]), 0)

    def test_swell_quality_score_rewards_matching_direction(self):
        self.assertEqual(self.strategy.swell_quality_score(135, [135, 180]), 3)
        self.assertEqual(self.strategy.swell_quality_score(110, [135, 180]), 2)
        self.assertEqual(self.strategy.swell_quality_score(70, [135, 180]), 1)
        self.assertEqual(self.strategy.swell_quality_score(270, [135, 180]), 0)

    def test_score_combines_all_three_components(self):
        breakdown = self.strategy.score(
            {"wave_height": 1.2, "wave_direction": 135, "wave_period": 10},
            {"wind_speed": 8, "wind_direction": 270},
            {"preferred_swell_degrees": [135, 180], "best_wind_degrees": [270, 315]},
            "advanced",
        )
        self.assertEqual(breakdown.total, breakdown.wave_score + breakdown.swell_score + breakdown.wind_score)

    def test_angle_diff_wraps_around_360(self):
        self.assertEqual(angle_diff(350, 10), 20)


class RankingFactoryTests(unittest.TestCase):
    def test_build_known_strategy(self):
        strategy = build_ranking_strategy("classic")
        self.assertEqual(strategy.name, "classic")

    def test_build_unknown_strategy_raises(self):
        with self.assertRaises(ValueError):
            build_ranking_strategy("does-not-exist")


class PresentationTests(unittest.TestCase):
    def test_classify_condition_thresholds(self):
        self.assertEqual(classify_condition(12), "Excellent")
        self.assertEqual(classify_condition(8), "Good")
        self.assertEqual(classify_condition(5), "Fair")
        self.assertEqual(classify_condition(1), "Poor")

    def test_classify_color_matches_condition(self):
        self.assertEqual(classify_color(12), "green")
        self.assertEqual(classify_color(1), "red")

    def test_degrees_to_cardinal_arrow(self):
        self.assertEqual(degrees_to_cardinal_arrow(0), "N")
        self.assertEqual(degrees_to_cardinal_arrow(90), "E")
        self.assertEqual(degrees_to_cardinal_arrow(None), "N/A")

    def test_weather_label_prioritizes_rain(self):
        self.assertEqual(weather_label(0, 1.0), "Rain")
        self.assertEqual(weather_label(0, 0), "Clear sky")
        self.assertEqual(weather_label(None, 0), "N/A")


if __name__ == "__main__":
    unittest.main()

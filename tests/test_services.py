import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from persistent_cache import PersistentTTLCache
from providers.ports import ProviderError
from ranking.classic import ClassicHeuristicRanking
from services.beach_discovery import BeachDiscoveryService
from services.beach_evaluator import BeachEvaluator, is_dynamic_beach_source
from services.location_resolver import LocationResolver
from services.search_orchestrator import SearchOrchestrator


def _disk_cache(tmp_dir):
    return PersistentTTLCache(Path(tmp_dir) / "cache.json")


class BeachDiscoveryServiceTests(unittest.TestCase):
    def test_deduplicates_equivalent_beach_names_and_filters_by_radius(self):
        with TemporaryDirectory() as tmp_dir:
            places_provider = Mock()
            places_provider.find_nearby_beaches.return_value = [
                {
                    "name": "Praia da Silveira",
                    "region": "Garopaba",
                    "lat": -28.0240,
                    "lon": -48.6210,
                    "source": "google_places",
                },
                {
                    "name": "Silveira",
                    "region": "Garopaba",
                    "lat": -28.0244,
                    "lon": -48.6212,
                    "source": "google_places",
                },
            ]
            service = BeachDiscoveryService(places_provider, _disk_cache(tmp_dir))

            origin = {"name": "Garopaba", "lat": -28.0226, "lon": -48.6138}
            nearby = service.find_candidate_beaches(origin, 50)

            self.assertEqual(len(nearby), 1)
            self.assertEqual(nearby[0]["name"], "Praia da Silveira")

    def test_propagates_provider_error(self):
        with TemporaryDirectory() as tmp_dir:
            places_provider = Mock()
            places_provider.find_nearby_beaches.side_effect = ProviderError("Google Places unavailable")
            service = BeachDiscoveryService(places_provider, _disk_cache(tmp_dir))

            with self.assertRaises(ProviderError):
                service.find_candidate_beaches({"name": "x", "lat": -27.6, "lon": -48.5}, 20)


class BeachEvaluatorTests(unittest.TestCase):
    def test_skips_forecast_for_dynamic_spot_when_marine_fails(self):
        marine_provider = Mock()
        marine_provider.get_marine_conditions.side_effect = Exception("marine timeout")
        forecast_provider = Mock()

        evaluator = BeachEvaluator(marine_provider, forecast_provider, ClassicHeuristicRanking())
        result = evaluator.evaluate(
            {
                "name": "Praia da Silveira",
                "region": "Garopaba",
                "lat": -27.6293,
                "lon": -48.4490,
                "distance_km": 4.5,
                "source": "google_places",
            },
            "advanced",
        )

        self.assertIsNone(result["wind_speed"])
        forecast_provider.get_forecast_conditions.assert_not_called()

    def test_adds_swell_weight_when_metadata_matches(self):
        marine_provider = Mock()
        marine_provider.get_marine_conditions.return_value = {
            "wave_height": 1.3,
            "wave_direction": 135,
            "wave_period": 10,
        }
        forecast_provider = Mock()
        forecast_provider.get_forecast_conditions.return_value = {
            "wind_speed": 8,
            "wind_direction": 270,
            "temperature_c": 23,
            "precipitation": 0,
            "weather_code": 1,
        }

        evaluator = BeachEvaluator(marine_provider, forecast_provider, ClassicHeuristicRanking())
        result = evaluator.evaluate(
            {
                "name": "Praia da Silveira",
                "region": "Garopaba",
                "lat": -28.024,
                "lon": -48.621,
                "distance_km": 2.0,
                "best_wind_degrees": [270, 315],
                "preferred_swell_label": "SE / S",
                "preferred_swell_degrees": [135, 180],
                "source": "google_places",
            },
            "advanced",
        )

        self.assertEqual(result["swell_score"], 3)
        self.assertEqual(result["score"], result["wave_score"] + result["swell_score"] + result["wind_score"])

    def test_is_dynamic_beach_source(self):
        self.assertTrue(is_dynamic_beach_source("google_places"))
        self.assertFalse(is_dynamic_beach_source("local"))


class SearchOrchestratorTests(unittest.TestCase):
    def test_limits_external_evaluation_to_closest_candidates_and_sorts_results(self):
        with TemporaryDirectory() as tmp_dir:
            discovery = Mock()
            discovery.find_candidate_beaches.return_value = [
                {
                    "name": f"Beach {index}",
                    "region": "Florianopolis",
                    "lat": -27.5,
                    "lon": -48.4,
                    "distance_km": float(index),
                    "source": "google_places",
                }
                for index in range(1, 31)
            ]

            evaluator = Mock()
            evaluator.evaluate.side_effect = lambda beach, skill_level: {
                "name": beach["name"],
                "distance_km": beach["distance_km"],
                "source": beach["source"],
                "wave_score": 5,
                "swell_score": 0,
                "wind_score": 4,
                "score": 9,
                "has_marine_signal": True,
            }

            orchestrator = SearchOrchestrator(discovery, evaluator, _disk_cache(tmp_dir))
            origin = {"name": "Florianopolis", "lat": -27.5954, "lon": -48.5480}

            _, results = orchestrator.build_beach_rankings(origin, 80, 5, "advanced")

            self.assertEqual(evaluator.evaluate.call_count, 15)
            self.assertEqual(len(results), 5)

    def test_filters_dynamic_beach_without_marine_signal(self):
        with TemporaryDirectory() as tmp_dir:
            discovery = Mock()
            discovery.find_candidate_beaches.return_value = [
                {
                    "name": "Praia sem mar aberto",
                    "region": "Nearby area",
                    "lat": -30.1,
                    "lon": -51.2,
                    "distance_km": 8.0,
                    "source": "google_places",
                }
            ]
            evaluator = Mock()
            evaluator.evaluate.return_value = {
                "name": "Praia sem mar aberto",
                "distance_km": 8.0,
                "source": "google_places",
                "wave_score": 0,
                "swell_score": 0,
                "wind_score": 2,
                "score": 2,
                "has_marine_signal": False,
            }

            orchestrator = SearchOrchestrator(discovery, evaluator, _disk_cache(tmp_dir))
            origin = {"name": "Porto Alegre", "lat": -30.0346, "lon": -51.2177}

            _, results = orchestrator.build_beach_rankings(origin, 20, 5, "advanced")

            self.assertEqual(results, [])

    def test_radius_fallback_keeps_requested_radius_when_empty_and_no_expansion_steps(self):
        with TemporaryDirectory() as tmp_dir:
            discovery = Mock()
            discovery.find_candidate_beaches.return_value = []
            evaluator = Mock()

            orchestrator = SearchOrchestrator(discovery, evaluator, _disk_cache(tmp_dir))
            origin = {"name": "Porto Alegre", "lat": -30.0346, "lon": -51.2177}

            _, beaches, final_radius, info_message = orchestrator.build_rankings_with_radius_fallback(
                origin, 50, 5, "advanced"
            )

            self.assertEqual(final_radius, 50)
            self.assertEqual(beaches, [])
            self.assertIsNone(info_message)


class LocationResolverTests(unittest.TestCase):
    def test_uses_browser_coordinates_when_present(self):
        resolver = LocationResolver(Mock())
        origin, error = resolver.resolve_origin(None, -27.6, -48.5, "browser", "My spot")

        self.assertIsNone(error)
        self.assertEqual(origin["name"], "My spot")
        self.assertEqual(origin["source"], "browser")

    def test_requires_a_query_when_no_coordinates(self):
        resolver = LocationResolver(Mock())
        origin, error = resolver.resolve_origin("", None, None, "manual", "")

        self.assertIsNone(origin)
        self.assertEqual(error, "Enter a location or use your current location.")

    def test_geocodes_free_text_query(self):
        geocoding_provider = Mock()
        geocoding_provider.geocode_address.return_value = {
            "formatted_address": "Florianopolis, SC, Brazil",
            "lat": -27.5954,
            "lon": -48.5480,
            "place_id": "abc",
        }
        resolver = LocationResolver(geocoding_provider)

        origin, error = resolver.resolve_origin("Florianopolis", None, None, "manual", "")

        self.assertIsNone(error)
        self.assertEqual(origin["name"], "Florianopolis, SC, Brazil")

    def test_surfaces_provider_error_as_message(self):
        geocoding_provider = Mock()
        geocoding_provider.geocode_address.side_effect = ProviderError("Location not found.")
        resolver = LocationResolver(geocoding_provider)

        origin, error = resolver.resolve_origin("Nowhereville", None, None, "manual", "")

        self.assertIsNone(origin)
        self.assertEqual(error, "Location not found.")


if __name__ == "__main__":
    unittest.main()

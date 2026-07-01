import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from providers.ports import ProviderError
from surfweb.config import TestingConfig


def _make_app(cache_dir):
    class _Config(TestingConfig):
        CACHE_PATH = Path(cache_dir) / "cache.json"

    from surfweb import create_app

    return create_app(_Config)


class AppLocationFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.app = _make_app(self.temp_dir.name)
        self.client = self.app.test_client()
        self.container = self.app.extensions["surfspot_container"]

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_requires_location_when_no_origin_is_provided(self):
        response = self.client.post("/", data={})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Enter a location or use your current location.", response.data)

    def test_home_limits_radius_options_to_google_places_range(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'id="location-autocomplete"', response.data)
        self.assertIn(b">30 km<", response.data)
        self.assertIn(b">50 km<", response.data)
        self.assertNotIn(b">120 km<", response.data)

    def test_manual_location_search_uses_geocoding_provider(self):
        with patch.object(
            self.container.providers.geocoding, "geocode_address"
        ) as geocode_mock, patch.object(
            self.container.search_orchestrator, "build_rankings_with_radius_fallback"
        ) as rankings_mock:
            geocode_mock.return_value = {
                "formatted_address": "Florianopolis, State of Santa Catarina, Brazil",
                "lat": -27.5954,
                "lon": -48.5480,
                "place_id": "place-123",
            }
            rankings_mock.return_value = (
                {
                    "name": "Florianopolis, State of Santa Catarina, Brazil",
                    "lat": -27.5954,
                    "lon": -48.5480,
                    "source": "manual",
                },
                [],
                50,
                None,
            )

            response = self.client.post(
                "/",
                data={
                    "location_query": "Florianopolis",
                    "max_distance_km": "50",
                    "result_limit": "5",
                    "skill_level": "beginner",
                },
            )

            self.assertEqual(response.status_code, 200)
            geocode_mock.assert_called_once_with("Florianopolis")
            rankings_mock.assert_called_once()

    def test_manual_location_search_clamps_radius_to_configured_limit(self):
        with patch.object(
            self.container.providers.geocoding, "geocode_address"
        ) as geocode_mock, patch.object(
            self.container.search_orchestrator, "build_rankings_with_radius_fallback"
        ) as rankings_mock:
            geocode_mock.return_value = {
                "formatted_address": "Florianopolis, State of Santa Catarina, Brazil",
                "lat": -27.5954,
                "lon": -48.5480,
                "place_id": "place-123",
            }
            rankings_mock.return_value = (
                {"name": "Florianopolis", "lat": -27.5954, "lon": -48.5480, "source": "manual"},
                [],
                50,
                None,
            )

            self.client.post(
                "/",
                data={
                    "location_query": "Florianopolis",
                    "max_distance_km": "120",
                    "result_limit": "5",
                    "skill_level": "beginner",
                },
            )

            self.assertEqual(rankings_mock.call_args.kwargs["max_distance_km"], 50)

    def test_invalid_result_limit_and_skill_level_do_not_crash(self):
        response = self.client.post(
            "/",
            data={
                "location_query": "x",
                "result_limit": "not-a-number",
                "skill_level": "godlike",
                "max_distance_km": "999999",
            },
        )

        self.assertEqual(response.status_code, 200)

    def test_invalid_latitude_is_rejected_with_friendly_message(self):
        response = self.client.post("/", data={"origin_lat": "999", "origin_lon": "10"})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Latitude must be between", response.data)

    def test_reverse_geocode_endpoint(self):
        with patch.object(self.container.providers.geocoding, "reverse_geocode") as reverse_mock:
            reverse_mock.return_value = {
                "formatted_address": "Joaquina Beach, Florianopolis - SC, Brazil",
                "lat": -27.6293,
                "lon": -48.4490,
                "place_id": "place-456",
            }

            response = self.client.post("/api/reverse-geocode", json={"lat": -27.6293, "lon": -48.4490})

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.get_json()["formatted_address"],
                "Joaquina Beach, Florianopolis - SC, Brazil",
            )

    def test_reverse_geocode_endpoint_validates_latitude(self):
        response = self.client.post("/api/reverse-geocode", json={"lat": 999, "lon": 10})

        self.assertEqual(response.status_code, 400)

    def test_location_autocomplete_endpoint_uses_places_provider(self):
        with patch.object(self.container.providers.places, "autocomplete_places") as autocomplete_mock:
            autocomplete_mock.return_value = [
                {
                    "value": "Laguna, State of Santa Catarina, Brazil",
                    "label": "Laguna, State of Santa Catarina, Brazil",
                    "meta": "State of Santa Catarina, Brazil",
                    "place_id": "place-1",
                }
            ]

            response = self.client.get("/api/location-autocomplete?q=Lagu")

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json()["suggestions"][0]["place_id"], "place-1")
            autocomplete_mock.assert_called_once_with("Lagu")

    def test_home_shows_provider_error_when_beach_discovery_fails(self):
        with patch.object(
            self.container.providers.geocoding, "geocode_address"
        ) as geocode_mock, patch.object(
            self.container.providers.places, "find_nearby_beaches"
        ) as places_mock:
            geocode_mock.return_value = {
                "formatted_address": "Florianopolis, State of Santa Catarina, Brazil",
                "lat": -27.5954,
                "lon": -48.5480,
                "place_id": "place-123",
            }
            places_mock.side_effect = ProviderError("Places API not enabled")

            response = self.client.post(
                "/",
                data={
                    "location_query": "Florianopolis",
                    "max_distance_km": "50",
                    "result_limit": "5",
                    "skill_level": "beginner",
                },
            )

            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Places API not enabled", response.data)


class SecurityHeaderAndLimitTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_security_headers_present(self):
        app = _make_app(self.temp_dir.name)
        response = app.test_client().get("/")

        csp = response.headers.get("Content-Security-Policy", "")
        self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(response.headers.get("X-Frame-Options"), "SAMEORIGIN")
        self.assertIn("default-src 'self'", csp)
        self.assertNotIn("unsafe-inline", csp)

    def test_static_css_and_js_are_served(self):
        app = _make_app(self.temp_dir.name)
        client = app.test_client()

        css_response = client.get("/static/css/app.css")
        js_response = client.get("/static/js/app.js")

        self.assertEqual(css_response.status_code, 200)
        self.assertEqual(js_response.status_code, 200)

    def test_production_requires_secret_key(self):
        class ProdConfig(TestingConfig):
            ENV = "production"
            TESTING = False
            SECRET_KEY = ""

        with self.assertRaises(RuntimeError):
            ProdConfig.resolved_secret_key()

    def test_search_route_is_rate_limited(self):
        class _Config(TestingConfig):
            CACHE_PATH = Path(self.temp_dir.name) / "cache.json"
            RATELIMIT_ENABLED = True
            RATE_LIMIT_SEARCH = "2 per minute"

        from surfweb import create_app

        app = create_app(_Config)
        client = app.test_client()

        statuses = [client.post("/", data={}).status_code for _ in range(4)]

        self.assertIn(429, statuses)


if __name__ == "__main__":
    unittest.main()

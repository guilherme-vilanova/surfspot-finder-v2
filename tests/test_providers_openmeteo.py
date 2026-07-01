import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests

from providers.openmeteo import (
    OpenMeteoForecastProvider,
    OpenMeteoMarineProvider,
    has_surf_marine_signal,
    safe_get,
)


class SafeGetTests(unittest.TestCase):
    @patch("providers.openmeteo.requests.get")
    def test_retries_timeout_before_succeeding(self, requests_get_mock):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"ok": True}
        requests_get_mock.side_effect = [requests.Timeout("slow response"), response]

        result = safe_get("https://example.com", {"q": "test"}, timeout=1, retries=2)

        self.assertIs(result, response)
        self.assertEqual(requests_get_mock.call_count, 2)

    @patch("providers.openmeteo.requests.get")
    def test_raises_after_exhausting_retries(self, requests_get_mock):
        requests_get_mock.side_effect = requests.Timeout("slow response")

        with self.assertRaises(requests.Timeout):
            safe_get("https://example.com", {}, timeout=1, retries=2)


class HasSurfMarineSignalTests(unittest.TestCase):
    def test_requires_meaningful_wave_reading(self):
        self.assertFalse(has_surf_marine_signal({"wave_height": None, "wave_period": None}))
        self.assertFalse(has_surf_marine_signal({"wave_height": 0.1, "wave_period": 2}))
        self.assertTrue(has_surf_marine_signal({"wave_height": 0.5, "wave_period": 3}))
        self.assertTrue(has_surf_marine_signal({"wave_height": 0.2, "wave_period": 6}))


class OpenMeteoMarineProviderTests(unittest.TestCase):
    @patch("providers.openmeteo.requests.get")
    def test_get_marine_conditions_parses_first_hourly_value(self, requests_get_mock):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "hourly": {"wave_height": [1.2, 1.3], "wave_direction": [90], "wave_period": [10]}
        }
        requests_get_mock.return_value = response

        provider = OpenMeteoMarineProvider()
        result = provider.get_marine_conditions(-27.6, -48.4)

        self.assertEqual(result, {"wave_height": 1.2, "wave_direction": 90, "wave_period": 10})


class OpenMeteoForecastProviderTests(unittest.TestCase):
    @patch("providers.openmeteo.requests.get")
    def test_get_forecast_conditions_parses_first_hourly_value(self, requests_get_mock):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "hourly": {
                "wind_speed_10m": [12],
                "wind_direction_10m": [270],
                "temperature_2m": [24],
                "precipitation": [0],
                "weather_code": [1],
            }
        }
        requests_get_mock.return_value = response

        provider = OpenMeteoForecastProvider()
        result = provider.get_forecast_conditions(-27.6, -48.4)

        self.assertEqual(
            result,
            {
                "wind_speed": 12,
                "wind_direction": 270,
                "temperature_c": 24,
                "precipitation": 0,
                "weather_code": 1,
            },
        )


if __name__ == "__main__":
    unittest.main()

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from providers.openweathermap import OpenWeatherMapForecastProvider, _map_condition_code
from providers.ports import ProviderError


class MapConditionCodeTests(unittest.TestCase):
    def test_maps_owm_ranges_to_wmo_style_codes(self):
        self.assertIsNone(_map_condition_code(None))
        self.assertEqual(_map_condition_code(211), 95)  # Thunderstorm
        self.assertEqual(_map_condition_code(301), 51)  # Drizzle
        self.assertEqual(_map_condition_code(500), 61)  # Light rain
        self.assertEqual(_map_condition_code(502), 65)  # Heavy rain
        self.assertEqual(_map_condition_code(601), 71)  # Snow
        self.assertEqual(_map_condition_code(741), 45)  # Fog
        self.assertEqual(_map_condition_code(800), 0)  # Clear sky
        self.assertEqual(_map_condition_code(801), 1)  # Few clouds
        self.assertEqual(_map_condition_code(802), 2)  # Scattered clouds
        self.assertEqual(_map_condition_code(804), 3)  # Overcast


class OpenWeatherMapForecastProviderTests(unittest.TestCase):
    @patch("providers.openmeteo.requests.get")
    def test_get_forecast_conditions_parses_and_converts_units(self, requests_get_mock):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "wind": {"speed": 5, "deg": 270},
            "main": {"temp": 24.3},
            "rain": {"1h": 0.5},
            "weather": [{"id": 500}],
        }
        requests_get_mock.return_value = response

        provider = OpenWeatherMapForecastProvider(api_key="test-key")
        result = provider.get_forecast_conditions(-27.6, -48.4)

        self.assertEqual(
            result,
            {
                "wind_speed": 18.0,  # 5 m/s * 3.6
                "wind_direction": 270,
                "temperature_c": 24.3,
                "precipitation": 0.5,
                "weather_code": 61,
            },
        )

    @patch("providers.openmeteo.requests.get")
    def test_missing_optional_fields_default_to_none_or_zero(self, requests_get_mock):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"weather": [{"id": 800}]}
        requests_get_mock.return_value = response

        provider = OpenWeatherMapForecastProvider(api_key="test-key")
        result = provider.get_forecast_conditions(-27.6, -48.4)

        self.assertEqual(
            result,
            {
                "wind_speed": None,
                "wind_direction": None,
                "temperature_c": None,
                "precipitation": 0,
                "weather_code": 0,
            },
        )

    def test_raises_provider_error_when_api_key_missing(self):
        provider = OpenWeatherMapForecastProvider(api_key="")

        with self.assertRaises(ProviderError):
            provider.get_forecast_conditions(-27.6, -48.4)

    @patch.dict("os.environ", {"OPENWEATHER_API_KEY": "from-env"})
    def test_reads_api_key_from_environment_by_default(self):
        provider = OpenWeatherMapForecastProvider()

        self.assertEqual(provider.api_key, "from-env")


if __name__ == "__main__":
    unittest.main()

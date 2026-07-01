import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from surfweb.validation import (
    ValidationError,
    clamp_radius_km,
    parse_latitude,
    parse_longitude,
    parse_optional_float,
    parse_result_limit,
    parse_skill_level,
    sanitize_location_query,
)


class ValidationTests(unittest.TestCase):
    def test_parse_optional_float_handles_blank_and_garbage(self):
        self.assertIsNone(parse_optional_float(""))
        self.assertIsNone(parse_optional_float(None))
        self.assertIsNone(parse_optional_float("not-a-number"))
        self.assertEqual(parse_optional_float("1.5"), 1.5)

    def test_parse_latitude_rejects_out_of_range(self):
        with self.assertRaises(ValidationError):
            parse_latitude("999")
        self.assertEqual(parse_latitude("-27.6"), -27.6)
        self.assertIsNone(parse_latitude(""))

    def test_parse_longitude_rejects_out_of_range(self):
        with self.assertRaises(ValidationError):
            parse_longitude("-999")
        self.assertEqual(parse_longitude("-48.5"), -48.5)

    def test_clamp_radius_km_falls_back_on_garbage(self):
        self.assertEqual(clamp_radius_km("not-a-number", 30, 50, 50), 50)
        self.assertEqual(clamp_radius_km("9999", 30, 50, 50), 50)
        self.assertEqual(clamp_radius_km("10", 30, 50, 50), 30)

    def test_parse_result_limit_falls_back_on_invalid_choice(self):
        self.assertEqual(parse_result_limit("5", (5, 10), 5), 5)
        self.assertEqual(parse_result_limit("999", (5, 10), 5), 5)
        self.assertEqual(parse_result_limit("nope", (5, 10), 5), 5)

    def test_parse_skill_level_falls_back_on_invalid_choice(self):
        self.assertEqual(parse_skill_level("advanced", ("beginner", "advanced"), "beginner"), "advanced")
        self.assertEqual(parse_skill_level("godlike", ("beginner", "advanced"), "beginner"), "beginner")

    def test_sanitize_location_query_strips_and_truncates(self):
        self.assertEqual(sanitize_location_query("  Floripa  "), "Floripa")
        self.assertEqual(len(sanitize_location_query("a" * 500)), 200)


if __name__ == "__main__":
    unittest.main()

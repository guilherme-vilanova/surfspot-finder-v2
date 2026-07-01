"""Pure display helpers for turning scores/readings into user-facing labels.

Separated from classic.py so swapping the scoring model doesn't force a
rethink of how totals map to "Excellent/Good/Fair/Poor" or colors - and vice
versa, tuning these labels doesn't touch scoring math.
"""


def classify_condition(score: float) -> str:
    if score >= 11:
        return "Excellent"
    if score >= 7:
        return "Good"
    if score >= 4:
        return "Fair"
    return "Poor"


def classify_color(score: float) -> str:
    if score >= 11:
        return "green"
    if score >= 7:
        return "yellow"
    if score >= 4:
        return "orange"
    return "red"


def degrees_to_cardinal_arrow(degrees):
    if degrees is None:
        return "N/A"

    directions = [
        ("N", 0),
        ("NE", 45),
        ("E", 90),
        ("SE", 135),
        ("S", 180),
        ("SW", 225),
        ("W", 270),
        ("NW", 315),
    ]

    normalized = degrees % 360
    closest = min(
        directions,
        key=lambda item: min(abs(normalized - item[1]), 360 - abs(normalized - item[1])),
    )
    return closest[0]


def weather_label(weather_code, precipitation):
    if weather_code is None:
        return "N/A"

    if precipitation is not None and precipitation > 0:
        return "Rain"

    mapping = {
        0: "Clear sky",
        1: "Mostly clear",
        2: "Partly cloudy",
        3: "Cloudy",
        45: "Fog",
        48: "Fog",
        51: "Drizzle",
        53: "Drizzle",
        55: "Drizzle",
        61: "Rain",
        63: "Rain",
        65: "Heavy rain",
        71: "Snow",
        80: "Rain showers",
        81: "Rain showers",
        82: "Heavy showers",
        95: "Thunderstorm",
    }

    return mapping.get(weather_code, "Mixed weather")

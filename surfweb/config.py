"""Central app configuration, sourced from environment variables / .env.

This replaces the scattered module-level constants that used to live in
app.py and mcp_server/config.py. Anything that used to be a magic constant
in app.py should be a class attribute here instead.
"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional local convenience dependency
    def load_dotenv(*args, **kwargs):
        return False

from env_loader import load_local_env

BASE_DIR = Path(__file__).resolve().parents[1]


def _load_env_file():
    if not load_dotenv(BASE_DIR / ".env"):
        load_local_env(BASE_DIR / ".env")


_load_env_file()


def _env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    ENV = os.environ.get("FLASK_ENV", "production").strip().lower()
    DEBUG = _env_bool("FLASK_DEBUG", False)
    TESTING = False

    SECRET_KEY = os.environ.get("SECRET_KEY", "").strip()

    GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()

    # Which provider implementation backs each capability. Swapping an API
    # later means adding an adapter in providers/ and changing one of these.
    MARINE_PROVIDER = os.environ.get("MARINE_PROVIDER", "open_meteo").strip()
    # Open-Meteo's forecast endpoint rate-limits by shared source IP, which
    # bites hard on shared hosting; OpenWeatherMap's free tier is keyed by
    # API key instead, so it's the default here. Set OPENWEATHER_API_KEY to
    # use it, or set FORECAST_PROVIDER=open_meteo to fall back to Open-Meteo.
    FORECAST_PROVIDER = os.environ.get("FORECAST_PROVIDER", "openweathermap").strip()
    GEOCODING_PROVIDER = os.environ.get("GEOCODING_PROVIDER", "google").strip()
    PLACES_PROVIDER = os.environ.get("PLACES_PROVIDER", "google").strip()

    # Which scoring model to use. See ranking/factory.py.
    RANKING_STRATEGY = os.environ.get("RANKING_STRATEGY", "classic").strip()

    CACHE_PATH = Path(os.environ.get("CACHE_PATH", str(BASE_DIR / ".cache" / "surfspot_cache.json")))
    CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "600"))

    MIN_RADIUS_KM = 30
    MAX_RADIUS_KM = 50
    DEFAULT_RADIUS_KM = 50
    ALLOWED_RESULT_LIMITS = (5, 10)
    ALLOWED_SKILL_LEVELS = ("beginner", "advanced")
    MIN_BEACHES_TO_EVALUATE = 12
    MAX_BEACHES_TO_EVALUATE = 18

    # Flask-Limiter storage. In-memory is fine for a single-process deploy;
    # point RATELIMIT_STORAGE_URI at Redis once running more than one worker.
    # RATELIMIT_STORAGE_URI / RATELIMIT_DEFAULT are the real Flask-Limiter
    # config keys (applied to every route automatically). RATE_LIMIT_SEARCH
    # and RATE_LIMIT_AUTOCOMPLETE are our own, used as explicit per-route
    # overrides on the costlier endpoints (they call paid Google APIs).
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_DEFAULT = os.environ.get("RATELIMIT_DEFAULT", "60 per minute")
    RATE_LIMIT_SEARCH = os.environ.get("RATE_LIMIT_SEARCH", "20 per minute")
    RATE_LIMIT_AUTOCOMPLETE = os.environ.get("RATE_LIMIT_AUTOCOMPLETE", "30 per minute")

    @classmethod
    def resolved_secret_key(cls) -> str:
        """Fail loudly in production if no SECRET_KEY was configured.

        A blank key would silently disable session/CSRF protection, so this
        only falls back to an insecure default outside production.
        """
        if cls.SECRET_KEY:
            return cls.SECRET_KEY
        if cls.ENV == "production" and not cls.TESTING:
            raise RuntimeError(
                "SECRET_KEY is not set. Set it in the environment before running in production."
            )
        return "dev-only-insecure-secret-key"


class TestingConfig(Config):
    ENV = "testing"
    TESTING = True
    SECRET_KEY = "testing-secret-key"
    RATELIMIT_ENABLED = False

from flask import Blueprint, current_app, render_template, request

from providers.ports import ProviderError
from services.map_links import build_beach_google_maps_url, build_beach_map_embed_url
from surfweb.extensions import limiter
from surfweb.validation import (
    ValidationError,
    clamp_radius_km,
    parse_latitude,
    parse_longitude,
    parse_result_limit,
    parse_skill_level,
    sanitize_location_query,
)

pages_bp = Blueprint("pages", __name__)


def _search_rate_limit():
    return current_app.config["RATE_LIMIT_SEARCH"]


@pages_bp.route("/", methods=["GET", "POST"])
@limiter.limit(_search_rate_limit, methods=["POST"])
def home():
    config = current_app.config
    container = current_app.extensions["surfspot_container"]

    default_result_limit = config["ALLOWED_RESULT_LIMITS"][0]
    default_skill_level = config["ALLOWED_SKILL_LEVELS"][0]

    location_query = ""
    max_distance_km = config["DEFAULT_RADIUS_KM"]
    result_limit = default_result_limit
    skill_level = default_skill_level
    origin_lat_raw = ""
    origin_lon_raw = ""
    origin_source = "manual"
    resolved_location_label = ""

    origin = None
    beaches = []
    error_message = None
    info_message = None
    has_searched = False
    winner_map_embed_url = None
    winner_google_maps_url = None

    if request.method == "POST":
        has_searched = True
        location_query = sanitize_location_query(request.form.get("location_query", ""))
        max_distance_km = clamp_radius_km(
            request.form.get("max_distance_km", config["DEFAULT_RADIUS_KM"]),
            config["MIN_RADIUS_KM"],
            config["MAX_RADIUS_KM"],
            config["DEFAULT_RADIUS_KM"],
        )
        result_limit = parse_result_limit(
            request.form.get("result_limit", default_result_limit),
            config["ALLOWED_RESULT_LIMITS"],
            default_result_limit,
        )
        skill_level = parse_skill_level(
            request.form.get("skill_level", default_skill_level),
            config["ALLOWED_SKILL_LEVELS"],
            default_skill_level,
        )
        origin_lat_raw = request.form.get("origin_lat", "").strip()
        origin_lon_raw = request.form.get("origin_lon", "").strip()
        origin_source = request.form.get("origin_source", "manual").strip() or "manual"
        resolved_location_label = sanitize_location_query(request.form.get("resolved_location_label", ""))

        origin_lat = origin_lon = None
        try:
            origin_lat = parse_latitude(origin_lat_raw)
            origin_lon = parse_longitude(origin_lon_raw)
        except ValidationError as exc:
            error_message = str(exc)

        if error_message is None:
            resolved_origin, error_message = container.location_resolver.resolve_origin(
                location_query=location_query,
                origin_lat=origin_lat,
                origin_lon=origin_lon,
                origin_source=origin_source,
                resolved_location_label=resolved_location_label,
            )

            if resolved_origin is not None:
                try:
                    (
                        origin,
                        beaches,
                        max_distance_km,
                        info_message,
                    ) = container.search_orchestrator.build_rankings_with_radius_fallback(
                        origin=resolved_origin,
                        max_distance_km=max_distance_km,
                        result_limit=result_limit,
                        skill_level=skill_level,
                    )
                    location_query = location_query or origin["name"]
                    resolved_location_label = origin["name"]
                except ProviderError as exc:
                    error_message = str(exc)
                except Exception:
                    current_app.logger.exception("Unexpected error building beach rankings")
                    error_message = "We could not load surf conditions right now. Please try again."

    if beaches:
        winner_map_embed_url = build_beach_map_embed_url(beaches[0], config["GOOGLE_MAPS_API_KEY"])
        winner_google_maps_url = build_beach_google_maps_url(beaches[0])

    return render_template(
        "index.html",
        location_query=location_query,
        max_distance_km=max_distance_km,
        result_limit=result_limit,
        skill_level=skill_level,
        origin=origin,
        beaches=beaches,
        has_searched=has_searched,
        error_message=error_message,
        info_message=info_message,
        origin_lat=origin_lat_raw,
        origin_lon=origin_lon_raw,
        origin_source=origin_source,
        resolved_location_label=resolved_location_label,
        winner_map_embed_url=winner_map_embed_url,
        winner_google_maps_url=winner_google_maps_url,
    )

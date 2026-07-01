from flask import Blueprint, current_app, jsonify, request

from providers.ports import ProviderError
from surfweb.extensions import limiter
from surfweb.validation import ValidationError, parse_latitude, parse_longitude, sanitize_location_query

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _autocomplete_rate_limit():
    return current_app.config["RATE_LIMIT_AUTOCOMPLETE"]


@api_bp.route("/location-autocomplete")
@limiter.limit(_autocomplete_rate_limit)
def location_autocomplete():
    container = current_app.extensions["surfspot_container"]
    query = sanitize_location_query(request.args.get("q", ""))
    if len(query) < 2:
        return jsonify({"suggestions": []})

    try:
        suggestions = container.providers.places.autocomplete_places(query)
    except ProviderError as exc:
        return jsonify({"error": str(exc), "suggestions": []}), 502

    return jsonify({"suggestions": suggestions[:6]})


@api_bp.route("/reverse-geocode", methods=["POST"])
@limiter.limit(_autocomplete_rate_limit)
def reverse_geocode():
    container = current_app.extensions["surfspot_container"]
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        payload = request.form.to_dict() if request.form else {}

    try:
        lat = parse_latitude(payload.get("lat"))
        lon = parse_longitude(payload.get("lon"))
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400

    if lat is None or lon is None:
        return jsonify({"error": "Latitude and longitude are required."}), 400

    try:
        resolved = container.providers.geocoding.reverse_geocode(lat, lon)
    except ProviderError as exc:
        return jsonify({"error": str(exc)}), 502

    return jsonify(resolved)

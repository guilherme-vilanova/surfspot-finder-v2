"""Central error handling so unexpected exceptions never leak internals to users."""

import logging

from flask import jsonify, render_template, request

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    @app.errorhandler(404)
    def _not_found(exc):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Not found."}), 404
        return render_template("error.html", message="Page not found."), 404

    @app.errorhandler(429)
    def _rate_limited(exc):
        message = "Too many requests. Please wait a moment and try again."
        if request.path.startswith("/api/"):
            return jsonify({"error": message}), 429
        return render_template("error.html", message=message), 429

    @app.errorhandler(500)
    def _server_error(exc):
        logger.error("Unhandled server error on %s %s", request.method, request.path, exc_info=exc)
        message = "Something went wrong on our end. Please try again."
        if request.path.startswith("/api/"):
            return jsonify({"error": message}), 500
        return render_template("error.html", message=message), 500

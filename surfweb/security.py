"""Baseline security headers for a public-facing app.

Kept as a plain after_request hook (no extra dependency). CSS/JS now live in
static/ files (see templates/index.html and templates/error.html), and the
direction-arrow rotation that used to be an inline style="transform:..."
attribute is now applied via a data-rotate-deg attribute + static/js/app.js.
There is no inline CSS/JS left in the templates, so script-src/style-src can
be 'self' only - no 'unsafe-inline'.
"""

CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data: https:; "
    "frame-src https://www.google.com https://maps.google.com; "
    "connect-src 'self'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'self'"
)


def register_security_headers(app):
    @app.after_request
    def _add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        if not app.debug and not app.testing:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response

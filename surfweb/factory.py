import logging

from flask import Flask

from .config import Config
from .container import ServiceContainer
from .errors import register_error_handlers
from .extensions import limiter
from .security import register_security_headers


def create_app(config_class=None):
    app = Flask(__name__, template_folder="../templates", static_folder="../static")

    config_class = config_class or Config
    app.config.from_object(config_class)
    app.secret_key = config_class.resolved_secret_key()

    _configure_logging(app)

    limiter.init_app(app)
    register_security_headers(app)
    register_error_handlers(app)

    app.extensions["surfspot_container"] = ServiceContainer(config_class)

    from .blueprints.api import api_bp
    from .blueprints.pages import pages_bp

    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp)

    return app


def _configure_logging(app):
    if logging.getLogger().handlers:
        return
    level = logging.DEBUG if app.debug else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

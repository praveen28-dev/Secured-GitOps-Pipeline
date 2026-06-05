"""
Container Security Falcon — Flask Application Factory

Uses the factory pattern for testability and configuration flexibility.
Metrics are automatically instrumented via Prometheus middleware.
"""

import logging
import os

from flask import Flask

from app.config import config_by_name


def create_app(config_name: str | None = None) -> Flask:
    """Create and configure the Flask application.

    Args:
        config_name: Configuration profile ('development', 'testing', 'production').
                     Defaults to APP_ENV environment variable or 'development'.

    Returns:
        Configured Flask application instance.
    """
    if config_name is None:
        config_name = os.getenv("APP_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # ── Logging ──────────────────────────────────────────────
    log_level = app.config.get("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    logger = logging.getLogger(__name__)

    # ── Register Blueprints ──────────────────────────────────
    from app.routes import api_bp, health_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(api_bp, url_prefix="/api/v1")

    # ── Security Headers Middleware ──────────────────────────
    @app.after_request
    def set_security_headers(response):
        """Inject security headers on every response."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )
        # Remove server header to avoid fingerprinting
        response.headers.pop("Server", None)
        return response

    # ── Prometheus Metrics ───────────────────────────────────
    if app.config.get("ENABLE_METRICS", True):
        try:
            from prometheus_flask_exporter import PrometheusMetrics

            PrometheusMetrics(app)
            logger.info("Prometheus metrics enabled at /metrics")
        except ImportError:
            logger.warning(
                "prometheus-flask-exporter not installed, "
                "metrics endpoint disabled"
            )

    logger.info(
        "Container Security Falcon started [env=%s]", config_name
    )
    return app

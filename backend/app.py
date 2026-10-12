"""Flask application factory. Run: python -m flask --app backend.app:create_app run."""
import logging
import time
import uuid

from flask import Flask, g, jsonify, request
from werkzeug.exceptions import HTTPException

from backend.api.routes import api
from backend.api.validation import ValidationError
from backend.config import settings
from backend.services.catalogue import CatalogueService


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(settings())
    if config:
        app.config.update(config)
    app.json.sort_keys = False
    app.json.ensure_ascii = False
    app.logger.setLevel(app.config["LOG_LEVEL"])
    app.extensions["catalogue"] = CatalogueService(app.config["DATA_PATH"])
    app.register_blueprint(api)

    @app.before_request
    def begin_request():
        g.request_id = uuid.uuid4().hex
        g.started_at = time.perf_counter()

    @app.after_request
    def finish_request(response):
        response.headers["X-Request-ID"] = g.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        origin = request.headers.get("Origin")
        if origin in app.config["ALLOWED_ORIGINS"]:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers.add("Vary", "Origin")
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        # Never log preference bodies, query strings, or authentication headers.
        app.logger.info("request_id=%s method=%s route=%s status=%s elapsed_ms=%.1f",
                        g.request_id, request.method, request.url_rule.rule if request.url_rule else "unmatched",
                        response.status_code, (time.perf_counter() - g.started_at) * 1000)
        return response

    def error(code, message, status):
        return jsonify({"error": {"code": code, "message": message, "request_id": g.request_id}}), status

    @app.errorhandler(ValidationError)
    @app.errorhandler(ValueError)
    def invalid(exc):
        return error("validation_error", str(exc), 400)

    @app.errorhandler(LookupError)
    def missing(_exc):
        return error("not_found", "Destination not found.", 404)

    @app.errorhandler(HTTPException)
    def http_error(exc):
        messages = {400: "Malformed JSON or request.", 404: "Endpoint not found.",
                    405: "Method not allowed.", 413: "Request body exceeds the 16 KiB limit.",
                    415: "Use Content-Type: application/json."}
        return error(exc.name.lower().replace(" ", "_"), messages.get(exc.code, exc.description), exc.code)

    @app.errorhandler(Exception)
    def unexpected(exc):
        app.logger.error("request_id=%s unhandled_error_type=%s", g.request_id, type(exc).__name__)
        return error("internal_error", "Unable to complete the request. Please retry.", 500)

    @app.get("/health")
    def health():
        return jsonify({"status": "success", "message": "TripGenie API is running",
                        "catalogue_records": len(app.extensions["catalogue"].records)})

    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_app().run(host="127.0.0.1", port=5001, debug=False)

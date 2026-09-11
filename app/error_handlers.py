"""
app/error_handlers.py

Registers global error handlers (Part 3.3 Section 8). Dual-mode as of
Part 3.5: requests under /api/* always get the standardized JSON
envelope (app/utils/formatters.py); every other (page-based) request
gets a real rendered HTML error page, since a browser navigating to a
protected page should see a styled Access Denied / 404 page, not a raw
JSON blob. Every unexpected error is still logged with full context
before a sanitized message reaches the client either way (Part 3.1
Section 21 — never expose internal details to the client).
"""

from flask import request, render_template
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException

from app.utils.formatters import fail_response, error_response
from app.utils.logger import get_error_logger
from app.utils.validators import ValidationError


def _is_api_request() -> bool:
    return request.path.startswith("/api/")


def register_error_handlers(app) -> None:

    @app.errorhandler(ValidationError)
    def handle_validation_error(err: ValidationError):
        if _is_api_request():
            return fail_response(err.message, status_code=400, field=err.field)
        return render_template("errors/access_denied.html", reason=err.message), 400

    @app.errorhandler(404)
    def handle_not_found(err):
        if _is_api_request():
            return fail_response("The requested resource was not found.", status_code=404)
        return render_template("errors/access_denied.html", reason="That page doesn't exist."), 404

    @app.errorhandler(403)
    def handle_forbidden(err):
        if _is_api_request():
            return fail_response("You do not have permission to perform this action.", status_code=403)
        reason = getattr(err, "description", None) or "You do not have permission to view this page."
        return render_template("errors/access_denied.html", reason=reason), 403

    @app.errorhandler(401)
    def handle_unauthorized(err):
        if _is_api_request():
            return fail_response("Authentication is required to access this resource.", status_code=401)
        # Page-based routes: Flask-Login's @login_required already redirects
        # to the login page before this would normally fire; this remains
        # as a safety net for any 401 raised outside that flow.
        return render_template("errors/access_denied.html", reason="Please log in to continue."), 401

    @app.errorhandler(SQLAlchemyError)
    def handle_db_error(err):
        get_error_logger().error("Database error on %s %s: %s", request.method, request.path, err)
        if _is_api_request():
            return error_response("A database error occurred. Please try again shortly.", status_code=500)
        return render_template("errors/access_denied.html", reason="A database error occurred."), 500

    @app.errorhandler(500)
    def handle_internal_error(err):
        get_error_logger().error("Internal server error on %s %s: %s", request.method, request.path, err)
        if _is_api_request():
            return error_response("An unexpected error occurred. Please try again shortly.", status_code=500)
        return render_template("errors/access_denied.html", reason="Something went wrong on our end."), 500

    @app.errorhandler(HTTPException)
    def handle_http_exception(err: HTTPException):
        if _is_api_request():
            return fail_response(err.description or err.name, status_code=err.code or 400)
        return render_template("errors/access_denied.html", reason=err.description or err.name), (err.code or 400)

    @app.errorhandler(Exception)
    def handle_unhandled_exception(err: Exception):
        get_error_logger().error(
            "Unhandled exception on %s %s: %s", request.method, request.path, err, exc_info=True
        )
        if _is_api_request():
            return error_response("An unexpected error occurred. Please try again shortly.", status_code=500)
        return render_template("errors/access_denied.html", reason="Something went wrong on our end."), 500

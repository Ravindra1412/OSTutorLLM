"""
app/utils/formatters.py

Implements the standardized JSON API response envelope (Section 10).
Every API endpoint in this backend returns one of these shapes, so a
frontend developer only ever has to handle one response contract.

Success:
    { "status": "success", "data": {...}, "message": "..." }

Failure (validation/auth/not-found — client-correctable):
    { "status": "fail", "message": "...", "field": "email" }

Error (unexpected server-side fault):
    { "status": "error", "message": "..." }
"""

from flask import jsonify

from app.utils.constants import STATUS_SUCCESS, STATUS_FAIL, STATUS_ERROR


def success_response(data=None, message: str = "OK", status_code: int = 200):
    payload = {"status": STATUS_SUCCESS, "message": message, "data": data if data is not None else {}}
    return jsonify(payload), status_code


def fail_response(message: str, status_code: int = 400, field: str | None = None):
    payload = {"status": STATUS_FAIL, "message": message}
    if field:
        payload["field"] = field
    return jsonify(payload), status_code


def error_response(message: str = "An unexpected error occurred.", status_code: int = 500):
    payload = {"status": STATUS_ERROR, "message": message}
    return jsonify(payload), status_code

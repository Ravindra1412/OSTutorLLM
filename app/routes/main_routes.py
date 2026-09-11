"""
app/routes/main_routes.py

Minimal top-level page routes. Just the landing page in this phase —
enough for `/` to resolve to something real so the auth flow has a
home to redirect to/from.
"""

from flask import Blueprint, render_template

main_bp = Blueprint("main_bp", __name__)


@main_bp.route("/", methods=["GET"])
def index():
    return render_template("index.html")

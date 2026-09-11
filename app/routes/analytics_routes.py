"""
app/routes/analytics_routes.py

Analytics blueprint (Part 3.9, Section 16). Thin translation layer
over app/analytics/services/*, mirroring the exact pattern every prior
JSON API blueprint follows (Part 3.6/3.7/3.8): routes validate/
authorize/serialize only, all real logic lives in the service layer.

Covers the Analytics, Recommendation, Achievements, Dashboard, and
Timeline APIs from Section 16. The Progress API is progress_routes.py
(Part 3.3, extended this phase with /summary).
"""

from flask import Blueprint, request
from flask_login import login_required, current_user

from app.utils.constants import ROLE_STUDENT
from app.utils.formatters import success_response, fail_response
from app.utils.helpers import role_required
from app.analytics.services import (
    analytics_engine, weak_topic_detector, recommendation_engine,
    achievement_manager, performance_scorer, predictive_engine,
    timeline_service, dashboard_service,
)

analytics_bp = Blueprint("analytics_bp", __name__, url_prefix="/api/analytics")


# --- Dashboard API ---

@analytics_bp.route("/dashboard", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def dashboard():
    return success_response(dashboard_service.build_dashboard(current_user.id))


@analytics_bp.route("/dashboard/refresh", methods=["POST"])
@login_required
@role_required(ROLE_STUDENT)
def dashboard_refresh():
    """Regenerates recommendations + re-checks platform achievements
    before returning the dashboard payload (dashboard_service's
    explicit-refresh path, distinct from the cheap read-only GET
    above)."""
    return success_response(dashboard_service.refresh_and_build_dashboard(current_user.id))


# --- Analytics API ---

@analytics_bp.route("", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def full_analytics():
    return success_response(analytics_engine.build_full_analytics(current_user.id))


@analytics_bp.route("/performance", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def performance():
    return success_response(performance_scorer.compute_all_scores(current_user.id))


@analytics_bp.route("/weak-topics", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def weak_topics():
    return success_response(weak_topic_detector.detect_weak_topics(current_user.id))


@analytics_bp.route("/predictive", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def predictive():
    return success_response(predictive_engine.build_predictive_summary(current_user.id))


# --- Recommendation API ---

@analytics_bp.route("/recommendations", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def recommendations():
    return success_response(recommendation_engine.get_active_recommendations(current_user.id))


@analytics_bp.route("/recommendations/sync", methods=["POST"])
@login_required
@role_required(ROLE_STUDENT)
def sync_recommendations():
    rows = recommendation_engine.sync_recommendations(current_user.id)
    return success_response([r.to_dict() for r in rows], message=f"Generated {len(rows)} recommendation(s).")


@analytics_bp.route("/recommendations/<int:recommendation_id>/dismiss", methods=["POST"])
@login_required
@role_required(ROLE_STUDENT)
def dismiss_recommendation(recommendation_id):
    ok = recommendation_engine.dismiss_recommendation(current_user.id, recommendation_id)
    if not ok:
        return fail_response("Recommendation not found.", status_code=404)
    return success_response(message="Recommendation dismissed.")


# --- Achievements API ---

@analytics_bp.route("/achievements", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def achievements():
    return success_response(achievement_manager.get_achievements_summary(current_user.id))


# --- Timeline API ---

@analytics_bp.route("/timeline", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def timeline():
    event_type = request.args.get("event_type")
    limit = min(int(request.args.get("limit", 50)), 200)
    return success_response(timeline_service.get_timeline(current_user.id, event_type=event_type, limit=limit))

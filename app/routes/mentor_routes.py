"""
app/routes/mentor_routes.py

AI Learning Mentor — student-facing JSON API (Section 20) + HTML pages
(Section 19). Thin translation layer over app/mentor/services/*.
"""

from flask import Blueprint, request, render_template, abort
from flask_login import login_required, current_user

from app.utils.constants import ROLE_STUDENT
from app.utils.formatters import success_response, fail_response
from app.utils.helpers import role_required
from app.utils.validators import require_fields
from app.mentor.services import (
    mentor_engine, study_planner, learning_health, confidence_engine,
    insights_engine, mentor_assistant,
)

mentor_bp = Blueprint("mentor_bp", __name__, url_prefix="/api/mentor")
mentor_pages_bp = Blueprint("mentor_pages_bp", __name__, url_prefix="/mentor")


def _require_student():
    if not current_user.is_authenticated or current_user.role != ROLE_STUDENT:
        abort(403)


# --- Mentor API ---

@mentor_bp.route("/overview", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def overview():
    return success_response(mentor_engine.build_mentor_overview(current_user.id))


@mentor_bp.route("/refresh", methods=["POST"])
@login_required
@role_required(ROLE_STUDENT)
def refresh():
    return success_response(mentor_engine.run_full_mentor_cycle(current_user.id), message="Mentor refreshed.")


# --- Learning Health API ---

@mentor_bp.route("/health", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def health():
    return success_response(learning_health.compute_learning_health(current_user.id))


# --- Confidence API ---

@mentor_bp.route("/confidence", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def confidence():
    return success_response(confidence_engine.compute_confidence(current_user.id))


# --- Insights API ---

@mentor_bp.route("/insights", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def insights():
    return success_response(insights_engine.generate_insights(current_user.id))


# --- Study Plan API ---

@mentor_bp.route("/study-plan/<string:period>", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def get_study_plan(period):
    if period not in ("daily", "weekly", "monthly"):
        return fail_response("period must be daily, weekly, or monthly.", status_code=400)
    plan = study_planner.get_saved_plan(current_user.id, period)
    return success_response(plan)


@mentor_bp.route("/study-plan/<string:period>/generate", methods=["POST"])
@login_required
@role_required(ROLE_STUDENT)
def generate_study_plan(period):
    generators = {
        "daily": study_planner.generate_daily_plan,
        "weekly": study_planner.generate_weekly_plan,
        "monthly": study_planner.generate_monthly_plan,
    }
    if period not in generators:
        return fail_response("period must be daily, weekly, or monthly.", status_code=400)
    plan = generators[period](current_user.id)
    return success_response(plan, message=f"{period.capitalize()} plan generated.")


# --- Student AI Assistant (Section 14) ---

@mentor_bp.route("/assistant/ask", methods=["POST"])
@login_required
@role_required(ROLE_STUDENT)
def ask_assistant():
    data = request.get_json(silent=True) or {}
    require_fields(data, ["question"])
    result = mentor_assistant.ask_student_assistant(current_user.id, data["question"])
    return success_response(result)


@mentor_bp.route("/assistant/history", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def assistant_history():
    return success_response(mentor_assistant.get_interaction_history(current_user.id))


# --- HTML Pages ---

@mentor_pages_bp.route("", methods=["GET"])
@login_required
def mentor_home_page():
    _require_student()
    return render_template("mentor/mentor_home.html")


@mentor_pages_bp.route("/study-planner", methods=["GET"])
@login_required
def study_planner_page():
    _require_student()
    return render_template("mentor/study_planner.html")

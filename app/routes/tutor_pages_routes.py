"""
Student-facing page routes for the OSTutorLLM Tutor interface.
Provides the HTML chat views (/tutor, /tutor/session/<id>).
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.chat_session import ChatSession
from app.ai import config as ai_config

tutor_pages_bp = Blueprint("tutor_pages", __name__)


@tutor_pages_bp.route("/tutor", methods=["GET"])
@login_required
def tutor_index():
    """Renders the main Tutor chat interface."""
    return render_template(
        "tutor/chat.html", 
        active_session_id=None,
        ai_provider=ai_config.provider_display_name()
    )


@tutor_pages_bp.route("/tutor/session/<int:session_id>", methods=["GET"])
@login_required
def tutor_session(session_id):
    """
    Renders the Tutor chat interface for a specific existing session,
    validating that the session belongs to the current user.
    """
    session = ChatSession.query.get(session_id)
    if not session:
        flash("Tutor session not found.", "warning")
        return redirect(url_for("tutor_pages.tutor_index"))

    if session.user_id != current_user.id:
        flash("You do not have permission to access that session.", "danger")
        return redirect(url_for("tutor_pages.tutor_index"))

    return render_template(
        "tutor/chat.html", 
        active_session_id=session.id,
        ai_provider=ai_config.provider_display_name()
    )
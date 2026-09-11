"""
app/routes/auth_routes.py

Authentication blueprint (Section 4). This is the one blueprint given a
working implementation in this foundation phase (rather than a bare
stub) because every other blueprint's @login_required/@role_required
protection is meaningless to test without real registration/login/logout
behind it. No Tutor/Quiz/AI logic is implemented here — this is strictly
identity and session management (Part 3.1 Section 1.3 layering: routes
stay thin, calling straight into the model layer since there is no
Service layer content yet for Auth beyond basic CRUD).
"""

from flask import Blueprint, request
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db
from app.models import User, StudentProfile
from app.utils.formatters import success_response, fail_response
from app.utils.validators import (
    require_fields, validate_email, validate_password, validate_role, validate_name
)
from app.utils.logger import get_activity_logger

auth_bp = Blueprint("auth_bp", __name__, url_prefix="/api/auth")


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    require_fields(data, ["name", "email", "password", "role"])

    name = validate_name(data.get("name"))
    email = validate_email(data.get("email"))
    password = validate_password(data.get("password"))
    role = validate_role(data.get("role"))

    if User.query.filter_by(email=email).first():
        return fail_response("An account with this email already exists.", status_code=409, field="email")

    user = User(name=name, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()  # populate user.id before creating the dependent profile row

    if role == "student":
        db.session.add(StudentProfile(user_id=user.id))

    db.session.commit()

    get_activity_logger().info("New %s account registered: %s", role, email)
    return success_response(user.to_dict(), message="Account created successfully.", status_code=201)


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    require_fields(data, ["email", "password"])

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    remember = bool(data.get("remember", False))

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        # Deliberately identical message for "no such user" and "wrong password"
        # so a caller cannot enumerate which registered emails exist.
        return fail_response("Invalid email or password.", status_code=401)

    login_user(user, remember=remember)
    get_activity_logger().info("Login: %s", email)
    return success_response(user.to_dict(), message="Logged in successfully.")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    email = current_user.email
    logout_user()
    get_activity_logger().info("Logout: %s", email)
    return success_response(message="Logged out successfully.")


@auth_bp.route("/me", methods=["GET"])
@login_required
def me():
    """Returns the currently authenticated user — used by the frontend
    to hydrate the navbar profile menu (Part 3.2) without a full page reload."""
    return success_response(current_user.to_dict())

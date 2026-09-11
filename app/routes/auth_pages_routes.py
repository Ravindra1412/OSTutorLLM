"""
app/routes/auth_pages_routes.py

Page-based (HTML/session/redirect) authentication routes — Section 15.
This is distinct from app/routes/auth_routes.py (Part 3.3's JSON API
under /api/auth/*, kept unchanged for programmatic/future-SPA use).
Both blueprints call into the SAME service layer (app/auth/services.py)
so business logic is never duplicated between the two interfaces —
only the request/response translation differs.

Route summary (Section 15):
    GET/POST /register
    GET/POST /login
    POST     /logout
    GET/POST /profile
    GET/POST /change-password
    GET/POST /forgot-password
    GET/POST /reset-password/<token>
    GET      /verify-email/<token>
    POST     /resend-verification
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user

from app.auth.forms import (
    RegistrationForm, LoginForm, ForgotPasswordForm, ResetPasswordForm,
    ChangePasswordForm, ProfileForm,
)
from app.auth.services import (
    register_user, authenticate, record_logout, change_password,
    request_password_reset, reset_password_with_token,
    send_verification_email_stub, verify_email_token, update_profile,
    AuthError,
)
from app.auth.rate_limit import rate_limit

auth_pages_bp = Blueprint("auth_pages_bp", __name__)


def _client_ip() -> str:
    return request.headers.get("X-Forwarded-For", request.remote_addr) or "unknown"


def _redirect_after_login(user):
    """Role-based post-login redirect (Section 5)."""
    next_url = request.args.get("next")
    if next_url and next_url.startswith("/"):  # only ever follow a relative, same-site path
        return redirect(next_url)
    return redirect(url_for("auth_pages_bp.profile"))


# --------------------------------------------------------------------
# Registration
# --------------------------------------------------------------------

@auth_pages_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("auth_pages_bp.profile"))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = register_user(
            name=form.name.data, email=form.email.data, password=form.password.data,
            role=form.role.data, ip_address=_client_ip(),
        )
        verify_url = send_verification_email_stub(user)
        flash("Account created! Please check your email to verify your account.", "success")
        if current_app.config.get("DEBUG"):
            flash(f"[Development only] Verification link: {verify_url}", "info")
        login_user(user)
        return _redirect_after_login(user)

    return render_template("auth/register.html", form=form)


# --------------------------------------------------------------------
# Login / Logout
# --------------------------------------------------------------------

@auth_pages_bp.route("/login", methods=["GET", "POST"])
@rate_limit(max_attempts=10, window_seconds=60)
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auth_pages_bp.profile"))

    form = LoginForm()
    if form.validate_on_submit():
        try:
            user = authenticate(
                email=form.email.data, password=form.password.data,
                ip_address=_client_ip(), user_agent=request.headers.get("User-Agent"),
            )
        except AuthError as exc:
            flash(exc.message, "danger")
            return render_template("auth/login.html", form=form)

        login_user(user, remember=form.remember.data)
        flash(f"Welcome back, {user.name.split(' ')[0]}!", "success")
        return _redirect_after_login(user)

    return render_template("auth/login.html", form=form)


@auth_pages_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    record_logout(current_user, ip_address=_client_ip())
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main_bp.index"))


# --------------------------------------------------------------------
# Password management
# --------------------------------------------------------------------

@auth_pages_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password_route():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        try:
            change_password(
                current_user, form.current_password.data, form.new_password.data, ip_address=_client_ip()
            )
        except AuthError as exc:
            flash(exc.message, "danger")
            return render_template("auth/change_password.html", form=form)

        flash("Your password has been updated.", "success")
        return redirect(url_for("auth_pages_bp.profile"))

    return render_template("auth/change_password.html", form=form)


@auth_pages_bp.route("/forgot-password", methods=["GET", "POST"])
@rate_limit(max_attempts=5, window_seconds=60)
def forgot_password():
    form = ForgotPasswordForm()
    dev_reset_link = None

    if form.validate_on_submit():
        user, token = request_password_reset(form.email.data)
        # Deliberately identical message whether or not the account exists
        # (Section 7/17) — never confirm/deny account existence to the caller.
        flash("If an account exists for that email, a reset link has been sent.", "info")
        if user and current_app.config.get("DEBUG"):
            dev_reset_link = url_for("auth_pages_bp.reset_password", token=token, _external=False)

    return render_template("auth/forgot_password.html", form=form, dev_reset_link=dev_reset_link)


@auth_pages_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    form = ResetPasswordForm()
    if form.validate_on_submit():
        try:
            reset_password_with_token(token, form.password.data, ip_address=_client_ip())
        except AuthError as exc:
            flash(exc.message, "danger")
            return redirect(url_for("auth_pages_bp.forgot_password"))

        flash("Your password has been reset. You can now log in.", "success")
        return redirect(url_for("auth_pages_bp.login"))

    return render_template("auth/reset_password.html", form=form)


# --------------------------------------------------------------------
# Email verification (Section 8)
# --------------------------------------------------------------------

@auth_pages_bp.route("/verify-email/<token>", methods=["GET"])
def verify_email(token):
    try:
        verify_email_token(token)
        flash("Your email has been verified. Thanks!", "success")
    except AuthError as exc:
        flash(exc.message, "danger")
    return redirect(url_for("auth_pages_bp.profile") if current_user.is_authenticated else url_for("auth_pages_bp.login"))


@auth_pages_bp.route("/resend-verification", methods=["POST"])
@login_required
def resend_verification():
    if current_user.email_verified:
        flash("Your email is already verified.", "info")
    else:
        verify_url = send_verification_email_stub(current_user)
        flash("Verification email sent.", "success")
        if current_app.config.get("DEBUG"):
            flash(f"[Development only] Verification link: {verify_url}", "info")
    return redirect(url_for("auth_pages_bp.profile"))


# --------------------------------------------------------------------
# Profile management (Section 9)
# --------------------------------------------------------------------

@auth_pages_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    if request.method == "GET" and current_user.is_student and current_user.student_profile:
        form.hint_verbosity_pref.data = str(current_user.student_profile.hint_verbosity_pref)
    if request.method == "GET" and current_user.is_faculty and current_user.faculty_profile:
        form.bio.data = current_user.faculty_profile.bio

    if form.validate_on_submit():
        hint_pref = int(form.hint_verbosity_pref.data) if form.hint_verbosity_pref.data else None
        update_profile(current_user, name=form.name.data, hint_verbosity_pref=hint_pref, bio=form.bio.data)
        flash("Profile updated.", "success")
        return redirect(url_for("auth_pages_bp.profile"))

    return render_template("auth/profile.html", form=form, user=current_user)

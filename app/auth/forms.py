"""
app/auth/forms.py

Flask-WTF form classes (Section 2 "forms/", Section 12 Input Validation).
Every form here gets automatic CSRF protection (Section 13) because it
inherits FlaskForm, and every field's validators run server-side before
any data reaches the service layer — client-side HTML5 validation
(Part 3.2's `required`/`minlength` attributes) is a UX nicety, never
the actual security boundary.

Note on "Username" (Section 4/12): this platform authenticates by email
rather than a separate username field, a decision already established
in Part 3.1 Section 8.2 and carried through Parts 3.3-3.4's `users`
table (no `username` column exists). Section 5's "Username Login"
requirement is satisfied by email functioning as the unique login
identifier; a dedicated username validator would validate a field this
schema does not have, so it is intentionally omitted rather than
bolted on inconsistently with the rest of the system.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, BooleanField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Optional

from app.models import User
from app.utils.constants import MIN_PASSWORD_LENGTH, VALID_ROLES


def _password_strength(form, field):
    """Beyond minimum length: require at least one letter and one digit.
    Kept simple/explainable rather than an opaque regex wall, but still
    meaningfully stronger than a bare length check (Section 4)."""
    value = field.data or ""
    has_letter = any(c.isalpha() for c in value)
    has_digit = any(c.isdigit() for c in value)
    if not (has_letter and has_digit):
        raise ValidationError("Password must contain at least one letter and one number.")


class RegistrationForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField("Email address", validators=[DataRequired(), Email(), Length(max=150)])
    role = SelectField("I am a", choices=[(r, r.capitalize()) for r in VALID_ROLES], validators=[DataRequired()])
    password = PasswordField(
        "Password", validators=[DataRequired(), Length(min=MIN_PASSWORD_LENGTH, max=128), _password_strength]
    )
    confirm_password = PasswordField(
        "Confirm password", validators=[DataRequired(), EqualTo("password", message="Passwords must match.")]
    )

    def validate_email(self, field):
        """Duplicate-account check (Section 4) — runs as part of normal
        WTForms validation so the template gets a field-level error for
        free, rather than the route having to special-case this check."""
        existing = User.query.filter_by(email=field.data.strip().lower()).first()
        if existing:
            raise ValidationError("An account with this email already exists.")


class LoginForm(FlaskForm):
    email = StringField("Email address", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember me")


class ForgotPasswordForm(FlaskForm):
    email = StringField("Email address", validators=[DataRequired(), Email()])


class ResetPasswordForm(FlaskForm):
    password = PasswordField(
        "New password", validators=[DataRequired(), Length(min=MIN_PASSWORD_LENGTH, max=128), _password_strength]
    )
    confirm_password = PasswordField(
        "Confirm new password", validators=[DataRequired(), EqualTo("password", message="Passwords must match.")]
    )


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current password", validators=[DataRequired()])
    new_password = PasswordField(
        "New password", validators=[DataRequired(), Length(min=MIN_PASSWORD_LENGTH, max=128), _password_strength]
    )
    confirm_new_password = PasswordField(
        "Confirm new password", validators=[DataRequired(), EqualTo("new_password", message="Passwords must match.")]
    )


class ProfileForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(min=2, max=100)])
    # Learning preference (Section 9) — student-only field, optional so the
    # same form works for a faculty profile edit without a validation error.
    hint_verbosity_pref = SelectField(
        "Hint verbosity",
        choices=[("1", "Terse"), ("2", "Balanced"), ("3", "Detailed")],
        validators=[Optional()],
    )
    bio = TextAreaField("Bio", validators=[Optional(), Length(max=1000)])

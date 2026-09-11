"""
app/__init__.py

The application factory. `create_app()` is the single entry point that
assembles the whole backend: configuration, extensions, models, logging,
blueprints, and global error handlers — in that order, because each
step depends on the previous one being ready.

Why a factory (rather than a module-level `app = Flask(__name__)`):
  - Enables creating multiple app instances with different configs
    (e.g. TestingConfig for pytest vs DevelopmentConfig for `python run.py`)
    without any global state leaking between them.
  - Avoids circular imports: extensions are created unbound in
    app/extensions.py and only wired to a concrete app here.
"""

from flask import Flask

from app.config.config import get_config
from app.extensions import db, migrate, login_manager, csrf
from app.error_handlers import register_error_handlers
from app.utils.logger import init_logging


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)

    # --- 1. Configuration ---
    config_class = get_config(config_name)
    app.config.from_object(config_class)

    # --- 2. Extensions ---
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # --- 3. Models ---
    from app import models  # noqa: F401

    @login_manager.user_loader
    def load_user(user_id: str):
        from app.models import User
        return db.session.get(User, int(user_id))

    # --- 4. Logging ---
    init_logging(app)

    # --- 5. Blueprints ---
    register_blueprints(app)

    # --- 6. Global error handlers ---
    register_error_handlers(app)

    # --- 6b. CLI commands ---
    register_cli_commands(app)

    # --- 7. Basic security headers on every response ---
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    app.logger.info("OSTutorLLM backend created with config=%s", config_class.__name__)
    return app


def register_blueprints(app: Flask) -> None:
    """Registers every Blueprint."""
    from app.routes.main_routes import main_bp
    from app.routes.health_routes import health_bp
    from app.routes.auth_routes import auth_bp
    from app.routes.auth_pages_routes import auth_pages_bp
    from app.routes.quiz_pages_routes import quiz_pages_bp
    from app.routes.code_review_pages_routes import code_review_pages_bp
    from app.routes.analytics_pages_routes import analytics_pages_bp
    from app.routes.faculty_pages_routes import faculty_pages_bp
    from app.routes.student_routes import student_bp
    from app.routes.faculty_routes import faculty_bp
    from app.routes.faculty_student_routes import faculty_student_bp
    from app.routes.faculty_content_routes import faculty_content_bp
    from app.routes.faculty_quiz_routes import faculty_quiz_bp
    from app.routes.faculty_assignment_routes import faculty_assignment_bp
    from app.routes.faculty_report_routes import faculty_report_bp
    from app.routes.mentor_routes import mentor_bp, mentor_pages_bp
    from app.routes.mentor_faculty_routes import mentor_faculty_bp
    from app.routes.assignment_student_routes import assignment_student_bp
    from app.routes.tutor_routes import tutor_bp
    from app.routes.tutor_pages_routes import tutor_pages_bp
    from app.routes.quiz_routes import quiz_bp
    from app.routes.progress_routes import progress_bp
    from app.routes.settings_routes import settings_bp
    from app.routes.code_review_routes import code_review_bp
    from app.routes.analytics_routes import analytics_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_pages_bp)
    app.register_blueprint(quiz_pages_bp)
    app.register_blueprint(code_review_pages_bp)
    app.register_blueprint(analytics_pages_bp)
    app.register_blueprint(faculty_pages_bp)
    app.register_blueprint(mentor_pages_bp)
    app.register_blueprint(tutor_pages_bp)

    # --- JSON API blueprints ---
    api_blueprints = [
        (student_bp, "/api/student/*"),
        (faculty_bp, "/api/faculty/*"),
        (tutor_bp, "/api/tutor/*"),
        (quiz_bp, "/api/quiz/*"),
        (progress_bp, "/api/progress/*"),
        (settings_bp, "/api/settings/*"),
        (auth_bp, "/api/auth/*"),
        (code_review_bp, "/api/code-review/*"),
        (analytics_bp, "/api/analytics/*"),
        (faculty_student_bp, "/api/faculty/students/*"),
        (faculty_content_bp, "/api/faculty/content/*"),
        (faculty_quiz_bp, "/api/faculty/quizzes/*"),
        (faculty_assignment_bp, "/api/faculty/assignments/*"),
        (faculty_report_bp, "/api/faculty/reports/*"),
        (assignment_student_bp, "/api/assignments/*"),
        (mentor_bp, "/api/mentor/*"),
        (mentor_faculty_bp, "/api/faculty/mentor/*"),
    ]
    for blueprint, _route_comment in api_blueprints:
        app.register_blueprint(blueprint)
        csrf.exempt(blueprint)


def register_cli_commands(app: Flask) -> None:
    """Registers custom `flask <command>` CLI commands."""

    @app.cli.command("seed-db")
    def seed_db():
        from database.seed.seed_data import run_seed
        run_seed()
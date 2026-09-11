"""
extensions.py

Holds Flask extension instances (SQLAlchemy, Migrate, LoginManager) as
module-level singletons, uninitialized. They are bound to the actual
Flask app later inside the application factory (app/__init__.py) via
each extension's .init_app(app) method.

Why this file exists: if db/login_manager were instead created directly
inside __init__.py, any module that needs to import `db` (e.g. every
file under app/models/) would have to import from __init__.py, which
itself imports those same model files -> circular import. Centralizing
extensions here breaks that cycle.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()

# Where Flask-Login redirects unauthenticated users who hit a
# @login_required route. Points at the page-based (HTML/session) login
# view (Part 3.5), not the JSON API blueprint from Part 3.3 — a browser
# hitting a protected page should land on an HTML login form, not a
# JSON 401 body.
login_manager.login_view = "auth_pages_bp.login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "info"

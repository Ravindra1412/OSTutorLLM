"""
tests/conftest.py

Shared pytest fixtures. Every test gets a fresh Flask app built with
TestingConfig (in-memory SQLite, see app/config/config.py) and a clean
database schema created and torn down per test — no test can leak state
into another.
"""

import werkzeug.security

_real_generate_password_hash = werkzeug.security.generate_password_hash
werkzeug.security.generate_password_hash = lambda password, *args, **kwargs: _real_generate_password_hash(
    password, method="pbkdf2:sha256:1"
)

import pytest

from app import create_app
from app.extensions import db as _db


@pytest.fixture()
def app():
    application = create_app("testing")
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    return _db
"""
app/utils/db_helpers.py

Generic, model-agnostic database helper functions (Part 3.4, Section
13). These wrap common SQLAlchemy patterns (create/get/update/delete,
pagination, simple search) once, so route/service code across every
future feature module calls one tested helper instead of hand-rolling
`db.session.add(); db.session.commit()` (with matching try/except)
in twenty different places.

All functions here use SQLAlchemy's query builder / ORM exclusively —
no raw SQL string interpolation — which is the primary SQL-injection
defense described in Section 16.
"""

from __future__ import annotations

from typing import Any, Type, TypeVar

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from app.utils.logger import get_error_logger

ModelT = TypeVar("ModelT")


class DatabaseError(Exception):
    """Raised by these helpers on any DB failure, wrapping the original
    SQLAlchemy exception so calling code can catch one exception type."""

    def __init__(self, message: str, original: Exception | None = None):
        super().__init__(message)
        self.message = message
        self.original = original


class DuplicateRecordError(DatabaseError):
    """Raised specifically for unique-constraint violations (Section 18),
    so calling code can return a clean 409 rather than a generic 500."""


# --------------------------------------------------------------------
# CRUD
# --------------------------------------------------------------------

def create_record(instance: ModelT) -> ModelT:
    """Adds and commits a single new model instance.

    Raises DuplicateRecordError on a unique/constraint violation,
    DatabaseError on any other SQLAlchemy failure. In both cases the
    session is rolled back so it is left usable for the next operation.
    """
    try:
        db.session.add(instance)
        db.session.commit()
        return instance
    except IntegrityError as exc:
        db.session.rollback()
        get_error_logger().error("IntegrityError creating %s: %s", type(instance).__name__, exc)
        raise DuplicateRecordError(
            f"A {type(instance).__name__} with these values already exists.", original=exc
        ) from exc
    except SQLAlchemyError as exc:
        db.session.rollback()
        get_error_logger().error("Error creating %s: %s", type(instance).__name__, exc)
        raise DatabaseError(f"Could not create {type(instance).__name__}.", original=exc) from exc


def get_by_id(model: Type[ModelT], record_id: Any) -> ModelT | None:
    """Simple primary-key lookup. Returns None (not an exception) when
    not found — callers decide whether "missing" is an error for them."""
    return db.session.get(model, record_id)


def get_or_404_dict(model: Type[ModelT], record_id: Any) -> ModelT:
    """Like get_by_id, but raises DatabaseError (caught centrally and
    converted to a clean 404-style response) when nothing is found —
    convenient for route handlers that always want a hard failure."""
    instance = get_by_id(model, record_id)
    if instance is None:
        raise DatabaseError(f"{model.__name__} with id={record_id} was not found.")
    return instance


def update_record(instance: ModelT, **fields) -> ModelT:
    """Applies field updates to an already-fetched instance and commits."""
    try:
        for key, value in fields.items():
            setattr(instance, key, value)
        db.session.commit()
        return instance
    except IntegrityError as exc:
        db.session.rollback()
        raise DuplicateRecordError(
            f"Update would violate a uniqueness constraint on {type(instance).__name__}.", original=exc
        ) from exc
    except SQLAlchemyError as exc:
        db.session.rollback()
        get_error_logger().error("Error updating %s: %s", type(instance).__name__, exc)
        raise DatabaseError(f"Could not update {type(instance).__name__}.", original=exc) from exc


def delete_record(instance: ModelT) -> None:
    try:
        db.session.delete(instance)
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        get_error_logger().error("Error deleting %s: %s", type(instance).__name__, exc)
        raise DatabaseError(f"Could not delete {type(instance).__name__}.", original=exc) from exc


# --------------------------------------------------------------------
# Pagination
# --------------------------------------------------------------------

def paginate(query, page: int = 1, per_page: int = 20, max_per_page: int = 100) -> dict:
    """Applies LIMIT/OFFSET-based pagination to a SQLAlchemy query and
    returns a JSON-ready envelope (items + pagination metadata).

    Clamps per_page to max_per_page so a caller cannot request an
    unbounded result set (a basic performance/DoS safeguard).
    """
    page = max(1, page)
    per_page = max(1, min(per_page, max_per_page))

    total = query.order_by(None).count()  # order_by(None) avoids a redundant ORDER BY in the COUNT query
    items = query.limit(per_page).offset((page - 1) * per_page).all()

    return {
        "items": items,
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": (total + per_page - 1) // per_page if per_page else 0,
    }


# --------------------------------------------------------------------
# Search
# --------------------------------------------------------------------

def search_by_field(model: Type[ModelT], field_name: str, term: str, limit: int = 20):
    """Simple case-insensitive partial-match search on a single text
    column. Uses SQLAlchemy's `.ilike()` (parameterized, injection-safe)
    rather than string-formatted SQL.
    """
    column = getattr(model, field_name)
    pattern = f"%{term}%"
    return model.query.filter(column.ilike(pattern)).limit(limit).all()

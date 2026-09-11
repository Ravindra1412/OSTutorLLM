"""
app/quiz/services/security.py

Quiz Security (Section 19). Four specific protections:

1. Answer Tampering — the correct_answer is NEVER included in any
   payload sent to the client (see app/routes/quiz_routes.py's
   `_serialize_question_for_student`, which explicitly excludes it).
   Grading always re-reads the correct_answer server-side from the
   database, never trusts a client-supplied "is this right" flag.
2. Multiple Submissions — `QuizAttempt.is_submitted` is checked before
   any grading; a second submit on an already-submitted attempt is
   rejected outright.
3. URL Manipulation — every attempt/question lookup is scoped by the
   requesting user's ID (ownership check), so incrementing an ID in
   the URL cannot access another student's attempt.
4. Session Abuse — only one ACTIVE (not-yet-submitted) attempt per quiz
   per student is allowed at a time, preventing a student from opening
   the same quiz in multiple tabs to attempt answer-fishing.
"""

from app.models import QuizAttempt


class QuizSecurityError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def assert_owns_attempt(attempt: QuizAttempt | None, user_id: int) -> QuizAttempt:
    if attempt is None or attempt.user_id != user_id:
        # Identical message for "doesn't exist" and "not yours" — no
        # existence-enumeration leak (Section 19 / same pattern as
        # Part 3.6's tutor session ownership check).
        raise QuizSecurityError("Quiz attempt not found.")
    return attempt


def assert_not_already_submitted(attempt: QuizAttempt) -> None:
    if attempt.is_submitted:
        raise QuizSecurityError("This quiz attempt has already been submitted and cannot be modified.")


def assert_no_other_active_attempt(user_id: int, quiz_id: int) -> None:
    existing = QuizAttempt.query.filter_by(user_id=user_id, quiz_id=quiz_id, is_submitted=False).first()
    if existing is not None:
        raise QuizSecurityError(
            f"You already have an in-progress attempt (id={existing.id}) for this quiz. "
            f"Submit or resume it before starting a new one."
        )

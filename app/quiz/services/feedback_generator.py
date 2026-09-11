"""
app/quiz/services/feedback_generator.py

The Feedback Generator (Section 1/10). Runs once, after a QuizAttempt
is fully graded. Produces:
  - Correct Explanation: pulled directly from each QuizQuestion.explanation
    (static, instant, no LLM call needed — already authored per Section
    6's question bank)
  - Mistake Analysis + Learning Suggestions: one LLM-generated paragraph
    summarizing the pattern across ALL wrong answers, not a per-question
    essay
  - Recommended Videos / Notes: explicit placeholders (Section 10 asks
    for these as placeholders — no video/notes content system exists
    in any phase yet, so returning a clearly-labeled null/placeholder
    is the honest implementation, not a fabricated link)
  - Next Topic Recommendation: reuses Part 3.6's personalization module
"""

import json
from dataclasses import dataclass

from app.models import QuizAttempt
from app.ai.prompts import manager as prompt_manager
from app.ai.services.llm_service import generate_reply
from app.ai.services import personalization


@dataclass
class QuestionFeedback:
    question_id: int
    question_text: str
    is_correct: bool
    student_answer: str
    correct_answer_display: str
    explanation: str
    points_earned: float
    points_possible: float


@dataclass
class AttemptFeedback:
    per_question: list
    mistake_analysis: str
    recommended_videos: None = None    # Section 10 — explicit placeholder, honestly null
    recommended_notes: None = None     # Section 10 — explicit placeholder, honestly null
    next_topic_recommendation: str | None = None


def build_per_question_feedback(attempt: QuizAttempt) -> list:
    feedback = []
    for result in attempt.results:
        question = result.question
        try:
            correct_display = json.loads(question.correct_answer)
        except (ValueError, TypeError):
            correct_display = question.correct_answer
        feedback.append(QuestionFeedback(
            question_id=question.id,
            question_text=question.question_text,
            is_correct=bool(result.is_correct),
            student_answer=result.student_answer or "",
            correct_answer_display=str(correct_display),
            explanation=question.explanation or "",
            points_earned=result.points_earned,
            points_possible=question.points,
        ))
    return feedback


def generate_mistake_analysis(attempt: QuizAttempt, topic_name: str) -> str:
    """Section 10 — LLM-generated holistic feedback. Falls back to a
    graceful message (never a raw error) if the LLM call fails (Part
    3.6's fallback strategy applies transitively since this calls the
    same generate_reply())."""
    from app.quiz.services.scoring_engine import summarize_attempt

    summary = summarize_attempt(attempt)
    weak_questions = [r.question.question_text for r in attempt.results if not r.is_correct][:3]
    weak_summary = "; ".join(weak_questions) if weak_questions else "none — great work!"

    if not weak_questions:
        return "Strong performance across the board — no significant weak areas to flag from this attempt."

    messages = prompt_manager.build_feedback_messages(
        topic=topic_name, score_percent=summary["score_percent"],
        correct_count=summary["correct_count"], total_count=summary["total_questions"],
        weak_question_summaries=weak_summary,
    )
    result = generate_reply(messages)
    return result.text  # llm_service already returns a graceful fallback message on failure


def build_attempt_feedback(attempt: QuizAttempt, topic_name: str) -> AttemptFeedback:
    per_question = build_per_question_feedback(attempt)
    mistake_analysis = generate_mistake_analysis(attempt, topic_name)

    from app.models import Topic
    available_topics = [t.name for t in Topic.query.all()]
    next_topic = personalization.recommend_next_topic(attempt.user_id, available_topics)

    return AttemptFeedback(
        per_question=per_question,
        mistake_analysis=mistake_analysis,
        next_topic_recommendation=next_topic,
    )

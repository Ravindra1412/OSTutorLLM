"""
app/quiz/services/question_generator.py

The Question Generator (Section 1/5/15). Assembles a question set for
a quiz from two sources:
  1. Static Question Bank (app/quiz/question_bank/seed_bank.py) —
     preferred when coverage exists, since curated questions have
     verified correct answers and explanations.
  2. LLM-Generated Questions — used to fill any gap the static bank
     doesn't cover for the requested topic/difficulty, via the Prompt
     Manager's `build_quiz_messages` (Part 3.6) and the LLM Service.

Also implements:
  - Randomized Questions / Random option order (Section 15)
  - No-repeat-within-window selection (Section 15) — avoids a student
    seeing the exact same static-bank question in back-to-back quiz
    attempts on the same topic
  - Topic-Based / Difficulty-Based selection (Section 5)
  - Learning Gap Questions (Section 5) — biased toward the student's
    weak topics (Part 3.6's personalization.get_weak_topics)
  - Revision Questions (Section 5) — pulls from topics the student
    completed a while ago, to space out review
"""

import json
import random

from app.models import Topic, QuizAttempt, Quiz
from app.quiz.question_bank import seed_bank
from app.ai.prompts import manager as prompt_manager
from app.ai.services.llm_service import generate_reply


def _recent_question_texts(user_id: int, topic_name: str, limit_attempts: int = 3) -> set[str]:
    """Section 15 — no repeated questions. Looks at the student's most
    recent attempts on this topic and collects the question text they
    already saw, so a fresh quiz avoids repeating them where possible."""
    topic = Topic.query.filter_by(name=topic_name).first()
    if not topic:
        return set()

    recent_attempts = (
        QuizAttempt.query.join(Quiz, QuizAttempt.quiz_id == Quiz.id)
        .filter(QuizAttempt.user_id == user_id, Quiz.topic_id == topic.id)
        .order_by(QuizAttempt.started_at.desc())
        .limit(limit_attempts)
        .all()
    )
    seen = set()
    for attempt in recent_attempts:
        for question in attempt.quiz.questions:
            seen.add(question.question_text)
    return seen


def _shuffle_options(question_dict: dict) -> dict:
    """Section 15 — random option order, for MCQ/multi-select only
    (true/false, matching, and drag-and-drop have meaningful/expected
    ordering that shuffling would break or make nonsensical)."""
    if question_dict["question_type"] in ("mcq", "multi_select") and question_dict.get("options"):
        options = list(question_dict["options"])
        random.shuffle(options)
        question_dict = dict(question_dict, options=options)
    return question_dict


def _from_static_bank(topic_name: str, difficulty_level: int, count: int, exclude_texts: set[str]) -> list[dict]:
    candidates = seed_bank.get_questions_for_topic_and_difficulty(topic_name, difficulty_level, tolerance=1)
    candidates = [q for q in candidates if q["question_text"] not in exclude_texts]
    random.shuffle(candidates)  # Section 15 — randomized selection
    return [_shuffle_options(q) for q in candidates[:count]]


def _from_llm(topic_name: str, difficulty_level: int, count: int, recent_topics_covered: str) -> list[dict]:
    """LLM-Generated Questions (Section 5). Expects the model to return
    a JSON array of question objects matching the quiz_prompt.txt
    contract (Part 3.6). Falls back to an empty list (not a crash) if
    the model's output isn't valid JSON — the caller simply gets fewer
    questions than requested rather than a failed quiz start, and this
    is logged for visibility (Section 21)."""
    from app.utils.logger import get_ai_logger

    messages = prompt_manager.build_quiz_messages(
        topic=topic_name, difficulty_level=difficulty_level, question_count=count,
        recent_topics_covered=recent_topics_covered,
    )
    result = generate_reply(messages)
    if not result.success:
        get_ai_logger().warning("Quiz LLM generation failed, falling back to static bank only: %s", result.text)
        return []

    try:
        raw = result.text.strip()
        if raw.startswith("```"):
            raw = raw.strip("`").lstrip("json").strip()
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            parsed = [parsed]
        questions = []
        for item in parsed:
            questions.append({
                "topic": topic_name,
                "question_text": item["question_text"],
                "question_type": item.get("question_type", "mcq"),
                "options": item.get("options"),
                "correct_answer": item["correct_answer"],
                "explanation": item.get("explanation", ""),
                "difficulty_level": item.get("difficulty_level", difficulty_level),
                "points": 1.0,
            })
        return questions[:count]
    except (ValueError, KeyError, TypeError) as exc:
        get_ai_logger().warning("Quiz LLM returned unparsable output, falling back to static bank only: %s", exc)
        return []


def generate_question_set(
    user_id: int, topic_name: str, difficulty_level: int, count: int = 5, avoid_repeats: bool = True,
) -> list[dict]:
    """The main entry point (Section 5). Fills `count` questions:
    static bank first, LLM generation for any remainder, static bank
    again (ignoring the repeat-avoidance) as a last resort so a quiz
    never starts with fewer questions than requested purely because
    the student has seen everything once before."""
    exclude_texts = _recent_question_texts(user_id, topic_name) if avoid_repeats else set()

    questions = _from_static_bank(topic_name, difficulty_level, count, exclude_texts)

    if len(questions) < count:
        remaining = count - len(questions)
        already_picked = {q["question_text"] for q in questions}
        llm_questions = _from_llm(topic_name, difficulty_level, remaining, recent_topics_covered="")
        questions.extend(q for q in llm_questions if q["question_text"] not in already_picked)

    if len(questions) < count:
        # Last resort: allow repeats rather than starting an under-filled quiz.
        remaining = count - len(questions)
        already_picked = {q["question_text"] for q in questions}
        fallback = _from_static_bank(topic_name, difficulty_level, remaining, exclude_texts=set())
        questions.extend(q for q in fallback if q["question_text"] not in already_picked)

    random.shuffle(questions)  # Section 15 — random topic/question presentation order within the set
    return questions[:count]


def generate_learning_gap_quiz(user_id: int, count: int = 5) -> tuple[str | None, list[dict]]:
    """Section 5 — Learning Gap Questions. Targets the student's single
    weakest tracked topic (reusing Part 3.6's personalization module)
    rather than a topic they explicitly chose."""
    from app.ai.services.personalization import get_weak_topics
    from app.quiz.services.difficulty_manager import determine_adaptive_difficulty

    weak = get_weak_topics(user_id, limit=1)
    if not weak:
        return None, []

    topic_name = weak[0]["topic_name"]
    difficulty = determine_adaptive_difficulty(user_id, topic_name)
    return topic_name, generate_question_set(user_id, topic_name, difficulty, count)


def generate_revision_quiz(user_id: int, count: int = 5) -> tuple[str | None, list[dict]]:
    """Section 5 — Revision Questions. Picks the topic the student has
    tracked progress on but hasn't attempted a quiz on most recently —
    i.e., something they learned a while ago and may be due to
    revisit, distinct from "weak" (Learning Gap) which targets low
    mastery regardless of recency."""
    from app.models import Progress

    entries = Progress.query.filter_by(user_id=user_id).order_by(Progress.last_updated.asc()).all()
    if not entries:
        return None, []

    topic_name = entries[0].topic_name  # least-recently-touched tracked topic
    from app.quiz.services.difficulty_manager import determine_adaptive_difficulty
    difficulty = determine_adaptive_difficulty(user_id, topic_name)
    return topic_name, generate_question_set(user_id, topic_name, difficulty, count)

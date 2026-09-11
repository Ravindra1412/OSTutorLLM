"""
app/mentor/services/mentor_assistant.py

Student + Faculty AI Assistant (Sections 13-14). A deliberately RULE-
BASED intent router, not a free-form LLM call — every question is
matched against a small set of known intents by keyword, and every
answer is generated from the real mentor/analytics services, never
from the LLM's own general knowledge. This keeps every answer
explainable (Section 13's own requirement: "Explain how answers are
generated") and free (no LLM call needed at all for this feature),
consistent with the same principle `predictive_engine.py` (Part 3.9)
established: heuristics over black boxes wherever an explainable
alternative exists.

Every question and answer is logged to `MentorInteraction` — this IS
"mentor memory" for the assistant: a real, queryable Q&A history,
distinct from the Tutor Engine's own conversational memory (Part 3.6),
which serves a different purpose (an ongoing teaching dialogue, not
one-shot analytical questions).
"""

import re

from app.extensions import db
from app.models import MentorInteraction, User, Topic
from app.utils.constants import ROLE_STUDENT
from app.mentor.services import study_planner, confidence_engine, insights_engine
from app.analytics.services.weak_topic_detector import detect_weak_topics
from app.analytics.services.predictive_engine import readiness_for_next_lesson
from app.faculty.services import class_analytics, code_review_monitoring


def _log(user_id: int, role: str, question: str, answer: str, intent: str) -> None:
    db.session.add(MentorInteraction(user_id=user_id, role=role, question=question, answer=answer, intent=intent))
    db.session.commit()


def _extract_topic_keyword(question: str) -> str | None:
    """Simple noun-phrase heuristic: look for a known topic name
    mentioned in the question — checking both the curriculum Topic
    table AND actual Progress.topic_name values, since a topic can be
    tracked in Progress (written by the Quiz/Code Review engines)
    without necessarily having a matching curriculum Topic row (the
    two are intentionally decoupled elsewhere in this codebase too —
    see Part 3.9's progress_tracker.py). Not a real NLP entity
    extractor — sufficient for this assistant's scoped intent set."""
    from app.models import Progress

    candidate_names = {t.name for t in Topic.query.all()}
    candidate_names |= {row[0] for row in db.session.query(Progress.topic_name).distinct().all()}

    q_lower = question.lower()
    for name in candidate_names:
        if name.lower() in q_lower:
            return name
    # fall back to any single significant word overlap
    words = re.findall(r"[a-zA-Z]+", q_lower)
    for name in candidate_names:
        if any(w in name.lower() for w in words if len(w) > 3):
            return name
    return None


# --- Student Assistant (Section 14) ---

def ask_student_assistant(user_id: int, question: str) -> dict:
    q = question.lower().strip()

    if any(p in q for p in ["study today", "what should i study", "today's plan", "today plan"]):
        plan = study_planner.generate_daily_plan(user_id)
        answer = f"Today's focus: {plan['focus']['activity']}. {plan['focus']['reason']}"
        intent = "daily_plan"

    elif any(p in q for p in ["weakest", "which topic is weak", "weak topic"]):
        weak = detect_weak_topics(user_id, limit=1)
        if weak:
            answer = f"Your weakest tracked topic is {weak[0]['topic_name']} — {weak[0]['signals'][0] if weak[0]['signals'] else 'flagged by multiple signals.'}"
        else:
            answer = "No weak topics detected right now — your tracked topics are all at a healthy mastery level."
        intent = "weakest_topic"

    elif any(p in q for p in ["ready for", "ready to", "next quiz", "am i ready"]):
        readiness = readiness_for_next_lesson(user_id)
        answer = ("Yes — " if readiness["ready"] else "Not quite yet — ") + readiness["reason"]
        intent = "readiness_check"

    elif any(p in q for p in ["confidence low", "why is my confidence", "confidence"]):
        conf = confidence_engine.compute_confidence(user_id)
        if conf["why"]["what_needs_work"]:
            answer = f"Your overall confidence is {conf['overall_confidence']}. Main factor: {conf['why']['what_needs_work'][0]}"
        else:
            answer = f"Your overall confidence is {conf['overall_confidence']}. No specific weak signal is dragging it down right now."
        intent = "confidence_explanation"

    elif any(p in q for p in ["revision plan", "revise", "revision"]):
        plan = study_planner.generate_weekly_plan(user_id)
        revision_day = next((s for s in plan["schedule"] if s["day"] == "Sunday"), None)
        weak_days = [s["topic"] for s in plan["schedule"] if s.get("reason", "").startswith("Flagged")]
        answer = f"Revision plan: focus your Sunday revision slot on {', '.join(weak_days) if weak_days else 'your tracked topics'}."
        intent = "revision_plan"

    else:
        insights = insights_engine.generate_insights(user_id)
        answer = insights[0]["text"] if insights else "I don't have enough data yet to answer that specifically — try asking about your weakest topic or today's study plan."
        intent = "fallback_insight"

    _log(user_id, ROLE_STUDENT, question, answer, intent)
    return {"question": question, "answer": answer, "intent": intent}


# --- Faculty Assistant (Section 13) ---

def ask_faculty_assistant(faculty_user_id: int, question: str) -> dict:
    q = question.lower().strip()

    if "struggle" in q or "weak" in q:
        topic_name = _extract_topic_keyword(question)
        if topic_name:
            from app.models import Progress
            struggling = (
                Progress.query.filter(Progress.topic_name == topic_name, Progress.mastery_score < 60)
                .join(User, Progress.user_id == User.id).all()
            )
            names = [db.session.get(User, p.user_id).name for p in struggling]
            answer = (f"{len(names)} student(s) below 60% mastery on {topic_name}: {', '.join(names)}."
                       if names else f"No students are currently struggling with {topic_name}.")
        else:
            weak = class_analytics.weak_and_strong_topics()["weak_topics"]
            answer = ("Class-wide weak topics: " + ", ".join(t["topic_name"] for t in weak)) if weak else "No class-wide weak topics detected."
        intent = "struggling_students"

    elif "lowest average" in q or "lowest score" in q:
        perf = class_analytics.topic_wise_class_performance()
        if perf:
            lowest = min(perf, key=lambda t: t["average_mastery"])
            answer = f"{lowest['topic_name']} has the lowest class average mastery, at {lowest['average_mastery']:.1f}% across {lowest['student_count']} student(s)."
        else:
            answer = "No topic performance data recorded yet."
        intent = "lowest_average_topic"

    elif "common" in q and ("mistake" in q or "error" in q):
        mistakes = code_review_monitoring.common_mistakes(top_n=5)
        answer = ("Most common code review findings: " + ", ".join(f"{m['category']} ({m['occurrences']}x)" for m in mistakes)) if mistakes else "No code review findings recorded yet."
        intent = "common_mistakes"

    elif "generate quiz" in q:
        topic_name = _extract_topic_keyword(question)
        answer = (f"To author a quiz on {topic_name}, use Faculty → Quizzes → New Quiz (Part 3.10) — "
                  f"I can point you there, but quiz authoring itself needs your review of each question, so I won't auto-create one silently."
                  if topic_name else "I couldn't identify which topic you want a quiz on — try 'generate quiz on <topic name>'.")
        intent = "quiz_generation_redirect"

    elif "revision plan" in q and ("weak student" in q or "struggling" in q):
        weak = class_analytics.weak_and_strong_topics()["weak_topics"][:3]
        answer = ("Suggested class revision focus: " + ", ".join(t["topic_name"] for t in weak)) if weak else "No class-wide weak topics to build a revision plan around right now."
        intent = "class_revision_plan"

    else:
        answer = ("I can answer: which students struggle with a topic, which topic has the lowest average score, "
                   "common shell mistakes, or suggest a revision plan for weak students. Try rephrasing your question "
                   "using one of those patterns.")
        intent = "fallback_help"

    _log(faculty_user_id, "faculty", question, answer, intent)
    return {"question": question, "answer": answer, "intent": intent}


def get_interaction_history(user_id: int, limit: int = 20) -> list[dict]:
    rows = (
        MentorInteraction.query.filter_by(user_id=user_id)
        .order_by(MentorInteraction.created_at.desc()).limit(limit).all()
    )
    return [r.to_dict() for r in rows]

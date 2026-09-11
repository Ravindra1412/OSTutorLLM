"""
app/code_review/services/llm_review_engine.py

The LLM Review Engine (Section 1/6). Makes the actual LLM calls that
review logic, readability, best practices, efficiency, style, and
security — reusing Part 3.6's LLM Service (provider-agnostic, with
built-in fallback handling) and the Part 3.8 prompt templates.

Explicitly does NOT rewrite the student's entire solution (Section 6's
own instruction): every prompt template used here (improvement_
suggestions_prompt.txt, security_review_prompt.txt, code_review_
prompt.txt) is written to request a *direction*, not corrected code —
enforced at the prompt-authoring level, consistent with the same
philosophy as the Tutor Engine's hint-ladder prompts.
"""

import json

from app.ai.prompts import manager as prompt_manager
from app.ai.services.llm_service import generate_reply
from app.utils.logger import get_ai_logger


def get_improvement_suggestions(topic: str, student_script: str) -> dict:
    """Section 6 (logic/readability/best practices/efficiency).
    Returns {"strengths": [...], "improvements": [...]}, falling back
    to an honest empty-but-valid structure (never a crash) if the LLM
    output isn't parsable JSON."""
    messages = prompt_manager.build_improvement_suggestions_messages(topic, student_script)
    result = generate_reply(messages)
    if not result.success:
        return {"strengths": [], "improvements": [], "fallback_message": result.text}

    try:
        raw = result.text.strip()
        if raw.startswith("```"):
            raw = raw.strip("`").lstrip("json").strip()
        parsed = json.loads(raw)
        return {
            "strengths": parsed.get("strengths", []),
            "improvements": parsed.get("improvements", []),
        }
    except (ValueError, TypeError) as exc:
        get_ai_logger().warning("Improvement-suggestions LLM output unparsable: %s", exc)
        return {"strengths": [], "improvements": [], "raw_text": result.text}


def get_security_review(topic: str, student_script: str) -> str:
    """Section 6 (security dimension) — distinct from the pre-LLM
    Security Scanner (Section 11), which blocks clearly dangerous
    submissions before they ever reach here. This call reviews secure
    *coding practice* (quoting, eval safety, permission choices) on
    submissions that already passed that earlier gate."""
    messages = prompt_manager.build_security_review_messages(topic, student_script)
    result = generate_reply(messages)
    return result.text


def get_best_practices_note(topic: str) -> str:
    messages = prompt_manager.build_best_practices_messages(topic)
    result = generate_reply(messages)
    return result.text


def explain_static_finding(topic: str, finding) -> str:
    """Section 8 — 'why it is incorrect', generated per static-analysis
    finding on demand (called by the Hint Engine flow, not eagerly for
    every finding, to bound LLM cost per review). Deliberately
    withholds the corrected code — used for hint stages 1-3 only."""
    messages = prompt_manager.build_error_explanation_messages(
        topic=topic, category=finding.category, severity=finding.severity,
        line_number=finding.line_number, static_message=finding.message,
    )
    result = generate_reply(messages)
    return result.text


def give_final_guidance(topic: str, finding) -> str:
    """Section 7 — Final Guidance. Distinct from explain_static_finding:
    this one explicitly reveals the corrected construct, only called
    once the hint ladder is exhausted. Using the SAME function for
    stages 3 and 4 was a real content-quality bug caught during live
    testing this phase (both produced identical guiding-only text with
    no actual fix ever shown) — see docs/project-report-part3.8.md's
    verification log."""
    messages = prompt_manager.build_final_guidance_messages(
        topic=topic, category=finding.category, line_number=finding.line_number, static_message=finding.message,
    )
    result = generate_reply(messages)
    return result.text


def get_staged_code_review_reply(topic: str, student_script: str) -> str:
    """The main conversational review call (Section 6), reusing Part
    3.6's code_review_prompt.txt — staged, one-issue-at-a-time critique."""
    messages = prompt_manager.build_code_review_full_messages(topic, student_script)
    result = generate_reply(messages)
    return result.text

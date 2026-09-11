"""
app/code_review/services/feedback_generator.py

The Feedback Generator (Section 1/8). Assembles the final structured
feedback object shown to the student, combining:
  - What is correct (LLM strengths list)
  - What is incorrect (static findings + security findings)
  - Why it is incorrect (per-finding messages, already educational —
    see analyzer.py's message text — LLM explanation available on
    demand via the Hint Engine flow, not eagerly for every finding)
  - How to improve (LLM improvements list)
  - Alternative approaches / best practices (LLM best-practices note)
  - Common mistakes / reference commands (drawn from the static
    findings' own categories, which already name the relevant command
    family — e.g. a "shebang" finding references `#!/bin/bash`)

This module does NOT call the LLM itself — it composes results the
caller (review_service.py) already gathered from llm_review_engine.py,
keeping this a pure data-shaping function that's trivially testable.
"""

from dataclasses import dataclass, field


@dataclass
class EducationalFeedback:
    strengths: list = field(default_factory=list)
    static_findings: list = field(default_factory=list)
    security_findings: list = field(default_factory=list)
    improvements: list = field(default_factory=list)
    best_practices_note: str = ""
    staged_review_reply: str = ""

    def to_dict(self) -> dict:
        return {
            "strengths": self.strengths,
            "static_findings": [
                {"category": f.category, "severity": f.severity, "line_number": f.line_number, "message": f.message}
                for f in self.static_findings
            ],
            "security_findings": [
                {"category": f.category, "description": f.pattern_description, "line_number": f.line_number}
                for f in self.security_findings
            ],
            "improvements": self.improvements,
            "best_practices_note": self.best_practices_note,
            "staged_review_reply": self.staged_review_reply,
        }


def build_feedback(
    static_findings: list, security_findings: list, llm_improvements: dict,
    best_practices_note: str, staged_review_reply: str,
) -> EducationalFeedback:
    return EducationalFeedback(
        strengths=llm_improvements.get("strengths", []),
        static_findings=static_findings,
        security_findings=security_findings,
        improvements=llm_improvements.get("improvements", []),
        best_practices_note=best_practices_note,
        staged_review_reply=staged_review_reply,
    )

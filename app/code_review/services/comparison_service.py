"""
app/code_review/services/comparison_service.py

Code Comparison (Section 10). Walks a CodeReviewSession's submission
chain (Part 3.8's CodeSubmission.submission_number ordering) to show
the student their actual improvement over time: original vs. latest,
a line-level diff, and a plain-language improvement summary derived
from the score deltas the Scoring Engine already computed for each
submission — no separate LLM call needed for this, since the score
breakdown already IS a structured measure of what changed.
"""

import difflib
import json
from dataclasses import dataclass, field


@dataclass
class ComparisonResult:
    original_code: str
    improved_code: str
    diff_lines: list = field(default_factory=list)   # unified diff, ready to render
    score_deltas: dict = field(default_factory=dict)   # dimension -> (old, new, delta)
    improvement_summary: str = ""


def compare_submissions(original_submission, latest_submission) -> ComparisonResult:
    diff = list(difflib.unified_diff(
        original_submission.code_text.splitlines(),
        latest_submission.code_text.splitlines(),
        fromfile=f"submission #{original_submission.submission_number}",
        tofile=f"submission #{latest_submission.submission_number}",
        lineterm="",
    ))

    old_scores = json.loads(original_submission.scores_json) if original_submission.scores_json else {}
    new_scores = json.loads(latest_submission.scores_json) if latest_submission.scores_json else {}

    deltas = {}
    for dimension in set(old_scores) | set(new_scores):
        old_val = old_scores.get(dimension, 0)
        new_val = new_scores.get(dimension, 0)
        deltas[dimension] = {"old": old_val, "new": new_val, "delta": round(new_val - old_val, 2)}

    summary = _build_summary(deltas)

    return ComparisonResult(
        original_code=original_submission.code_text,
        improved_code=latest_submission.code_text,
        diff_lines=diff,
        score_deltas=deltas,
        improvement_summary=summary,
    )


def _build_summary(deltas: dict) -> str:
    improved = [dim for dim, d in deltas.items() if dim != "overall" and d["delta"] > 0]
    regressed = [dim for dim, d in deltas.items() if dim != "overall" and d["delta"] < 0]
    overall_delta = deltas.get("overall", {}).get("delta", 0)

    if overall_delta > 0:
        headline = f"Nice improvement — your overall score went up by {overall_delta} points."
    elif overall_delta < 0:
        headline = f"Your overall score dropped by {abs(overall_delta)} points on this revision."
    else:
        headline = "Your overall score stayed about the same on this revision."

    parts = [headline]
    if improved:
        parts.append(f"Improved: {', '.join(improved)}.")
    if regressed:
        parts.append(f"Worth another look: {', '.join(regressed)}.")
    return " ".join(parts)

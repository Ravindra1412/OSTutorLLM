"""
app/code_review/services/scoring_engine.py

The Scoring Engine (Section 1/9). Computes an 8-dimension score
breakdown + overall score, deterministically derived from the Static
Analysis Engine's findings (Section 5) — NOT from an LLM call, so
scoring is consistent, explainable, and free (no LLM cost per score).
The LLM Review Engine's qualitative feedback (Section 6/8) explains
the "why", this module computes the "how much."

Each dimension starts at 100 and is deducted per relevant finding,
floored at 0. Weights reflect how directly each static category maps
to that dimension (e.g. a syntax error affects Syntax heavily and
Correctness moderately, but not Documentation at all).
"""

from dataclasses import dataclass

# category -> {dimension: deduction_per_finding}
_DEDUCTION_MAP = {
    "syntax": {"syntax": 25, "correctness": 15},
    "shebang": {"best_practices": 10, "style": 5},
    "naming": {"readability": 8, "style": 5},
    "unused_variable": {"logic": 10, "readability": 5},
    "infinite_loop": {"logic": 15, "correctness": 10},
    "style": {"style": 5, "readability": 3},
    "comments": {"documentation": 20},
}

DIMENSIONS = ("correctness", "logic", "syntax", "readability", "efficiency", "style", "documentation", "best_practices")


@dataclass
class ScoreBreakdown:
    correctness: float
    logic: float
    syntax: float
    readability: float
    efficiency: float
    style: float
    documentation: float
    best_practices: float

    @property
    def overall(self) -> float:
        return round(sum(getattr(self, d) for d in DIMENSIONS) / len(DIMENSIONS), 2)

    def to_dict(self) -> dict:
        return {d: getattr(self, d) for d in DIMENSIONS} | {"overall": self.overall}


def compute_score(static_findings: list, security_findings: list, efficiency_hint: float | None = None) -> ScoreBreakdown:
    """`efficiency_hint` (0-100, optional) allows the LLM Review Engine
    to nudge the Efficiency dimension based on genuine algorithmic
    observations static analysis can't detect (e.g. an O(n^2) loop
    pattern) — defaults to 90 (a mild, non-punitive baseline) when no
    LLM signal is available, since efficiency concerns are rarely
    severe in short learning-exercise scripts."""
    scores = {d: 100.0 for d in DIMENSIONS}

    for finding in static_findings:
        deductions = _DEDUCTION_MAP.get(finding.category, {})
        for dimension, amount in deductions.items():
            scores[dimension] = max(0.0, scores[dimension] - amount)

    for _ in security_findings:
        scores["correctness"] = max(0.0, scores["correctness"] - 20)
        scores["best_practices"] = max(0.0, scores["best_practices"] - 15)

    if efficiency_hint is not None:
        scores["efficiency"] = max(0.0, min(100.0, efficiency_hint))
    else:
        scores["efficiency"] = 90.0

    return ScoreBreakdown(**scores)

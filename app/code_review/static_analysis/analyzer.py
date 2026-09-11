"""
app/code_review/static_analysis/analyzer.py

The Static Analysis Engine (Section 1/5). Deliberately implemented as
PURE PATTERN ANALYSIS over the submitted text — it never executes,
sources, or interprets the student's script server-side. This is a
security-motivated architectural decision, not a shortcut: executing
arbitrary student-submitted shell code on the server is precisely the
class of risk Section 11 asks this system to prevent, so "run it in a
sandbox" is correctly deferred to Section 20's Future Enhancements
(Docker-based Execution) once real container isolation exists, rather
than attempted unsafely now.

Detects (Section 5): syntax errors (heuristic — unbalanced quotes/
brackets, unclosed control structures), missing shebang, poor naming
(single-letter/ambiguous variable names), unused variables (declared,
never referenced), infinite loops (a `while true`/`while :` loop with
no visible break/exit/return path), unsafe commands (delegated to the
dedicated Security Scanner, Section 11 — kept separate so a security
finding and a style finding are never conflated), style violations
(inconsistent indentation, trailing whitespace, line length), missing
comments.
"""

import re
from dataclasses import dataclass, field


@dataclass
class StaticFinding:
    category: str      # "syntax" | "shebang" | "naming" | "unused_variable" | "infinite_loop" | "style" | "comments"
    severity: str       # "error" | "warning" | "info"
    line_number: int | None
    message: str


@dataclass
class StaticAnalysisResult:
    findings: list = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "warning")


def analyze(code: str) -> StaticAnalysisResult:
    findings = []
    lines = code.splitlines()

    findings.extend(_check_shebang(lines))
    findings.extend(_check_syntax_balance(code, lines))
    findings.extend(_check_naming(lines))
    findings.extend(_check_unused_variables(code, lines))
    findings.extend(_check_infinite_loops(lines))
    findings.extend(_check_style(lines))
    findings.extend(_check_comments(lines))

    return StaticAnalysisResult(findings=findings)


def _check_shebang(lines: list) -> list:
    if not lines or not lines[0].strip().startswith("#!"):
        return [StaticFinding(
            category="shebang", severity="warning", line_number=1,
            message="Missing shebang line (e.g. `#!/bin/bash`) — without it, the script's interpreter "
                    "depends on how it's invoked, which can behave inconsistently across systems.",
        )]
    return []


def _check_syntax_balance(code: str, lines: list) -> list:
    """Heuristic, not a real parser: counts opening/closing control
    keywords and quote balance. Sufficient to catch the most common
    beginner mistakes (Section 5) without needing to execute the
    script."""
    findings = []

    # NOTE: for/while/until all close with `done` in Bash — checking
    # each opener against the total `done` count independently (as an
    # earlier version of this function did) produces false-positive
    # mismatches whenever a script correctly uses just ONE of the three
    # (e.g. a lone `for...done` loop would incorrectly also be flagged
    # as a mismatched `while` and a mismatched `until`, since 0 opens
    # of each don't match the 1 shared `done` close). Caught via live
    # testing (docs/project-report-part3.8.md's verification log) and
    # fixed by grouping all three under one shared-closer check.
    done_openers = ["for", "while", "until"]
    done_opens_total = sum(len(re.findall(rf"(?:^|\s){opener}\b", code)) for opener in done_openers)
    done_closes_total = len(re.findall(r"(?:^|\s)done\b", code))
    if done_opens_total != done_closes_total:
        findings.append(StaticFinding(
            category="syntax", severity="error", line_number=None,
            message=f"Mismatched loop openers vs `done`: found {done_opens_total} loop opener(s) "
                    f"(`for`/`while`/`until`) but {done_closes_total} `done` — every loop must be closed with `done`.",
        ))

    control_pairs = [("if", "fi"), ("case", "esac")]
    for opener, closer in control_pairs:
        opens = len(re.findall(rf"(?:^|\s){opener}\b", code))
        closes = len(re.findall(rf"(?:^|\s){closer}\b", code))
        if opens != closes:
            findings.append(StaticFinding(
                category="syntax", severity="error", line_number=None,
                message=f"Mismatched `{opener}`/`{closer}`: found {opens} `{opener}` but {closes} `{closer}` — "
                        f"every `{opener}` block must be closed with `{closer}`.",
            ))

    if_count = len(re.findall(r"(?:^|\s)if\b", code))
    then_count = len(re.findall(r"(?:^|\s)then\b", code))
    if if_count > then_count:
        findings.append(StaticFinding(
            category="syntax", severity="error", line_number=None,
            message="An `if` appears to be missing its `then` — Bash requires `then` on the same line "
                    "(after `;`) or the next line.",
        ))

    for i, line in enumerate(lines, start=1):
        stripped = line.split("#", 1)[0]  # ignore comments for quote balance
        if stripped.count('"') % 2 != 0:
            findings.append(StaticFinding(
                category="syntax", severity="error", line_number=i,
                message="Unbalanced double quotes on this line.",
            ))

    return findings


_POOR_NAME_PATTERN = re.compile(r"\b([a-zA-Z])=")


def _check_naming(lines: list) -> list:
    findings = []
    seen = set()
    for i, line in enumerate(lines, start=1):
        for match in _POOR_NAME_PATTERN.finditer(line):
            name = match.group(1)
            if name not in seen and name not in ("i", "j", "k", "n"):  # loop counters are a widely-accepted exception
                seen.add(name)
                findings.append(StaticFinding(
                    category="naming", severity="info", line_number=i,
                    message=f"Variable `{name}` has a single-letter name — a more descriptive name "
                            f"(e.g. `count`, `filename`) makes the script easier to read and maintain.",
                ))
    return findings


_VAR_ASSIGN_PATTERN = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)=")


def _check_unused_variables(code: str, lines: list) -> list:
    findings = []
    for i, line in enumerate(lines, start=1):
        match = _VAR_ASSIGN_PATTERN.match(line)
        if not match:
            continue
        name = match.group(1)
        use_pattern = re.compile(rf"\$\{{?{re.escape(name)}\b")
        occurrences = len(use_pattern.findall(code))
        if occurrences == 0:
            findings.append(StaticFinding(
                category="unused_variable", severity="warning", line_number=i,
                message=f"Variable `{name}` is assigned but never referenced (`${name}` or `${{{name}}}`) "
                        f"anywhere else in the script — likely dead code, or a typo elsewhere.",
            ))
    return findings


def _check_infinite_loops(lines: list) -> list:
    findings = []
    code_joined = "\n".join(lines)
    infinite_patterns = [r"while\s+true\b", r"while\s*:\s*(;|$)", r"while\s*\[\s*1\s*\]"]
    has_exit_path = bool(re.search(r"\b(break|exit|return)\b", code_joined))

    for i, line in enumerate(lines, start=1):
        for pattern in infinite_patterns:
            if re.search(pattern, line):
                if not has_exit_path:
                    findings.append(StaticFinding(
                        category="infinite_loop", severity="warning", line_number=i,
                        message="This loop has no visible `break`, `exit`, or `return` anywhere in the script — "
                                "if that's intentional (e.g. a daemon loop), fine, but double-check it's not "
                                "an accidental infinite loop.",
                    ))
    return findings


def _check_style(lines: list) -> list:
    findings = []
    for i, line in enumerate(lines, start=1):
        if line != line.rstrip():
            findings.append(StaticFinding(
                category="style", severity="info", line_number=i, message="Trailing whitespace on this line.",
            ))
        if len(line) > 100:
            findings.append(StaticFinding(
                category="style", severity="info", line_number=i,
                message=f"Line is {len(line)} characters long — consider breaking it up for readability "
                        f"(conventional style guides suggest wrapping around 80-100 chars).",
            ))
        if "\t" in line and "    " in line:
            findings.append(StaticFinding(
                category="style", severity="info", line_number=i,
                message="Mixed tabs and spaces for indentation on this line — pick one convention consistently.",
            ))
    return findings


def _check_comments(lines: list) -> list:
    non_blank = [l for l in lines if l.strip() and not l.strip().startswith("#!")]
    comment_lines = [l for l in non_blank if l.strip().startswith("#")]
    if len(non_blank) >= 8 and len(comment_lines) == 0:
        return [StaticFinding(
            category="comments", severity="info", line_number=None,
            message="This script has no comments at all — even a short comment above each major section "
                    "helps a reader (and your future self) understand intent, not just mechanics.",
        )]
    return []

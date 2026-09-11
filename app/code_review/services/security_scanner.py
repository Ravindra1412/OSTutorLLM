"""
app/code_review/services/security_scanner.py

The Security Scanner (Section 11). Runs BEFORE static analysis or any
LLM call — the same "structural enforcement before the expensive/risky
step" pattern used by the Tutor Engine's Safety Layer (Part 3.6) and
the Quiz Engine's ownership checks (Part 3.7). A submission that trips
this scanner is never sent to the LLM and never stored as a "clean"
review; it's stored with `is_safe=False` and a canned educational
explanation, so the student still gets SOME feedback (why this is
risky) rather than a silent rejection.

Explicitly NOT a sandbox or execution-based check — this is a
pattern/heuristic scanner over the text (consistent with the Static
Analysis Engine's no-execution design decision). It cannot catch every
possible obfuscated attack, and is documented as such; its job is to
catch the common, recognizable classes of dangerous shell operations
a student might paste in (accidentally or while testing the system),
not to be a hardened security product.
"""

import re
from dataclasses import dataclass, field

# Whole-filesystem or unrecoverable destructive operations
_DESTRUCTIVE_PATTERNS = [
    (r"rm\s+-rf\s+/(?:\s|$)", "Recursive force-delete of the root filesystem (`rm -rf /`)."),
    (r"rm\s+-rf\s+~", "Recursive force-delete of the entire home directory."),
    (r"rm\s+-rf\s+\*", "Recursive force-delete using an unqualified wildcard — very easy to run in the wrong directory by accident."),
    (r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;", "Classic fork bomb pattern (`:(){ :|:& };:`)."),
    (r"mkfs(\.\w+)?\s+/dev/", "Filesystem-format command targeting a raw device."),
    (r"dd\s+if=.*of=/dev/(sd|hd|nvme)", "`dd` writing directly to a raw disk device — can destroy all data on that disk."),
    (r">\s*/dev/sd[a-z]\b", "Direct write redirection to a raw disk device."),
]

# Remote-code-execution / supply-chain risk patterns
_RCE_PATTERNS = [
    (r"curl\s+[^\n|]*\|\s*(sudo\s+)?(bash|sh)\b", "Piping a downloaded remote script directly into a shell (`curl ... | bash`) — executes untrusted code with no review step."),
    (r"wget\s+[^\n|]*\|\s*(sudo\s+)?(bash|sh)\b", "Piping a downloaded remote script directly into a shell (`wget ... | bash`)."),
    (r"eval\s+.*\$\(", "`eval` combined with command substitution — a classic command-injection vector if the substituted content is ever attacker-influenced."),
]

# Unauthorized-access / privilege patterns
_ACCESS_PATTERNS = [
    (r"chmod\s+777\b", "Setting world-writable+executable permissions (`chmod 777`) — a common but risky over-broad permission grant."),
    (r"sudo\s+su\s*-?\s*$", "Escalating to a root shell — outside the scope of a shell-scripting exercise and risky to run casually."),
    (r"passwd\s+root\b", "Attempting to change the root password from within a script."),
    (r"/etc/shadow\b", "Direct reference to the system's shadow password file."),
]

ALL_PATTERN_GROUPS = [
    ("destructive", _DESTRUCTIVE_PATTERNS),
    ("remote_code_execution", _RCE_PATTERNS),
    ("unauthorized_access", _ACCESS_PATTERNS),
]


@dataclass
class SecurityFinding:
    category: str
    pattern_description: str
    line_number: int | None


@dataclass
class SecurityScanResult:
    is_safe: bool
    findings: list = field(default_factory=list)


def scan(code: str) -> SecurityScanResult:
    findings = []
    lines = code.splitlines()

    for category, patterns in ALL_PATTERN_GROUPS:
        for pattern, description in patterns:
            regex = re.compile(pattern)
            for i, line in enumerate(lines, start=1):
                if regex.search(line):
                    findings.append(SecurityFinding(category=category, pattern_description=description, line_number=i))

    return SecurityScanResult(is_safe=(len(findings) == 0), findings=findings)


def explanation_for_findings(findings: list) -> str:
    """Section 11 — 'Explain how unsafe submissions are handled.' A
    single educational (not scolding) explanation shown to the student
    instead of proceeding to LLM review, naming what was found and why
    it's flagged, without shaming the student for testing boundaries —
    a very normal thing for a learner to do."""
    if not findings:
        return ""
    lines = ["This submission wasn't sent for review because it contains one or more patterns "
             "that are considered unsafe to review automatically:"]
    for f in findings:
        location = f" (line {f.line_number})" if f.line_number else ""
        lines.append(f"- {f.pattern_description}{location}")
    lines.append(
        "\nIf this was intentional exploration (e.g. \"what does this command do?\"), that's a great question "
        "for the Tutor Chat instead — it can explain the concept and its risks without needing to review it as "
        "a working submission. If this was accidental (e.g. copy-pasted from an example), please edit it out "
        "and resubmit."
    )
    return "\n".join(lines)

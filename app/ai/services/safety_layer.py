"""
app/ai/services/safety_layer.py

The Safety Layer (Section 1/13, Topic Restriction Section 10). Runs
BEFORE any LLM call, on the student's raw message, and can short-
circuit the whole turn with a safe, canned response — meaning safety
here does not depend on the LLM behaving correctly, consistent with
the same "structural enforcement over prompt wording" philosophy as
the Hint Engine.

Three independent checks, each returning a SafetyResult:
  1. Prompt injection / role override / system-prompt-leakage attempts
  2. Unsafe command requests (destructive/malicious intent)
  3. Off-topic requests (Section 10 — restricted to Linux/shell/OS)

This is explicitly documented as heuristic/pattern-based, not a
trained classifier — sufficient to demonstrate the architecture and
catch the common/obvious cases, with a noted upgrade path (an LLM-
based classification pass) once a real provider is always available
in production.
"""

import re
from dataclasses import dataclass

from app.ai.services.hint_engine import _HINT_REQUEST_PATTERNS, _ANSWER_REQUEST_PATTERNS

_INJECTION_PATTERNS = [
    r"ignore (all |any )?(previous|prior|above) instructions",
    r"disregard (all |any )?(previous|prior|above) (instructions|rules)",
    r"you are now\b",
    r"act as (a|an)\b",
    r"pretend (to be|you are)\b",
    r"reveal your (system )?prompt",
    r"what (is|are) your (system )?instructions",
    r"repeat (the words|everything) above",
    r"jailbreak",
    r"dan mode",
    r"developer mode",
    r"new instructions?:",
    r"forget (your|all) (rules|instructions)",
]

_UNSAFE_COMMAND_PATTERNS = [
    r"rm\s+-rf\s+/(?!\S)",              # rm -rf / with nothing after (whole-filesystem wipe)
    r"how (do|can) i (hack|breach|exploit)\b",
    r"\bddos\b", r"\bkeylogger\b", r"\bransomware\b",
    r"how (do|can) i (delete|wipe) (someone|another user'?s|a server'?s) (data|files)\b.*without (permission|authorization)",
    r"bypass (login|authentication|password) (of|for) (someone|another|a) ",
]

_ON_TOPIC_KEYWORDS = [
    "linux", "shell", "bash", "terminal", "command", "script", "cli",
    "permission", "chmod", "chown", "grep", "sed", "awk", "pipe", "redirect",
    "process", "kernel", "file system", "filesystem", "directory", "cron",
    "sudo", "ssh", "package manager", "apt", "systemctl", "loop", "variable",
    "conditional", "operating system", "memory management", "scheduling",
    "deadlock", "thread", "environment variable", "path", "regex",
]


@dataclass
class SafetyResult:
    allowed: bool
    reason: str | None = None
    canned_response: str | None = None


def check_prompt_injection(message: str) -> SafetyResult:
    text = message.lower()
    for pattern in _INJECTION_PATTERNS:
        if re.search(pattern, text):
            return SafetyResult(
                allowed=False,
                reason="prompt_injection_attempt",
                canned_response=(
                    "I can't change my role or ignore my teaching guidelines — but I'm happy to keep "
                    "helping you with Linux commands or shell programming. What would you like to work on?"
                ),
            )
    return SafetyResult(allowed=True)


def check_unsafe_command(message: str) -> SafetyResult:
    text = message.lower()
    for pattern in _UNSAFE_COMMAND_PATTERNS:
        if re.search(pattern, text):
            return SafetyResult(
                allowed=False,
                reason="unsafe_command_request",
                canned_response=(
                    "I can't help with commands or techniques intended to damage systems, bypass security, "
                    "or access data without authorization. I'm glad to explain how commands like `rm`, `chmod`, "
                    "or permissions work safely and legitimately, though — want to explore that instead?"
                ),
            )
    return SafetyResult(allowed=True)


def check_topic_restriction(message: str) -> SafetyResult:
    """Section 10. A message is considered on-topic if it contains at
    least one Linux/shell/OS-related keyword, is short/conversational
    (greetings, "yes", "ok", answers to a diagnostic question rarely
    repeat topic keywords), OR reads as a hint/continuation request
    ("I don't know", "still stuck", "give me a hint") — these are, by
    definition, continuations of whatever on-topic conversation is
    already underway, not new off-topic questions, and rejecting them
    was a real false-positive caught during live testing of this
    module (see docs/project-report-part3.6.md's verification log).
    Only a sufficiently long message with NO topic vocabulary and NO
    continuation-phrase markers is treated as a genuine off-topic
    question."""
    text = message.lower()
    word_count = len(text.split())

    if word_count <= 12:
        return SafetyResult(allowed=True)  # short/conversational replies always pass through

    if any(keyword in text for keyword in _ON_TOPIC_KEYWORDS):
        return SafetyResult(allowed=True)

    if any(re.search(pattern, text) for pattern in _HINT_REQUEST_PATTERNS + _ANSWER_REQUEST_PATTERNS):
        return SafetyResult(allowed=True)  # continuation of an existing tutoring turn, not a new topic

    return SafetyResult(
        allowed=False,
        reason="off_topic",
        canned_response=(
            "That's outside what I can help with here — I'm focused specifically on Linux commands, shell "
            "programming, and basic Operating Systems concepts. Do you have a question in one of those areas?"
        ),
    )


def run_all_checks(message: str) -> SafetyResult:
    """Runs every check in order, returning the first failure. Order
    matters: injection/unsafe-command checks run before topic
    restriction, since a malicious message should get the specific
    safety message, not a generic 'off-topic' one."""
    for check in (check_prompt_injection, check_unsafe_command, check_topic_restriction):
        result = check(message)
        if not result.allowed:
            return result
    return SafetyResult(allowed=True)

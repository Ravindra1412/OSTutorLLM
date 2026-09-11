"""
app/code_review/services/code_validator.py

Input validation (Section 3's "Validate Input" workflow step). Runs
even before the Security Scanner — a submission that's empty, absurdly
long, or not valid UTF-8 text is rejected with a clear message before
any pattern scanning or LLM cost is spent on it, consistent with the
existing app/utils/validators.py's ValidationError pattern (Part 3.3).
"""

from app.utils.validators import ValidationError

MAX_CODE_LENGTH = 20_000  # characters — generous for a learning-exercise shell script, bounds LLM cost/latency
MIN_CODE_LENGTH = 3


def validate_code_submission(code: str, topic_name: str) -> str:
    if code is None:
        raise ValidationError("Please paste a shell script to review.", field="code")

    code = code.strip("\n")  # trim only leading/trailing blank lines, preserve internal formatting/indentation

    if len(code.strip()) < MIN_CODE_LENGTH:
        raise ValidationError("The submitted script is too short to review meaningfully.", field="code")

    if len(code) > MAX_CODE_LENGTH:
        raise ValidationError(
            f"Script is too long ({len(code)} characters, max {MAX_CODE_LENGTH}). "
            f"Please submit a focused excerpt rather than an entire project.",
            field="code",
        )

    try:
        code.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValidationError("Script contains characters that could not be validated as text.", field="code") from exc

    if not topic_name or not topic_name.strip():
        raise ValidationError("Please select a topic for this review.", field="topic")

    return code

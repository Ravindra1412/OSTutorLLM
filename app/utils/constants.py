"""
app/utils/constants.py

Central location for magic strings/numbers used across the backend.
Importing from here instead of re-typing literals avoids typo bugs
(e.g. "faculty" vs "Faculty") spreading across multiple files.
"""

# --- Roles ---
ROLE_STUDENT = "student"
ROLE_FACULTY = "faculty"
VALID_ROLES = (ROLE_STUDENT, ROLE_FACULTY)

# --- Password policy ---
MIN_PASSWORD_LENGTH = 8

# --- API response status strings (Section 10 standardized envelope) ---
STATUS_SUCCESS = "success"
STATUS_FAIL = "fail"       # expected/handled failure (validation, auth, not found)
STATUS_ERROR = "error"     # unexpected server-side error

# --- Hint verbosity preference bounds (Part 3.1, Section 8.3) ---
HINT_VERBOSITY_MIN = 1
HINT_VERBOSITY_MAX = 3

"""
app/mentor/

Part 3.13 — AI Learning Mentor. The "brain" that coordinates every
existing engine (Tutor, Quiz, Code Review, Analytics, Faculty) rather
than rebuilding any of them.

CRITICAL DESIGN PRINCIPLE: this package contains almost no new data
computation. Learning Health, Confidence, Recommendations, Achievements,
Timeline, and class-wide analytics are ALL already real, working,
tested services from Parts 3.7-3.10. The Mentor's job is orchestration —
calling the right existing services in the right order and combining
their output into one coherent view — not a parallel analytics
pipeline. Where a genuinely new computation is needed (Learning Health
scoring, Confidence breakdown, Study Plan generation, natural-language
Insights, the Assistant's Q&A), it is built here, on top of the
existing services' data, following the same "explainable heuristic, not
a black box" principle Part 3.9's predictive_engine.py established.

services/
├── mentor_engine.py       The central orchestrator (Section 3) — the
│                             one entry point that loads a student's
│                             complete profile and drives the whole
│                             workflow described in Section 4.
├── student_model.py         Student Profile Intelligence (Section 5) —
│                               assembles the raw signals every other
│                               mentor service reads.
├── learning_health.py         Learning Health Engine (Section 6) — NEW
│                                 computation: a single 0-100 score with
│                                 named, explained factors.
├── confidence_engine.py         Confidence Engine (Section 7) — NEW
│                                   computation: per-dimension confidence
│                                   (topic/command/programming/overall)
│                                   with a plain-language "why."
├── study_planner.py               AI Study Planner (Section 9) — NEW:
│                                     generates and persists a real
│                                     daily/weekly/monthly schedule from
│                                     the student's actual weak topics.
├── insights_engine.py               AI Learning Insights (Section 12) —
│                                       NEW: natural-language sentences,
│                                       each traceable to a specific
│                                       stored number, never invented.
└── mentor_assistant.py                 Student + Faculty AI Assistant
                                           (Sections 13-14) — a rule-
                                           based intent router over the
                                           real services above, logged
                                           to MentorInteraction
                                           ("mentor_memory").
"""

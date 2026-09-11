"""
app/analytics/

Part 3.9 — Progress Tracking, Learning Analytics & Personalized
Recommendation System. Mirrors the package-per-engine pattern already
established by app/quiz/ (Part 3.7) and app/code_review/ (Part 3.8):
a `services/` folder of single-responsibility modules, no route logic
inside this package (routes live in app/routes/analytics_routes.py and
app/routes/analytics_pages_routes.py and are thin translation layers
over these services, exactly like every prior engine).

This package reads from — and does not duplicate — the data every
other engine already writes: Progress (Part 3.4, updated by Tutor/Quiz/
CodeReview), QuizAttempt/QuizHistory (Part 3.4/3.7), CodeReviewSession/
CodeSubmission (Part 3.8), ChatSession (Part 3.4/3.6), Achievement/Badge/
StudentProfile (Part 3.4). Two new tables are added this phase
(LearningTimeline, Recommendation) because no existing table captures
"a chronological log of learning events" or "a persisted, explainable
recommendation" — everything else is aggregation over data that
already exists.
"""

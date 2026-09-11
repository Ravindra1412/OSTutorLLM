"""
app/faculty/

Part 3.10 — Faculty Dashboard & Administration. Mirrors the
package-per-domain pattern from app/quiz/ (3.7), app/code_review/
(3.8), and app/analytics/ (3.9): a `services/` folder of single-
responsibility modules; routes (app/routes/faculty_*_routes.py) are
thin translation layers over these.

Scope note (documented once, here, rather than repeated in every
service docstring): this schema has no `courses`/`enrollments` concept
(see faculty_routes.py's original Part 3.4 placeholder docstring) —
OSTutorLLM models one shared curriculum, not multiple sections/courses
per faculty member. Every "faculty" view in this package therefore
scopes over ALL student users, not a per-faculty roster. This is an
honest architectural boundary, not an oversight — introducing real
course/enrollment tables would be a significant, separate schema
change out of this phase's brief (Section 24 lists "Department
Dashboard" as a future enhancement for exactly this reason).
"""

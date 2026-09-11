# OSTutorLLM - Presentation Guide (PPT Structure)

## Slide-by-Slide Structure

**Slide 1 - Title**
OSTutorLLM: An Interactive AI-Powered Step-by-Step Tutor for Linux Commands
and Shell Programming Using Large Language Models. Your name, institution,
date.

**Slide 2 - Problem Statement**
Static textbooks and unattended CLI practice give no adaptive feedback;
generic AI chatbots answer directly and undermine learning; instructors lack
visibility into class-wide weak spots until exam time.
*Speaker notes*: Open with a relatable scenario - a student stuck on
`chmod` at 11pm with no one to ask.

**Slide 3 - Objectives**
List the 6-7 objectives from `docs/PROJECT_REPORT_SUPPORT.md`'s Objectives
section, one line each.

**Slide 4 - Architecture Slide**
Use the diagram from `docs/ARCHITECTURE.md` Section 1 (Browser -> Flask
Blueprints -> Service Layer -> Database -> LLM Provider). Keep it to 4 boxes
max on the slide itself - the layered diagram, not the full package tree.
*Speaker notes*: Emphasize the pluggable LLM layer - "this exact same code
runs with zero API cost via our offline Mock provider, and with a real LLM
via a one-line config change."

**Slide 5 - Innovation Slide**
Pull the 5-row table from `docs/RESEARCH_AND_INNOVATION.md` Section 3 -
condense to the top 3 rows if slide space is tight (shared Progress model,
explainable analytics, free-tier-first architecture).

**Slide 6 - The Five Engines (Overview)**
One line each: AI Tutor (teaches, doesn't answer), Quiz Engine (13 question
types, adaptive), Code Review (static analysis + LLM feedback), Analytics
(cross-engine, explainable), Faculty Dashboard (class-wide administration).

**Slide 7 - Demo Transition Slide**
"Let's see it working." (Switch to live demo here - see DEMO_SCRIPT.md.)

**Slide 8 - Results Slide**
- 409 automated tests, 82% code coverage
- Real measured performance (dashboard <1s, quiz gen <2s - pull exact
  numbers from `docs/PERFORMANCE_EVALUATION.md`)
- 5 real bugs found and fixed via adversarial testing (state this as a
  STRENGTH - it shows rigor, not weakness)

**Slide 9 - Testing & Security Slide**
Testing pyramid: unit -> integration -> API -> security -> performance.
Security highlights: password hashing, RBAC, injection-proof (ORM),
file-upload validation, session security - pull from `docs/SECURITY_REVIEW.md`.

**Slide 10 - Limitations (Be Honest)**
No course/enrollment model, Mock provider != real LLM quality, no live-LLM
adversarial testing, dev-server-only performance numbers. Evaluators respect
honesty about scope far more than an unrealistic "no limitations" claim.

**Slide 11 - Future Scope Slide**
Pull top 4-5 from `docs/RESEARCH_AND_INNOVATION.md` Section 8: voice tutor,
multilingual, LMS integration, RAG over institutional notes, fine-tuned LLM.

**Slide 12 - Conclusion**
Restate the problem -> solution -> validated result in 3 sentences.

**Slide 13 - Thank You / Questions**
Contact info, repository link.

## Demo Flow (Detailed Script)

See `docs/DEMO_SCRIPT.md` for the complete, minute-by-minute script.

## General Presentation Tips

- Rehearse the live demo at least twice beforehand using the seeded demo
  accounts (`docs/USER_MANUAL_STUDENT.md` / `USER_MANUAL_FACULTY.md`) so you
  aren't creating accounts live in front of evaluators.
- Have `docs/DEMO_SCRIPT.md`'s Backup Demo Strategy ready (screenshots/video)
  in case of a live technical failure.
- When asked a question you don't have a confident answer to, it is
  significantly better to say "that's a great question, I'd want to verify
  that" than to guess - see `docs/VIVA_PREPARATION.md` for prepared answers
  to the most likely questions.

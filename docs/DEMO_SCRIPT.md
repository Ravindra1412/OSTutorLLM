# OSTutorLLM - Demonstration Script

## Pre-Demo Checklist

- [ ] App running and reachable (`python run.py` or Docker), verify
      `GET /health` returns 200 before evaluators arrive.
- [ ] `flask seed-db` has been run - demo accounts exist.
- [ ] Browser has NO leftover session cookies from a previous test - start
      from a clean/incognito window.
- [ ] `AI_PROVIDER` is set to whatever you intend to demo - if using Mock,
      be ready to explain why (free/offline) rather than apologize for it.
- [ ] Have `docs/VIVA_PREPARATION.md` open on a second screen/tab for quick
      reference if questions come up mid-demo.
- [ ] Backup plan ready (see below) in case of live failure.

## Live Demo Script (~10-12 minutes)

### 1. Student Journey (4-5 min)
1. Register a new student account live (or log in as `aisha.khan@example.edu`
   / `Password123!`).
2. Land on the Dashboard - point out level/XP/streak/daily goal (all real,
   computed values, not static mockup numbers).
3. Start an AI Tutor session on a topic (e.g. "File Permissions"). Send one
   message, show the staged, non-answer-dumping response. Ask for a hint -
   show the hint ladder response.
4. Start a quiz on the same topic. Answer 1-2 questions, submit, show the
   score plus explanation.
5. Return to Dashboard - show the new quiz attempt and tutor session now
   appearing in Recent Activity / Timeline (emphasize: this updated live,
   no manual refresh trick).

### 2. Code Review (2 min)
1. Submit a small shell script (a deliberately imperfect one - e.g. missing
   a shebang, an unquoted variable) for review on a shell-programming topic.
2. Show the static-analysis findings plus AI feedback. Point out: it
   explains WHY, doesn't just hand over corrected code.
3. (Optional) Request a hint to show the 4-stage ladder.

### 3. Faculty View (3-4 min)
1. Log out, log in as faculty (`elena.ruiz@example.edu` / `Password123!`).
2. Dashboard - show total/active students, class averages.
3. Analytics - show class-wide weak topics (should reflect the low quiz
   score just generated in Step 1, if using the same topic - a nice, real
   "look, it updated automatically" moment).
4. Content Management - show a topic's version history / restore feature.
5. Author a quick quiz live (2 questions), publish it.
6. Reports - download one report live (CSV or PDF) to show it's a real file,
   not a mockup.

### 4. Wrap-up (1 min)
Return to the Results slide numbers (409 tests, 82% coverage) and state them
out loud as a closing credibility point.

## Faculty Demonstration Flow (If Presenting Faculty-Side Only)

Steps 3 above, expanded: also show Assignment creation plus grading, and the
AI Tutor admin toggle (disable it, show a student's session attempt fail
with the real error message, re-enable it) - this is a strong, concrete
"real admin control, not a mockup" moment.

## Expected Questions and Suggested Answers

See `docs/VIVA_PREPARATION.md` for the full 100-question bank. The 5 most
likely to come up immediately after a live demo:

**Q: Is this using a real AI model or is it faked?**
A: The architecture supports real LLMs (OpenAI, DeepSeek, Ollama) via a
one-line config change - what you just saw uses our offline Mock provider by
default, specifically so the whole platform is free and reproducible for
grading/testing without an API key. (Optionally switch AI_PROVIDER live if
you have a configured key.)

**Q: What happens if two students use the quiz at the same time?**
A: Verified directly - Part 3.11's performance suite fires 10 concurrent
quiz-start requests from the same account and confirms zero race-condition
failures (every response is a clean success or a documented conflict, never
a crash).

**Q: How do you know your analytics numbers are correct, not just displayed?**
A: They're computed live from the same database tables the quiz/tutor/code
review engines write into - not cached or precomputed. (Demonstrate by
generating a new quiz attempt and immediately refreshing the analytics page.)

**Q: What if the AI gives a wrong answer?**
A: The AI Tutor is designed to guide and question rather than assert facts
directly wherever possible; for factual OS content it's grounded in the
prompt's own topic-restriction instructions. This is an acknowledged
limitation of any LLM-based system - see our documented Known Limitations
rather than a claim of perfection.

**Q: How is this different from just using ChatGPT?**
A: Three concrete differences: (1) staged Socratic teaching with a hint
ladder instead of an immediate answer, (2) tightly integrated with a real
quiz/code-review/analytics pipeline so learning signal accumulates over
time per student, and (3) a faculty administration layer with class-wide
visibility - none of which a generic chatbot provides.

## Live Demo Checklist (Print This)

- [ ] Health check passes
- [ ] Demo accounts work
- [ ] Tutor session starts and responds
- [ ] Quiz can be started and submitted
- [ ] Code review accepts a submission
- [ ] Faculty dashboard loads with real numbers
- [ ] A report downloads successfully
- [ ] Backup plan (screenshots/video) is open in another tab, just in case

## Backup Demo Strategy

If live demo fails (network issue, unexpected error):
1. Stay calm, acknowledge it briefly, switch to backup materials - don't
   spend more than 15-20 seconds troubleshooting live.
2. Use pre-recorded screenshots or a screen-recording video (prepare one in
   advance covering the same flow as the live script above) stored locally,
   not dependent on network access.
3. Pivot to walking through the code/architecture slides and the test suite
   output (docs/project-report-part3.11.md's real numbers) as evidence of
   functionality, even without a live click-through.

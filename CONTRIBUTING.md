# Contributing to OSTutorLLM

Thanks for your interest in improving OSTutorLLM. This project follows a
consistent set of engineering conventions established across Parts 3.1-3.12 —
please read this before opening a PR.

## Ground Rules (established since Part 3.3)

1. **Never rewrite working code for style alone.** If a module works and is
   tested, extend it additively rather than restructuring it, unless there's
   a genuine correctness reason.
2. **Every bug fix ships with a regression test.** A fix isn't done until a
   test fails before it and passes after it — see `docs/BUG_REPORT_TEMPLATE.md`.
3. **Preserve backward compatibility.** New migrations must be additive
   (new tables/nullable columns) unless there's no other option — see any
   file under `migrations/versions/` for the established pattern.
4. **Document scope decisions, don't hide them.** If something is
   deliberately out of scope (see any `docs/project-report-part3.X.md`'s
   "Future Enhancements" section for examples), say so in a comment/docstring
   rather than silently omitting it.
5. **Free-tier-first.** Prefer free/open-source dependencies and the `mock`
   AI provider for anything that needs to run without paid API access,
   consistent with this being a student-reproducible project.

## Development Setup

```bash
git clone <repo-url> ostutorllm
cd ostutorllm
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # edit SECRET_KEY at minimum
flask db upgrade
flask seed-db                        # optional sample data
python run.py
```

See `docs/DEPLOYMENT_GUIDE.md` for OS-specific instructions and
`docs/DEVELOPER_GUIDE.md` for the codebase architecture tour.

## Running Tests Before You Submit

```bash
./run_tests.sh              # full suite except performance (fast)
./run_tests.sh all           # everything including performance
./run_tests.sh coverage       # full suite + HTML coverage report
```

A PR that drops the passing test count or lowers coverage on the module it
touches needs justification in the PR description.

## Code Style

- Python: standard library `logging`, type hints on public function
  signatures, docstrings that explain *why* a design choice was made, not
  just *what* the code does (see any `app/*/services/*.py` file for the
  established tone).
- Flask routes stay thin — business logic belongs in `app/*/services/`, not
  in the route function itself.
- Frontend: vanilla JS (no framework), Bootstrap 5 + the existing design
  system (`app/static/css/design-system.css`) — don't introduce a new CSS
  framework or a JS bundler for a single feature.

## Commit Messages

Reference the part/section being touched when relevant, e.g.:
```
Fix quiz attempt ownership check (Part 3.11, Section 14)
```

## Pull Request Checklist

- [ ] Tests pass (`./run_tests.sh all`)
- [ ] New functionality has new tests, not just a manual check
- [ ] No secrets committed (check `.env` is not staged)
- [ ] Migration is additive, or the breaking change is justified in the PR description
- [ ] Relevant `docs/` file updated if behavior changed

## Reporting Bugs / Requesting Features

Use `docs/BUG_REPORT_TEMPLATE.md` for bugs. For feature requests, check
`docs/RESEARCH_AND_INNOVATION.md`'s Future Research Directions and any
`docs/project-report-part3.X.md`'s "Future Enhancements" section first —
your idea may already be scoped there.

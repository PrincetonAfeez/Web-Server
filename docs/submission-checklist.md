# Course submission checklist

Complete locally. **Do not push** `src/`, `tests/`, `demo/`, or `docs/` to GitHub
unless policy changes.

## Repository

- [ ] Local tag created: `git tag v0.2.1`
- [ ] README polished (diagram + defense sentence + 3 commands)
- [ ] `.gitignore` excludes `demo/`, `docs/`, `src/`, `tests/`, planning drafts
- [ ] Optional: push **only** root metadata files if the course needs a public URL

## Written materials (submit to LMS)

- [ ] `docs/capstone-report.md` → export PDF if required
- [ ] `docs/production-reflection.md` included or merged into report
- [ ] ADR index (`docs/adr/README.md`) referenced in report

## Evidence

- [ ] Test run screenshot or CI log (local): `python -m pytest`
- [ ] `docs/benchmark-results.md` filled with real numbers
- [ ] Django screenshot or short demo video

## Oral defense

- [ ] Rehearse `docs/demo-rehearsal.md` end-to-end
- [ ] Practice `docs/defense-questions.md` (17 prompts)
- [ ] Record backup video → `submission/` (gitignored)

## Release (local only)

- [ ] `RELEASE_v0.2.1.md` reviewed
- [ ] GitHub Release **not** created unless you intentionally publish

## Personalization

- [ ] Confirm name/copyright in `pyproject.toml` and `LICENSE`
- [ ] Replace GitHub URLs if your remote differs

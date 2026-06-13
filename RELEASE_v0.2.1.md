# pyserve v0.2.1 — Release notes (local)

**Tag:** `v0.2.1` (created locally; not pushed to GitHub)

## Summary

Educational HTTP/1.1 WSGI server — socket to Django, by hand.

## Highlights

- Protocol fixes: empty Host, case-insensitive HTTP version, POST `Content-Length`,
  `417` for unsupported `Expect`, async executor/listener parity
- Submission packaging: benchmark harness, TOML config, CLF access logs, static
  files with `304`, stats JSON endpoint, Django+HTMX dashboard, Flask demo
- Documentation: capstone report, defense Q&A, demo rehearsal, ADR normalization

## Install (local)

```powershell
python -m pip install -r requirements-all.txt -c constraints.txt
```

## Verify

```powershell
python -m pytest
python -m ruff check src tests
python -m mypy src
python demo/benchmark.py --model serial
```

## GitHub Release (optional, manual)

If you later choose to publish a release without pushing source trees:

1. Push only tracked root files (README, CHANGELOG, requirements, etc.)
2. `gh release create v0.2.1 --notes-file RELEASE_v0.2.1.md`

**Do not** publish `src/`, `tests/`, `demo/`, or `docs/` if they must stay local.

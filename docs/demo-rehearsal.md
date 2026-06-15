# Live demo rehearsal checklist

Rehearse in order. Time target: 15–20 minutes.

## Before you start

- [ ] Fresh terminal; port 8000 free
- [ ] `pip install -r requirements-all.txt -c constraints.txt` done
- [ ] Working directory = repository root
- [ ] `docs/defense-questions.md` reviewed once

## Demo flow

### 1. Trivial app (serial)

```powershell
pyserve --app demo.trivial_app:application --host 127.0.0.1 --port 8000 --model serial
curl -i http://127.0.0.1:8000/
```

- [ ] Explain status line, headers, body, `Content-Length`

### 2. Malformed request → 400

Send incomplete headers via `nc` or a one-line Python socket client.

- [ ] Server stays up for a follow-up good request

### 3. POST echo

```powershell
pyserve --app demo.echo_app:application --port 8000 --model serial
curl -i -X POST http://127.0.0.1:8000/echo -H "Content-Type: text/plain" --data "hello"
```

### 4. HEAD no-body

```powershell
curl -I http://127.0.0.1:8000/
```

### 5. Threaded concurrency

```powershell
pyserve --app demo.trivial_app:application --port 8000 --model threaded --workers 4
```

Run several concurrent `curl` commands.

### 6. Async model

```powershell
pyserve --app demo.trivial_app:application --port 8000 --model async --workers 4
```

- [ ] Explain executor bridge (ADR 0002)

### 7. Benchmark (local evidence)

```powershell
python demo/benchmark.py --model serial --workers 8 --requests 30
python demo/benchmark.py --model threaded --workers 8 --requests 30
python demo/benchmark.py --model async --workers 8 --requests 30
```

- [ ] Cite `docs/benchmark-results.md`

### 8. Django proof

```powershell
pyserve --app demo.django_demo.config.wsgi:application --port 8000 --model threaded --stats-path /_pyserve/stats
```

- [ ] Browser: `http://127.0.0.1:8000/`
- [ ] Browser: `http://127.0.0.1:8000/dashboard/` (HTMX polls stats)

### 9. Optional stretch demos

- [ ] Flask: `pyserve --app demo.flask_app:application --port 8000`
- [ ] Static: `pyserve --app demo.trivial_app:application --static demo/public`
- [ ] CLF logs: add `--access-log --access-log-clf`

## Closing narrative

Trace the path aloud: **TCP → HTTP parse → WSGI environ → app → HTTP response → TCP**

## Backup

- [ ] Record screen capture of this script once (`submission/demo-recording.mp4` suggested)
- [ ] Keep terminal scrollback / notes from rehearsal

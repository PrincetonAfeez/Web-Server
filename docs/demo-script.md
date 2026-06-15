# Demo Script

## Trivial App

```powershell
python -m pip install -r requirements.txt
pyserve --app demo.trivial_app:application --host 127.0.0.1 --port 8000 --model serial
curl -i http://127.0.0.1:8000/
```

If `pyserve` is not on `PATH` after installation, replace `pyserve` with
`python -m pyserve`.

## Error Demo

Use `demo.error_app` with `--debug-errors` to show traceback bodies on `500`
responses:

```powershell
pyserve --app demo.error_app:application --host 127.0.0.1 --port 8000 --model serial --debug-errors
curl -i http://127.0.0.1:8000/
```

## Benchmark

```powershell
python demo/benchmark.py --model serial --workers 8 --requests 30
python demo/benchmark.py --model threaded --workers 8 --requests 30 --server-threads 4
python demo/benchmark.py --model async --workers 8 --requests 30 --server-threads 4
```

See `docs/benchmark-results.md` for sample numbers and interpretation.

## Django + HTMX stats

```powershell
pyserve --app demo.django_demo.config.wsgi:application --port 8000 --model threaded --stats-path /_pyserve/stats
```

Open `http://127.0.0.1:8000/dashboard/` — HTMX polls `/_pyserve/stats`.

## POST Body

Use `demo.echo_app` so the request body is echoed back:

```powershell
pyserve --app demo.echo_app:application --host 127.0.0.1 --port 8000 --model serial
curl -i -X POST http://127.0.0.1:8000/echo -H "Content-Type: text/plain" --data "hello"
```

## Threaded Mode

```powershell
pyserve --app demo.trivial_app:application --host 127.0.0.1 --port 8000 --model threaded
```

## Asyncio Mode

```powershell
pyserve --app demo.trivial_app:application --host 127.0.0.1 --port 8000 --model async
```

## Django Proof

Install Django first if needed, then run:

```powershell
pyserve --app demo.django_demo.config.wsgi:application --host 127.0.0.1 --port 8000 --model threaded
curl -i http://127.0.0.1:8000/
```

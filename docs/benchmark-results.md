# Benchmark results (local run)

Generated on Windows with Python 3.14, repository root, trivial WSGI app
returning `200 OK` / `ok`, `keep_alive_timeout=0`, 8 client threads × 30 requests
each (240 total requests per model).

Command:

```powershell
python demo/benchmark.py --model <serial|threaded|async> --workers 8 --requests 30
```

Threaded/async server uses `--server-threads 4`.

## Results

| Model | Success | Failures | Total (s) | req/s | Mean (ms) | p50 (ms) | p95 (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| serial | 240 | 0 | 0.33 | 737 | 10.3 | 6.8 | 23.4 |
| threaded | 240 | 0 | 0.09 | 2537 | 2.3 | 2.0 | 5.0 |
| async | 240 | 0 | 0.22 | 1094 | 4.4 | 3.2 | 14.8 |

## Interpretation (capstone defense)

- **Serial** handles one connection at a time; concurrent clients queue behind the
  single accept/handler loop — highest latency, lowest throughput.
- **Threaded** serves multiple connections concurrently; best throughput in this
  micro-benchmark because WSGI work is tiny and threads scale well on localhost.
- **Async** overlaps socket I/O efficiently but still pays executor overhead for
  WSGI calls; faster than serial, slower than threaded here.

These numbers substantiate ADR 0001: model choice is a tradeoff, not a universal
winner. Re-run locally before defending; localhost loops are not production load.

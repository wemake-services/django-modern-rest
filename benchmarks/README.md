# Benchmarks!


## Important Notice

All benchmarks are always synthetic.
Benchmarks do not test real performance, they test ideas of performance.


## Environment

- Python: `3.13.7`, no JIT, no free-threading
- OS: MacOS 15.6.1
- Device: Apple M2 Pro, mid 2023, 16 Gb of RAM


## Assumptions

- We test only the API part, because ``django_modern_rest`` does not include
  any database features, we want to make sure that the part that
  we are covering is measured, not something else
- We test the minimal possible app
- We use the same exact data for all apps
- We test production-like setups with `DEBUG=False`
- We test both sync (`gunicorn`)
  and async (`uvicorn`) version if the requested mode is supported
  (yes, DRF, we are looking at you)
- But, we don't compare sync to async and vice a versa,
  because they have different logic, different deploy strategies, etc


## Results

### Async

| framework   | is_async   |      rps |   tpr |
|-------------|------------|----------|-------|
| fastapi     | True       | 10854.6  | 1.843 |
| dmr         | True       |  7026.27 | 2.846 |
| ninja       | True       |  4359.12 | 4.588 |

### Sync

| framework   | is_async   |      rps |   tpr |
|-------------|------------|----------|-------|
| dmr         | False      |  5774.94 | 3.463 |
| ninja       | False      |  3888.13 | 5.144 |
| drf         | False      |  3024.24 | 6.613 |


## Running the script:

Pre-requirements:
- [`ab`](https://httpd.apache.org/docs/2.4/programs/ab.html)

Run from `benchmarks/` directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run_benchmark.py
```


## Manual debug

Single request:

```bash
curl -X POST \
  'http://127.0.0.1:8000/async/user/?per_page=1&count=2&page=3&filter=abc' \
  -d @payload.json \
  -H 'Content-Type: application/json' \
  -H 'X-API-Token: some-token-example' \
  -H 'X-Request-Origin: some-origin'
```

Manual bench:

```bash
ab -c 20 -n 1000 -l -p payload.json \
  -H 'X-API-Token: some-token-example' \
  -H 'X-Request-Origin: some-origin' \
  -T 'application/json' \
  'http://127.0.0.1:8000/async/user/?per_page=1&count=2&page=3&filter=abc'
```

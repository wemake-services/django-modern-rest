# Benchmarks!

[![CodSpeed](https://img.shields.io/endpoint?url=https://codspeed.io/badge.json)](https://app.codspeed.io/wemake-services/django-modern-rest?utm_source=badge)


## Important Notice

All benchmarks are always synthetic.
Benchmarks do not test real performance, they test ideas of performance.


## Environment

- Python: `3.13.7`, no JIT, no free-threading
- OS: MacOS 15.6.1
- Device: Apple M2 Pro, mid 2023, 16 Gb of RAM


## Assumptions

- We test only the API part, because `django-modern-rest` does not include
  any database features, we want to make sure that the part that
  we are covering is measured, not something else
- We test the minimal possible app
- We use semantically equivalent request and response data for all apps
- We benchmark a 50-item response for JSON serialization throughput
- We test production-like setups with `DEBUG=False`
- DMR uses its production setting `validate_responses=False`; every framework
  otherwise follows its native typed-response serialization path
- We test sync handlers with `gunicorn`, and async handlers with `gunicorn`
  and four `uvicorn_worker.UvicornWorker` workers
  (yes, DRF, we are looking at you)
- But, we don't compare sync to async and vice versa,
  because they have different logic, different deploy strategies, etc


## Measurements

Each target is measured once for three seconds with 20 concurrent requests
using `hey` with HTTP keep-alive enabled. The final table reports RPS and
average request time in milliseconds. Failed requests and non-2xx responses
abort the run. Benchmark dependencies are pinned in `requirements.txt`.


## Results

### Async

| framework   | is_async   |      rps |   tpr ms |
|-------------|------------|----------|----------|
| fastapi     | True       | 2231.98  |      8.9 |
| dmr         | True       | 1921.16  |     10.4 |
| ninja       | True       |  696.699 |     28.6 |

### Sync

| framework   | is_async   |      rps |   tpr ms |
|-------------|------------|----------|----------|
| dmr         | False      | 2368.02  |      8.4 |
| ninja       | False      |  709.831 |     28.1 |
| drf         | False      |  461.096 |     43.1 |


## Running the script:

Pre-requirements:
- `hey` (`brew install hey` on macOS)

Run from the project root:

```bash
just bench::bench
```

Shared benchmark settings are constants in `apps/config.py`: host, concurrency,
measurement duration, workers, threads, and response size. Change `RESPONSE_ITEMS`
there to update the response size for all frameworks at once.


## Manual debug

Single request:

```bash
curl -X POST \
  'http://127.0.0.1:8000/async/users/' \
  -d @payload.json \
  -H 'Content-Type: application/json'
```

Manual bench:

```bash
hey -c 20 -z 3s -D payload.json \
  -m POST \
  -T 'application/json' \
  'http://127.0.0.1:8000/async/users/'
```


## Feature benchmarks

We also benchmark several our features that can be used independently.

We run tests in `./tests/` using https://github.com/CodSpeedHQ/pytest-codspeed
and upload results to https://app.codspeed.io/wemake-services/django-modern-rest

See the [`codspeed.yml`](https://github.com/wemake-services/django-modern-rest/blob/master/.github/workflows/codspeed.yml) workflow.

Run `just benchmarks` from the root dir to run them.

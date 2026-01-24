import gc
import os
import re
import subprocess
import time

from tabulate import tabulate

_HOST = 'http://127.0.0.1:8000'

_ASYNC_COMMAND = 'uvicorn --workers=4 --no-access-log apps.{0}:async_app'
_ASYNC_ENDPOINTS = [
    (
        '/async/user/?per_page=1&count=2&page=3&filter={0}',
        'POST',
        'payload.json',
        (
            'X-API-Token: some-token-example',
            'X-Request-Origin: some-origin',
        ),
    ),
]

_SYNC_COMMAND = 'gunicorn apps.{0}:sync_app --workers=4 --threads=16'
_SYNC_ENDPOINTS = [
    (
        '/sync/user/?per_page=1&count=2&page=3&filter={0}',
        'POST',
        'payload.json',
        (
            'X-API-Token: some-token-example',
            'X-Request-Origin: some-origin',
        ),
    ),
]

_AB_COMMAND = [
    'ab',
    '-c',
    '20',
    '-n',
    '1000',
    '-l',
    '-T',
    'application/json',
    '-s',
    '60',
    '-v',
    '4',
]


def _run_app(app: str, *, is_async: bool) -> subprocess.Popen:
    kill_old = os.system('kill -9 $(lsof -t -i:8000) 2>/dev/null')
    if kill_old not in {0, 256}:
        raise RuntimeError(app, kill_old)

    cmd = _ASYNC_COMMAND if is_async else _SYNC_COMMAND
    process = subprocess.Popen(
        cmd.format(app),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=True,
        text=True,
    )
    time.sleep(5)
    return process


_Endpoint = tuple[str, str, str, tuple[str, ...]]


def _check_app(app: str, endpoint: _Endpoint) -> None:
    url = _HOST + endpoint[0].format(app)
    response = os.system(f'curl -s --head {url} 1>/dev/null')
    if response:
        raise RuntimeError(app, response)


def _run_bench(
    app: str,
    endpoint: _Endpoint,
    *,
    is_async: bool,
) -> tuple[float, float]:
    cmd = [
        *_AB_COMMAND,
        '-p',
        endpoint[2],
        '-m',
        endpoint[1],
    ]

    for header in endpoint[3]:
        cmd.extend(('-H', header))

    cmd.append(_HOST + endpoint[0].format(app))

    print(' '.join(cmd))

    process = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        timeout=100,
    )

    if process.returncode != 0:
        raise RuntimeError(process.returncode, process.stdout, process.stderr)

    assert 'Non-2xx responses:' not in process.stdout, process.stdout
    assert 'Failed requests:        0' in process.stdout, process.stdout
    tpr = re.search(  # pyrefly: ignore[missing-attribute]
        r'Time per request:\s+([\d.]+)\s+\[ms\]\s+\(mean\)',
        process.stdout,
    ).group(1)
    rps = re.search(  # pyrefly: ignore[missing-attribute]
        r'Requests per second:\s+([\d.]+)',
        process.stdout,
    ).group(1)
    if float(tpr) >= 50:
        raise RuntimeError(process.stdout)
    return float(rps), float(tpr)


_APPS = {
    'dmr': [True, False],
    'fastapi': [True],
    'drf': [False],
    'ninja': [True, False],
}


def run_benchmark() -> None:
    timings = []
    for app, modes in _APPS.items():
        for is_async in modes:
            local_timings = (0, 0)
            print(f'Starting {app} {is_async=}')
            try:
                process = _run_app(app, is_async=is_async)
                container = _ASYNC_ENDPOINTS if is_async else _SYNC_ENDPOINTS
                assert container
                for endpoint in container:
                    print('Checking...')
                    _check_app(app, endpoint)
                    print(f'Benching {app} {is_async=}')
                    per_endpoint = _run_bench(app, endpoint, is_async=is_async)
                    print(per_endpoint)
                    local_timings = (
                        local_timings[0] + per_endpoint[0],
                        local_timings[1] + per_endpoint[1],
                    )
                timings.append([
                    app,
                    is_async,
                    *local_timings,  # pyrefly: ignore[not-iterable]
                ])
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except Exception:
                    process.kill()
            gc.collect()
            time.sleep(10)

    print(
        tabulate(
            timings,
            ['framework', 'is_async', 'rps', 'tpr'],
            tablefmt='github',
        ),
    )


if __name__ == '__main__':
    run_benchmark()

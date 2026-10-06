import gc
import re
import subprocess
import time

from apps import config
from tabulate import tabulate

_ASYNC_COMMAND = (
    'gunicorn',
    'apps.{0}:async_app',
    '--workers',
    str(config.WORKERS),
    '--worker-class',
    'uvicorn_worker.UvicornWorker',
)
_ASYNC_ENDPOINT = ('/async/users/', 'POST', 'payload.json')

_SYNC_COMMAND = (
    'gunicorn',
    'apps.{0}:sync_app',
    '--workers',
    str(config.WORKERS),
    '--threads',
    str(config.THREADS),
)
_SYNC_ENDPOINT = ('/sync/users/', 'POST', 'payload.json')

_APPS = {
    'dmr': (True, False),
    'fastapi': (True,),
    'drf': (False,),
    'ninja': (True, False),
}

_Endpoint = tuple[str, str, str]


def _run_app(
    app: str,
    *,
    is_async: bool,
) -> subprocess.Popen[bytes]:
    command = _ASYNC_COMMAND if is_async else _SYNC_COMMAND
    return subprocess.Popen(
        [part.format(app) for part in command],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )


def _request_command(endpoint: _Endpoint) -> list[str]:
    return [
        'curl',
        '--silent',
        '--show-error',
        '--output',
        '/dev/null',
        '--write-out',
        '%{http_code}',
        '--request',
        endpoint[1],
        '--data-binary',
        f'@{endpoint[2]}',
        '--header',
        'Content-Type: application/json',
        config.HOST + endpoint[0],
    ]


def _wait_for_app(
    app: str,
    process: subprocess.Popen[bytes],
    endpoint: _Endpoint,
) -> None:
    for _ in range(100):
        return_code = process.poll()
        if return_code is not None:
            raise RuntimeError(f'{app} exited with code {return_code}')

        response = subprocess.run(
            _request_command(endpoint),
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if response.returncode == 0 and response.stdout.startswith('2'):
            return
        time.sleep(0.1)

    raise RuntimeError(f'{app} did not become ready')


def _run_bench(endpoint: _Endpoint) -> tuple[float, float]:
    command = [
        'hey',
        '-c',
        str(config.CONCURRENCY),
        '-t',
        '60',
        '-z',
        f'{config.DURATION_SECONDS}s',
        '-T',
        'application/json',
        '-m',
        endpoint[1],
        '-D',
        endpoint[2],
        config.HOST + endpoint[0],
    ]
    print(' '.join(command))
    process = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=max(100, config.DURATION_SECONDS + 30),
    )
    if process.returncode != 0:
        raise RuntimeError(process.returncode, process.stdout, process.stderr)

    output = process.stdout
    statuses = re.findall(r'\[(\d{3})\]\s+(\d+) responses', output)
    if (
        not statuses
        or any(not 200 <= int(status) < 300 for status, _ in statuses)
        or 'Error distribution:' in output
    ):
        raise RuntimeError(output)
    rps = re.search(r'Requests/sec:\s+([\d.]+)', output)
    average = re.search(r'Average:\s+([\d.]+) secs', output)
    if rps is None or average is None:
        raise RuntimeError(output)
    return float(rps.group(1)), 1000 * float(average.group(1))


def _stop_app(process: subprocess.Popen[bytes]) -> None:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def run_benchmark() -> None:
    timings = []
    for app, modes in _APPS.items():
        for is_async in modes:
            print(f'Starting {app} {is_async=}')
            endpoint = _ASYNC_ENDPOINT if is_async else _SYNC_ENDPOINT
            process = _run_app(app, is_async=is_async)
            try:
                _wait_for_app(app, process, endpoint)
                print(f'Benching {app} {is_async=}')
                rps, tpr = _run_bench(endpoint)
                print((rps, tpr))
                timings.append([app, is_async, rps, tpr])
            finally:
                _stop_app(process)
            gc.collect()

    print(
        tabulate(
            timings,
            ['framework', 'is_async', 'rps', 'tpr ms'],
            tablefmt='github',
        ),
    )


if __name__ == '__main__':
    run_benchmark()

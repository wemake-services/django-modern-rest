import importlib
import json
import os
import shutil
import socket
import subprocess  # noqa: S404
import sys
import time
from contextlib import contextmanager, redirect_stderr
from multiprocessing import Process
from pathlib import Path
from typing import TYPE_CHECKING, cast

import django
import httpx
import uvicorn
from django.apps import apps
from django.conf import settings
from django.core.handlers.asgi import ASGIHandler
from django.urls import clear_url_caches
from sphinx.application import Sphinx
from sphinx.errors import ExtensionError

_EXAMPLE_MODULE = Path('examples/openapi/setting_up_schema.py')
_RAW_JSON_PATH = Path('_static/generated/openapi.json')
_DEFAULT_URLCONF = 'url_conf'
_DJANGO_SETTINGS_MODULE = 'server.settings'
_OPENAPI_URL = '/docs/openapi.json/'

if TYPE_CHECKING:
    from collections.abc import Iterator


def _get_available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('localhost', 0))
        return int(sock.getsockname()[1])


def _add_to_syspath(path: Path) -> None:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def _setup_django(docs_dir: Path) -> None:
    project_dir = docs_dir.parent
    django_app_dir = project_dir / 'django_test_app'

    _add_to_syspath(docs_dir)
    _add_to_syspath(project_dir)
    _add_to_syspath(django_app_dir)

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', _DJANGO_SETTINGS_MODULE)
    if not settings.configured:
        settings.configure(
            ROOT_URLCONF=_DEFAULT_URLCONF,
            ALLOWED_HOSTS=['*'],
            DEBUG=True,
            SECRET_KEY='dummy-key-for-examples',  # noqa: S106
            INSTALLED_APPS=[
                'django.contrib.auth',
                'django.contrib.contenttypes',
                'dmr',
                'dmr.security.jwt.blocklist',
            ],
            MIDDLEWARE=[],
            USE_TZ=True,
            HTTP_BASIC_USERNAME='admin',
            HTTP_BASIC_PASSWORD='pass',  # noqa: S106
        )
    if not apps.ready:
        django.setup()


def _get_example_module_name(module_path: Path, docs_dir: Path) -> str:
    _add_to_syspath(docs_dir)
    return '.'.join(module_path.relative_to(docs_dir).with_suffix('').parts)


def _load_example_module(module_name: str) -> None:
    sys.modules.pop(module_name, None)
    importlib.import_module(module_name)


def _start_app_process(module_name: str, docs_dir: Path, port: int) -> Process:
    proc = Process(
        target=_run_app_worker,
        args=(port, module_name, str(docs_dir)),
    )
    proc.start()
    _wait_for_app_startup(port)
    return proc


@contextmanager
def _run_app(module_name: str, docs_dir: Path) -> 'Iterator[int]':
    port = _get_available_port()
    proc = _start_app_process(module_name, docs_dir, port)
    try:
        yield port
    finally:
        proc.kill()


def _run_app_worker(port: int, module_name: str, docs_dir: str) -> None:
    _setup_django(Path(docs_dir))
    _load_example_module(module_name)
    settings.ROOT_URLCONF = module_name
    clear_url_caches()
    with redirect_stderr(Path(os.devnull).open(encoding='utf-8')):
        uvicorn.run(
            ASGIHandler(),
            port=port,
            access_log=False,
            log_level='error',
        )


def _wait_for_app_startup(port: int) -> None:
    for _ in range(100):
        try:
            httpx.get(f'http://127.0.0.1:{port}{_OPENAPI_URL}', timeout=0.1)
        except httpx.TransportError:
            time.sleep(0.1)
        else:
            return
    raise ExtensionError(f'App failed to come online on port {port}')


def _fetch_openapi_json(port: int) -> dict[str, object]:
    curl_path = shutil.which('curl')
    if curl_path is None:
        raise ExtensionError('curl executable was not found')

    proc = subprocess.run(  # noqa: S603, PLW1510
        [
            curl_path,
            '-sS',
            '--fail-with-body',
            f'http://127.0.0.1:{port}{_OPENAPI_URL}',
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise ExtensionError(proc.stderr or 'Failed to fetch openapi.json')
    return cast(dict[str, object], json.loads(proc.stdout))


def _fetch_snapshot_data(
    example_path: Path,
    docs_dir: Path,
) -> dict[str, object]:
    _setup_django(docs_dir)
    module_name = _get_example_module_name(example_path, docs_dir)
    with _run_app(module_name, docs_dir) as port:
        return _fetch_openapi_json(port)


def _dump_snapshot_data(schema_data: dict[str, object]) -> str:
    return f'{json.dumps(schema_data, indent=2, sort_keys=True)}\n'


def _write_snapshot_file(
    raw_json_path: Path,
    schema_data: dict[str, object],
) -> None:
    raw_json_path.parent.mkdir(parents=True, exist_ok=True)
    raw_json_path.write_text(
        _dump_snapshot_data(schema_data),
        encoding='utf-8',
    )


def _generate_openapi_snapshot(app: Sphinx) -> None:
    docs_dir = Path(app.srcdir)
    example_path = docs_dir / _EXAMPLE_MODULE
    raw_json_path = docs_dir / _RAW_JSON_PATH

    try:
        schema_data = _fetch_snapshot_data(example_path, docs_dir)
    except Exception as exc:  # pragma: no cover
        raise ExtensionError(
            'Failed to generate OpenAPI schema snapshot',
        ) from exc

    _write_snapshot_file(raw_json_path, schema_data)


def setup(app: Sphinx) -> None:
    """Generate OpenAPI snapshot files for the docs build."""
    app.connect('builder-inited', _generate_openapi_snapshot)

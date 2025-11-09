"""
This file contains code adapted from Litestar.

See: https://github.com/litestar-org/litestar/blob/main/tools/sphinx_ext/run_examples.py.
"""

from __future__ import annotations

import importlib
import json
import logging
import multiprocessing
import os
import platform
import re
import socket
import subprocess  # noqa: S404
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager, redirect_stderr
from pathlib import Path
from types import ModuleType
from typing import Any, ClassVar, Final, TypeAlias, cast, final

import httpx
import uvicorn
from auto_pytabs.sphinx_ext import LiteralIncludeOverride
from django.conf import settings
from django.core.handlers.asgi import ASGIHandler
from django.urls import path
from django.views import View
from docutils.nodes import Node, admonition, literal_block, title
from docutils.parsers.rst import directives
from sphinx.addnodes import highlightlang
from sphinx.application import Sphinx

if platform.system() in {'Darwin', 'Linux'}:
    multiprocessing.set_start_method('fork', force=True)

_PATH_TO_TMP_EXAMPLES: Final = '_build/_tmp_example/'
_RGX_RUN: Final = re.compile(r'# +?run:(.*)')

_AppRunArgsT: TypeAlias = dict[str, Any]

logger: Final = logging.getLogger(__name__)
ignore_missing_output: Final = True


@final
class _StartupError(RuntimeError):
    """Raised when application fails to start."""


def _get_available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(('localhost', 0))
        except OSError as error:
            raise _StartupError('Could not find an open port') from error
        else:
            return cast(int, sock.getsockname()[1])


@final
class _AppBuilder:
    """Builds a Django application from configuration."""

    def __init__(self, file_path: Path, config: _AppRunArgsT) -> None:
        """Initialize application builder with file path and configuration."""
        self.file_path = file_path
        self.config = config

    def build_app(self) -> ASGIHandler:
        """Build and return configured ASGI application."""
        self._configure_settings()
        return self._build_app()

    def _configure_settings(self) -> None:
        if settings.configured:
            return

        settings.configure(
            ROOT_URLCONF='url_conf',
            ALLOWED_HOSTS=['*'],
            DEBUG=True,
            SECRET_KEY='dummy-key-for-examples',  # noqa: S106
            INSTALLED_APPS=[
                'django.contrib.auth',
                'django.contrib.contenttypes',
                'django_modern_rest',
            ],
            MIDDLEWARE=[],
            USE_TZ=True,
        )

    def _build_app(self) -> ASGIHandler:
        file_path_without_ext = self.file_path.with_suffix('')
        module_name = str(file_path_without_ext).replace(os.sep, '.')

        sys.modules.pop(module_name, None)

        module = importlib.import_module(module_name)
        controller_name = self.config['controller']

        controller_cls = self._find_controller(module, controller_name)
        self._add_controller_to_urlpatterns(controller_cls)

        return ASGIHandler()

    def _find_controller(
        self,
        module: ModuleType,
        controller_name: str,
    ) -> View:
        controller_cls: View | None = None
        for obj_name in module.__dict__:
            module_obj = getattr(module, obj_name)
            if hasattr(module_obj, 'as_view') and obj_name == controller_name:
                controller_cls = module_obj
                break

        if controller_cls is None:
            raise RuntimeError(
                f'Controller {controller_name} not found in {self.file_path}',
            )

        return controller_cls

    def _add_controller_to_urlpatterns(
        self,
        controller_cls: View,
    ) -> None:
        url_conf_module = ModuleType('url_conf')
        url_path = _get_url_path_from_run_args(
            self.config,
        ).lstrip('/')  # noqa: WPS226

        url_conf_module.urlpatterns = [  # type: ignore[attr-defined]
            path(url_path, controller_cls.as_view()),
        ]

        sys.modules['url_conf'] = url_conf_module


def _get_url_path_from_run_args(run_args: _AppRunArgsT) -> str:
    controller_name = run_args['controller'].lower()
    url: str = run_args.get(
        'url',
        f'/api/{controller_name}/',
    )
    return url


@contextmanager
def _run_app(path: Path, config: _AppRunArgsT) -> Iterator[int]:
    """Start a Django app on an available port."""
    restart_duration = 0.2
    port = _get_available_port()
    app = _AppBuilder(path, config).build_app()

    attempts = 0
    while attempts < 100:
        proc = multiprocessing.Process(target=_run_app_worker, args=(app, port))
        proc.start()

        try:
            _wait_for_app_startup(port)
        except _StartupError:
            time.sleep(restart_duration)
            attempts += 1
            port = _get_available_port()
        else:
            yield port
            break
        finally:
            proc.kill()
    else:
        raise _StartupError(str(path))


def _run_app_worker(app: ASGIHandler, port: int) -> None:
    with redirect_stderr(Path(os.devnull).open(encoding='utf-8')):
        uvicorn.run(app, port=port, access_log=False)


def _wait_for_app_startup(port: int) -> None:
    """Wait for app to start up and become responsive."""
    for _ in range(100):
        try:
            httpx.get(f'http://127.0.0.1:{port}', timeout=0.1)
        except httpx.TransportError:
            time.sleep(0.1)
        else:
            return
    raise _StartupError(f'App failed to come online on port {port}')


def _extract_run_args(file_content: str) -> tuple[str, list[_AppRunArgsT]]:
    """Extract run args from a python file.

    Return the file content stripped of the run comments
    and a list of argument lists.
    """
    new_lines = []
    run_configs = []
    for line in file_content.splitlines():
        run_stmt_match = _RGX_RUN.match(line)
        if run_stmt_match:
            run_stmt = run_stmt_match.group(1).lstrip()
            if '# noqa' in run_stmt:
                run_stmt = run_stmt.split('# noqa')[0]
            run_configs.append(json.loads(run_stmt))
        else:
            new_lines.append(line)
    return '\n'.join(new_lines), run_configs


def _exec_examples(app_file: Path, run_configs: list[_AppRunArgsT]) -> str:
    """
    Start a server with the example application, run the specified requests.

    Run requests against it and return their results.
    """
    example_results = []

    for run_args in run_configs:
        url_path = _get_url_path_from_run_args(run_args)
        with _run_app(app_file, run_args) as port:
            example_result = _process_single_example(
                app_file,
                run_args,
                port,
                url_path,
            )
            if example_result:
                example_results.append(example_result)

    return '\n\n'.join(example_results)


def _process_single_example(
    app_file: Path,
    run_args: _AppRunArgsT,
    port: int,
    url_path: str,
) -> str:
    """Process a single example configuration."""
    args, clean_args = _build_curl_request(run_args, port, url_path)

    proc = subprocess.run(  # noqa: PLW1510, S603
        args,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise _StartupError(
            (
                f'Could not run {args!r} in {app_file}, '
                f'got {proc.returncode} error code'
            ),
            proc.stdout,
            proc.stderr,
        )
    stdout = proc.stdout.splitlines()
    if not stdout:
        logger.debug(proc.stderr)
        if not ignore_missing_output:
            logger.error(
                'Example: %s:%s yielded no results',
                app_file,
                args,
            )
        return ''

    clean_args_string = ' '.join(clean_args)
    return '\n'.join((f'$ {clean_args_string}', *stdout))


_CurlArgsT: TypeAlias = list[str]
_CurlCleanArgsT: TypeAlias = list[str]


def _build_curl_request(
    run_args: _AppRunArgsT,
    port: int,
    url_path: str,
) -> tuple[_CurlArgsT, _CurlCleanArgsT]:
    args = [
        'curl',
        '--fail-with-body',
        '-v',
        '-s',
        f'http://127.0.0.1:{port}{url_path}',
    ]
    clean_args = ['curl', f'http://127.0.0.1:8000{url_path}']

    _add_curl_flags(args, clean_args, run_args)
    _add_method(args, clean_args, run_args)
    _add_body_and_content_type(args, clean_args, run_args)
    _add_headers(args, clean_args, run_args)

    return args, clean_args


def _add_curl_flags(
    args: list[str],
    clean_args: list[str],
    run_args: _AppRunArgsT,
) -> None:
    curl_extra_args = run_args.get('curl_args', [])
    args.extend(curl_extra_args)
    clean_args.extend(curl_extra_args)


def _add_method(
    args: list[str],
    clean_args: list[str],
    run_args: _AppRunArgsT,
) -> None:
    method = run_args.get('method', 'get').upper()
    if method != 'GET':
        args.extend(['-X', method])
        clean_args.extend(['-X', method])


def _add_body_and_content_type(
    args: list[str],
    clean_args: list[str],
    run_args: _AppRunArgsT,
) -> None:
    if 'body' in run_args:
        body_data = json.dumps(run_args.get('body', {}))
        args.extend(['-d', body_data])
        clean_args.extend(['-d', body_data])

        args.extend(['-H', 'Content-Type: application/json'])
        clean_args.extend(['-H', 'Content-Type: application/json'])


def _add_headers(
    args: list[str],
    clean_args: list[str],
    run_args: _AppRunArgsT,
) -> None:
    header_flag = '-H'
    for header_name, header_value in run_args.get('headers', {}).items():
        args.extend([header_flag, f'{header_name}: {header_value}'])
        clean_args.extend([header_flag, f'{header_name}: {header_value}'])


@final
class LiteralInclude(LiteralIncludeOverride):  # type: ignore[misc]
    """Extended `.. literalinclude` directive with code execution capability."""

    option_spec: ClassVar = {
        **LiteralIncludeOverride.option_spec,
        'no-run': directives.flag,
    }

    def run(self) -> list[Node]:
        """Execute code examples and display results."""
        file_path = Path(self.env.relfn2path(self.arguments[0])[1])
        if not self._need_to_run(file_path):
            return cast(list[Node], super().run())

        clean_content, run_args = self._execute_code(file_path)
        if not run_args:
            return cast(list[Node], super().run())
        self._create_tmp_example_file(file_path, clean_content)

        nodes = cast(list[Node], super().run())

        executed_result = _exec_examples(
            file_path.relative_to(Path.cwd()),
            run_args,
        )

        if not executed_result:
            return nodes

        nodes.append(
            admonition(
                '',
                title('', 'Run result'),
                highlightlang(
                    '',
                    literal_block('', executed_result),
                    lang='shell',
                    force=False,
                    linenothreshold=sys.maxsize,
                ),
                literal_block('', executed_result),
                classes=['tip'],
            ),
        )
        return nodes

    def _need_to_run(self, file_path: Path) -> bool:
        language = self.options.get('language', '')
        no_run_in_options = 'no-run' in self.options
        not_python_file = language != 'python' and file_path.suffix != '.py'
        return not (not_python_file or no_run_in_options)

    def _execute_code(
        self,
        file_path: Path,
    ) -> tuple[str, list[_AppRunArgsT]]:
        file_content = file_path.read_text(encoding='utf-8')
        return _extract_run_args(file_content)

    def _create_tmp_example_file(
        self,
        file_path: Path,
        clean_content: str,
    ) -> None:
        cwd = Path.cwd()
        docs_dir = cwd if cwd.name == 'docs' else cwd / 'docs'
        tmp_file = (
            cwd
            / _PATH_TO_TMP_EXAMPLES
            / str(
                file_path.relative_to(docs_dir),
            ).replace('/', '_')
        )

        self.arguments[0] = f'/{tmp_file.relative_to(docs_dir)!s}'
        tmp_file.write_text(clean_content)


def setup(app: Sphinx) -> None:
    """Register Sphinx extension directives."""
    tmp_examples_path = Path.cwd() / _PATH_TO_TMP_EXAMPLES
    tmp_examples_path.mkdir(exist_ok=True, parents=True)

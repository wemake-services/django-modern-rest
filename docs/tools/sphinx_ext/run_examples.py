"""
This file contains code adapted from Litestar.

See:
https://github.com/litestar-org/litestar/blob/main/tools/sphinx_ext/run_examples.py

This module is also allowed to contain AI slop.
"""

from __future__ import annotations

import ast
import importlib
import json
import logging
import multiprocessing
import os
import re
import shlex
import socket
import subprocess  # noqa: S404
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager, redirect_stderr, suppress
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any, ClassVar, Final, TypeAlias, cast
from urllib.parse import urlencode

import django
import httpx
import uvicorn
import xmltodict_rs as xmltodict
from django.conf import settings
from django.core.handlers.asgi import ASGIHandler
from django.db import IntegrityError
from django.test import override_settings
from django.urls import URLPattern, clear_url_caches, path
from django.views import View
from docutils.nodes import (
    Element,
    General,
    Node,
    Text,
    admonition,
    container,
    literal_block,
    title,
)
from docutils.parsers.rst import directives
from sphinx.addnodes import highlightlang
from sphinx.application import Sphinx
from sphinx.directives.code import LiteralInclude as _LiteralInclude
from typing_extensions import override

from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import build_404_handler, build_500_handler
from dmr.settings import Settings, clear_settings_cache

if TYPE_CHECKING:
    from sphinx.writers.html5 import HTML5Translator


def _get_mp_context() -> Any:
    default_start_method = 'spawn' if sys.platform == 'win32' else 'fork'
    start_method = os.environ.get('DMR_SPAWN_METHOD', default_start_method)
    try:
        return multiprocessing.get_context(start_method)
    except ValueError as error:
        raise RuntimeError(
            (
                f'Unsupported multiprocessing start method: {start_method!r}. '
                'Set DMR_SPAWN_METHOD to a valid value for this platform.'
            ),
        ) from error


_MP_CONTEXT: Final = _get_mp_context()

_BASE_DIR: Final = Path(__file__).parent.parent.parent.parent

_PATH_TO_TMP_EXAMPLES: Final = '_build/_tmp_example/'
_RGX_RUN: Final = re.compile(r'# +?run:(.*)')
_RGX_RUN_COMMENT: Final = re.compile(r'^\s*#\s*run:')
_RGX_OPENAPI: Final = re.compile(r'# +?openapi:(.*)')
_RGX_OPENAPI_COMMENT: Final = re.compile(r'^\s*#\s*openapi:')

_AppRunArgs: TypeAlias = dict[str, Any]
_OpenAPIRunArgs: TypeAlias = dict[str, Any]

logger: Final = logging.getLogger(__name__)
ignore_missing_output: Final = True

db_populated = False


class _StartupError(RuntimeError):
    """Raised when application fails to start."""


class _ImportsSpoiler(General, Element):
    """Imports toggle container node."""


class _ImportsSpoilerSummary(General, Element):
    """Imports toggle control node."""


class _GithubSourceLink(General, Element):
    """GitHub source link node."""


class _OpenAPIResultToggle(General, Element):
    """OpenAPI result collapse container node."""


class _OpenAPIResultToggleSummary(General, Element):
    """OpenAPI result collapse summary node."""


def _visit_imports_spoiler(
    self: HTML5Translator,
    node: _ImportsSpoiler,
) -> None:
    classes = ' '.join(['imports-spoiler', *node.get('classes', [])])
    imports_from_line = int(node.get('imports_from_line', 1))
    self.body.append(
        (
            f'<div class="{classes}" '
            f'data-imports-from-line="{imports_from_line}">\n'
        ),
    )


def _depart_imports_spoiler(
    self: HTML5Translator,
    node: _ImportsSpoiler,
) -> None:
    self.body.append('</div>\n')


def _visit_imports_spoiler_summary(
    self: HTML5Translator,
    node: _ImportsSpoilerSummary,
) -> None:
    collapsed_title = node.get('collapsed_title', 'Show imports')
    expanded_title = node.get('expanded_title', 'Hide imports')
    self.body.append(
        (
            '<button type="button" class="imports-spoiler-toggle" '
            f'data-collapsed-title="{collapsed_title}" '
            f'data-expanded-title="{expanded_title}">'
        ),
    )


def _depart_imports_spoiler_summary(
    self: HTML5Translator,
    node: _ImportsSpoilerSummary,
) -> None:
    self.body.append('</button>\n')


def _visit_github_source_link(
    self: HTML5Translator,
    node: _GithubSourceLink,
) -> None:
    github_url = node.get('github_url', '')
    self.body.append(
        f'<a href="{github_url}" class="github-source-link" '
        'target="_blank" rel="noopener noreferrer">[source]</a>\n',
    )


def _depart_github_source_link(
    self: HTML5Translator,
    node: _GithubSourceLink,
) -> None:
    self.body.append('')


def _visit_openapi_result_toggle(
    self: HTML5Translator,
    node: _OpenAPIResultToggle,
) -> None:
    self.body.append('<details class="openapi-result-toggle">\n')


def _depart_openapi_result_toggle(
    self: HTML5Translator,
    node: _OpenAPIResultToggle,
) -> None:
    self.body.append('</details>\n')


def _visit_openapi_result_toggle_summary(
    self: HTML5Translator,
    node: _OpenAPIResultToggleSummary,
) -> None:
    self.body.append('<summary class="openapi-result-summary">')


def _depart_openapi_result_toggle_summary(
    self: HTML5Translator,
    node: _OpenAPIResultToggleSummary,
) -> None:
    self.body.append('</summary>\n')


def _get_available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(('localhost', 0))
        except OSError as error:
            raise _StartupError('Could not find an open port') from error
        else:
            return cast(int, sock.getsockname()[1])


def _ensure_project_import_paths() -> None:
    """Ensure external examples can import project modules."""
    cwd = Path.cwd()
    project_root = cwd.parent if cwd.name == 'docs' else cwd
    for path_item in (project_root, project_root / 'django_test_app'):
        path_string = str(path_item)
        if path_item.exists() and path_string not in sys.path:
            sys.path.insert(0, path_string)


class _BaseBuilder:  # noqa: WPS214
    def __init__(self, file_path: Path, config: _AppRunArgs) -> None:
        """Initialize application builder with file path and configuration."""
        self.file_path = file_path
        self.config = config

    def build_app(self) -> ASGIHandler:
        """Build and return configured ASGI application."""
        self._configure_settings()
        app = self._build_app()
        self._populate_db()
        return app

    def _configure_settings(self) -> None:
        if settings.configured:
            return

        settings.configure(
            ROOT_URLCONF='url_conf',
            ALLOWED_HOSTS=['*'],
            DEBUG=False,
            SECRET_KEY='dummy-key-for-examples',  # noqa: S106
            INSTALLED_APPS=[
                'django.contrib.auth',
                'django.contrib.sessions',
                'django.contrib.contenttypes',
                'dmr',
                'dmr.security.jwt.blocklist',
            ],
            MIDDLEWARE=[
                'django.middleware.security.SecurityMiddleware',
                'django.contrib.sessions.middleware.SessionMiddleware',
                'django.middleware.common.CommonMiddleware',
                'django.middleware.csrf.CsrfViewMiddleware',
                'django.contrib.auth.middleware.AuthenticationMiddleware',
                'django.middleware.locale.LocaleMiddleware',
                'django.contrib.messages.middleware.MessageMiddleware',
                'django.middleware.clickjacking.XFrameOptionsMiddleware',
            ],
            USE_TZ=True,
            USE_I18N=True,
            LANGUAGE_CODE='en-us',
            LOCALE_PATHS=[str(_BASE_DIR / 'dmr' / 'locale')],
            LANGUAGES=(
                ('en', 'English'),
                ('ru', 'Russian'),
            ),
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': '_build/test.db',
                },
            },
            LOGGING_CONFIG=None,
            # Needed for HTTP Basic auth example:
            HTTP_BASIC_USERNAME='admin',
            HTTP_BASIC_PASSWORD='pass',  # noqa: S106
        )
        django.setup()

    def _populate_db(self) -> None:
        global db_populated  # noqa: PLW0603, WPS420
        if not self.config.get('populate_db') or db_populated:
            return

        from django.core.management.commands import migrate  # noqa: PLC0415

        migrate.Command().run_from_argv(['python', 'run_examples.py'])

        from django.contrib.auth.models import User  # noqa: PLC0415

        with suppress(IntegrityError):
            User.objects.create_user(
                'test_user',
                email='test@example.com',
                password='password',  # noqa: S106
            )

        db_populated = True

    def _build_app(self) -> ASGIHandler:
        _ensure_project_import_paths()

        file_path_without_ext = self.file_path.with_suffix('')
        module_name = str(file_path_without_ext).replace(os.sep, '.')

        sys.modules.pop(module_name, None)
        module = importlib.import_module(module_name)
        self._create_urlpatterns(module)

        return ASGIHandler()

    def _find_controller(self, module: ModuleType) -> View:
        controller_name = self.config.get('controller')
        if not controller_name:
            raise RuntimeError(
                'Controller option is required',
                self.file_path,
                self.config,
            )
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

    def _create_urlpatterns(self, module: ModuleType) -> None:
        url_conf_module = ModuleType('url_conf')
        url_conf_module.urlpatterns = self._generate_urls(module)  # type: ignore[attr-defined]
        url_conf_module.handler404 = build_404_handler(  # type: ignore[attr-defined]
            'api/',
            serializer=PydanticSerializer,
        )
        url_conf_module.handler500 = build_500_handler(  # type: ignore[attr-defined]
            'api/',
            serializer=PydanticSerializer,
        )
        sys.modules['url_conf'] = url_conf_module

    def _generate_urls(self, module: ModuleType) -> list[URLPattern]:
        clear_url_caches()

        if self.config.get('use_urlpatterns', False):
            return module.urlpatterns  # type: ignore[no-any-return]

        controller_cls = self._find_controller(module)
        url_path = _get_route_path_from_run_args(
            self.config,
        ).lstrip('/')  # noqa: WPS226
        return [
            path(url_path, controller_cls.as_view()),
        ]


class _AppBuilder(_BaseBuilder):
    """Builds a Django application from configuration."""


class _OpenAPIBuilder(_BaseBuilder):
    """Builds an OpenAPI application from configuration."""

    @override
    def _generate_urls(self, module: ModuleType) -> list[URLPattern]:
        from dmr.openapi import build_schema  # noqa: PLC0415
        from dmr.openapi.views import OpenAPIJsonView  # noqa: PLC0415
        from dmr.routing import Router  # noqa: PLC0415

        urlpatterns = super()._generate_urls(module)
        if self.config.get('use_urlpatterns', False):
            return urlpatterns

        controller_cls = self._find_controller(module)
        url_path = _get_route_path_from_run_args(
            self.config,
        ).lstrip('/')  # noqa: WPS226

        router = Router(
            '',
            [
                path(url_path, controller_cls.as_view()),
            ],
        )
        schema = build_schema(router)

        urlpatterns.append(
            path(
                self.config['openapi_url'].lstrip('/'),
                OpenAPIJsonView.as_view(schema),
            ),
        )
        return urlpatterns


def _get_url_path_from_run_args(run_args: _AppRunArgs) -> str:
    url = run_args.get('url')
    if url:
        assert isinstance(url, str)  # noqa: S101
        return url
    controller_name = run_args['controller'].lower()
    return f'/api/{controller_name}/'


def _get_route_path_from_run_args(run_args: _AppRunArgs) -> str:
    url_pattern = run_args.get('url_pattern')
    if url_pattern:
        assert isinstance(url_pattern, str)  # noqa: S101
        return url_pattern
    return _get_url_path_from_run_args(run_args)


@contextmanager
def _run_app(
    path: Path,
    config: _AppRunArgs,
    builder: type[_BaseBuilder],
) -> Iterator[int]:
    """Start a Django app on an available port."""
    restart_duration = 0.2
    port = _get_available_port()
    # Needed by autodoc imports in the parent process.
    builder(path, config)._configure_settings()  # noqa: SLF001
    attempts = 0
    while attempts < 100:
        proc = _MP_CONTEXT.Process(
            target=_run_app_worker,
            args=(path, config, builder, port),
        )
        proc.start()

        try:
            _wait_for_app_startup(port, proc)
        except _StartupError:
            _shutdown_process(proc)
            time.sleep(restart_duration)
            attempts += 1
            port = _get_available_port()
            continue

        try:
            yield port
        finally:
            _shutdown_process(proc)
        return
    raise _StartupError(str(path))


def _run_app_worker(
    path: Path,
    config: _AppRunArgs,
    builder: type[_BaseBuilder],
    port: int,
) -> None:
    app = builder(path, config).build_app()
    with redirect_stderr(Path(os.devnull).open(encoding='utf-8')):
        uvicorn.run(app, port=port, access_log=False)


def _shutdown_process(proc: multiprocessing.Process) -> None:
    if proc.is_alive():
        proc.terminate()
        proc.join(timeout=1.0)
    if proc.is_alive():
        proc.kill()
        proc.join(timeout=1.0)
    else:
        proc.join(timeout=0)


def _get_module_name(file_path: Path) -> str:
    return str(file_path.with_suffix('')).replace(os.sep, '.')


def _resolve_tmp_example_relative_path(
    file_path: Path,
    docs_dir: Path,
) -> Path:
    """Return a stable relative path for temp examples inside docs/_build."""
    if file_path.is_relative_to(docs_dir):
        return file_path.relative_to(docs_dir)

    project_root = docs_dir.parent
    if file_path.is_relative_to(project_root):
        return Path('_external') / file_path.relative_to(project_root)

    return Path('_external') / file_path.name


def _resolve_example_file_for_execution(file_path: Path) -> Path:
    """Resolve example path for importing regardless of current cwd."""
    cwd = Path.cwd()
    if file_path.is_relative_to(cwd):
        return file_path.relative_to(cwd)

    project_root = cwd.parent if cwd.name == 'docs' else cwd
    if file_path.is_relative_to(project_root):
        return file_path.relative_to(project_root)

    return file_path


def _wait_for_app_startup(port: int, proc: multiprocessing.Process) -> None:
    """Wait for app to start up and become responsive."""
    for _ in range(100):
        if proc.exitcode is not None:
            raise _StartupError(
                f'App worker exited during startup with {proc.exitcode}',
            )
        try:
            httpx.get(f'http://127.0.0.1:{port}', timeout=0.1)
        except httpx.TransportError:
            time.sleep(0.1)
        else:
            return
    raise _StartupError(f'App failed to come online on port {port}')


def _extract_run_args(
    file_content: str,
) -> tuple[str, list[_AppRunArgs], list[_OpenAPIRunArgs]]:
    """Extract run args from a python file.

    Return the file content stripped of the run comments
    and a list of argument lists.
    """
    new_lines, run_configs, openapi_configs = _split_example_lines(
        file_content.splitlines(),
    )
    return '\n'.join(new_lines), run_configs, openapi_configs


def _split_example_lines(
    lines: list[str],
) -> tuple[list[str], list[_AppRunArgs], list[_OpenAPIRunArgs]]:
    new_lines: list[str] = []
    run_configs: list[_AppRunArgs] = []
    openapi_configs: list[_OpenAPIRunArgs] = []
    for line in lines:
        config = _extract_comment_config(line, _RGX_RUN)
        if config is not None:
            run_configs.append(config)
            continue
        config = _extract_comment_config(line, _RGX_OPENAPI)
        if config is not None:
            openapi_configs.append(config)
            continue

        new_lines.append(line)
    return new_lines, run_configs, openapi_configs


def _extract_comment_config(
    line: str,
    pattern: re.Pattern[str],
) -> dict[str, Any] | None:
    match = pattern.match(line)
    if match is None:
        return None

    run_stmt = match.group(1).lstrip()
    if '# noqa' in run_stmt:
        run_stmt = run_stmt.split('# noqa')[0]
    return cast(dict[str, Any], json.loads(run_stmt))


def _exec_examples(app_file: Path, run_configs: list[_AppRunArgs]) -> str:
    """
    Start a server with the example application, run the specified requests.

    Run requests against it and return their results.
    """
    example_results = []

    for run_args in run_configs:
        url_path = _get_url_path_from_run_args(run_args)
        with _run_app(app_file, run_args, _AppBuilder) as port:
            clear_settings_cache()
            example_result = _process_single_example(
                app_file,
                run_args,
                port,
                url_path,
            )
            if example_result:
                example_results.append(example_result)

    return '\n\n'.join(example_results)


def _exec_openapi_examples(
    app_file: Path,
    openapi_configs: list[_OpenAPIRunArgs],
) -> str:
    openapi_results = []

    for openapi_args in openapi_configs:
        url_path = cast(str, openapi_args['openapi_url'])
        with (
            override_settings(
                DMR_SETTINGS={
                    Settings.openapi_examples_seed: openapi_args.get(
                        'openapi_examples_seed',
                    ),
                },
            ),
            _run_app(app_file, openapi_args, _OpenAPIBuilder) as port,
        ):
            clear_settings_cache()
            openapi_results.append(
                _process_openapi_example(port, url_path, app_file),
            )

    return '\n\n'.join(openapi_results)


def _process_single_example(
    app_file: Path,
    run_args: _AppRunArgs,
    port: int,
    url_path: str,
) -> str:
    """Process a single example configuration."""
    args, clean_args = _build_curl_request(app_file, run_args, port, url_path)

    proc = subprocess.run(  # noqa: PLW1510, S603
        args,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise _StartupError(
            (
                (
                    f'Could not run example in {app_file}, '
                    f'got {proc.returncode} error code'
                ),
                args,
                proc.stdout,
                proc.stderr,
            ),
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

    clean_args_string = shlex.join(clean_args)
    return '\n'.join((f'$ {clean_args_string}', *stdout))


def _process_openapi_example(port: int, url_path: str, app_file: Path) -> str:
    args = [
        'curl',
        '-v',
        '-sS',
        '--fail-with-body',
        f'http://127.0.0.1:{port}{url_path}',
    ]
    proc = subprocess.run(  # noqa: PLW1510, S603
        args,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise _StartupError(
            (
                f'Could not fetch OpenAPI schema in {app_file}',
                args,
                proc.stdout,
                proc.stderr,
            ),
        )
    return json.dumps(json.loads(proc.stdout), indent=2, sort_keys=True)


def _create_openapi_admonition(result_content: str) -> Node:
    result_toggle = _OpenAPIResultToggle()
    result_summary = _OpenAPIResultToggleSummary()
    result_summary += Text('Preview openapi.json')
    result_toggle += result_summary
    result_toggle += highlightlang(
        '',
        literal_block('', result_content),
        lang='json',
        force=False,
        linenothreshold=sys.maxsize,
    )
    result_toggle += literal_block('', result_content)
    return admonition(
        '',
        title('', 'OpenAPI Schema'),
        result_toggle,
        classes=['hint'],
    )


_CurlArgs: TypeAlias = list[str]
_CurlCleanArgs: TypeAlias = list[str]


def _build_curl_request(
    app_file: Path,
    run_args: _AppRunArgs,
    port: int,
    url_path: str,
) -> tuple[_CurlArgs, _CurlCleanArgs]:
    query = run_args.pop('query', '')
    if query and not query.startswith('?'):
        raise ValueError(f'{query!r} must start with "?"')
    args = [
        'curl',
        '-v',
        '-sS',
        f'http://127.0.0.1:{port}{url_path}{query}',
    ]
    if run_args.pop('fail-with-body', True):
        args.append('--fail-with-body')

    clean_args = ['curl', f'http://127.0.0.1:8000{url_path}{query}']

    _add_curl_flags(args, clean_args, run_args)
    _add_method(args, clean_args, run_args)
    _add_body_and_content_type(app_file, args, clean_args, run_args)
    _add_headers(args, clean_args, run_args)
    _add_cookies(args, clean_args, run_args)

    return args, clean_args


def _add_curl_flags(
    args: list[str],
    clean_args: list[str],
    run_args: _AppRunArgs,
) -> None:
    curl_extra_args = run_args.get('curl_args', [])
    args.extend(curl_extra_args)
    clean_args.extend(curl_extra_args)


def _add_method(
    args: list[str],
    clean_args: list[str],
    run_args: _AppRunArgs,
) -> None:
    method = run_args.get('method', 'get').upper()
    args.extend(['-X', method])
    clean_args.extend(['-X', method])


def _add_body_and_content_type(  # noqa: C901, WPS210, WPS213, WPS231
    app_file: Path,
    args: list[str],
    clean_args: list[str],
    run_args: _AppRunArgs,
) -> None:
    if 'body' not in run_args:
        return

    content_type = run_args.get('headers', {}).get(
        'Content-Type',
        None,
    )
    if content_type == 'application/json' or content_type is None:  # noqa: WPS223
        body_data = json.dumps(run_args['body'])
        args.extend(['-d', body_data])
        clean_args.extend(['-d', body_data])
    elif content_type == 'application/xml':
        body_data = xmltodict.unparse(
            {'request': run_args['body']},
            full_document=False,
        )
        args.extend(['-d', body_data])
        clean_args.extend(['-d', body_data])
    elif content_type == 'application/x-www-form-urlencoded':
        body_data = urlencode(run_args['body'])
        args.extend(['-d', body_data])
        clean_args.extend(['-d', body_data])
    elif content_type == 'multipart/form-data':
        for body_key, body_value in run_args.get('body', {}).items():
            if isinstance(body_value, list):
                body_args = []
                for body_subvalue in body_value:
                    body_args.extend(['-F', f'{body_key}={body_subvalue}'])
            else:
                body_args = ['-F', f'{body_key}={body_value}']
            args.extend(body_args)
            clean_args.extend(body_args)
        for body_key, body_value in run_args.get('files', {}).items():
            clean_args.extend(['-F', f'{body_key}=@{body_value}'])
            body_value = str(app_file.parent / body_value)
            args.extend(['-F', f'{body_key}=@{body_value}'])
    elif content_type == 'application/msgpack':
        source = run_args['body']
        args.extend(['--data-binary', f'@{source}'])
        clean_args.extend(['--data-binary', f'@{source}'])
    else:
        raise RuntimeError(f'{content_type} is not supported')

    if content_type is None:
        args.extend(['-H', 'Content-Type: application/json'])
        clean_args.extend(['-H', 'Content-Type: application/json'])


def _add_headers(
    args: list[str],
    clean_args: list[str],
    run_args: _AppRunArgs,
) -> None:
    header_flag = '-H'

    headers = run_args.get('headers', {})
    if isinstance(headers, dict):
        headers = headers.items()
    for header_name, header_value in headers:
        args.extend([header_flag, f'{header_name}: {header_value}'])
        clean_args.extend([header_flag, f'{header_name}: {header_value}'])


def _add_cookies(
    args: list[str],
    clean_args: list[str],
    run_args: _AppRunArgs,
) -> None:
    cookie_flag = '--cookie'

    cookies = run_args.get('cookies', {})
    for cookie_name, cookie_value in cookies.items():
        args.extend([cookie_flag, f'{cookie_name}={cookie_value}'])
        clean_args.extend([cookie_flag, f'{cookie_name}={cookie_value}'])


def _find_imports_block_end_line(file_content: str) -> int:
    try:
        parsed = ast.parse(file_content)
    except SyntaxError:
        return 0

    statements = parsed.body
    start_index = 0
    if (
        statements
        and isinstance(statements[0], ast.Expr)
        and isinstance(statements[0].value, ast.Constant)
        and isinstance(statements[0].value.value, str)
    ):
        start_index = 1

    last_import_line = 0
    for statement in statements[start_index:]:
        if not isinstance(statement, (ast.Import, ast.ImportFrom)):
            break
        last_import_line = max(
            last_import_line,
            statement.end_lineno or statement.lineno,
        )
    return last_import_line


def _extend_with_trailing_blank_lines(
    source_lines: list[str],
    last_import_line: int,
) -> int:
    hidden_until_line = last_import_line
    while (
        hidden_until_line < len(source_lines)
        and not source_lines[hidden_until_line].strip()
    ):
        hidden_until_line += 1
    return hidden_until_line


class LiteralInclude(_LiteralInclude):  # noqa: WPS214
    """Extended `.. literalinclude` directive with code execution capability."""

    option_spec: ClassVar = {
        **_LiteralInclude.option_spec,
        'no-run': directives.flag,
        'imports-spoiler-title': directives.unchanged,
        'no-imports-spoiler': directives.flag,
    }

    @override
    def run(self) -> list[Node]:  # noqa: WPS210
        """Execute code examples and display results."""
        file_path = Path(self.env.relfn2path(self.arguments[0])[1])
        imports_data = self._get_imports_data(file_path)
        if not self._need_to_run(file_path):
            return self._generate_nodes(file_path, imports_data)

        clean_content, run_args, openapi_args = self._execute_code(file_path)
        if not run_args and not openapi_args:
            return self._generate_nodes(file_path, imports_data)
        self._create_tmp_example_file(file_path, clean_content)

        nodes = self._generate_nodes(file_path, imports_data)

        example_file = _resolve_example_file_for_execution(file_path)
        executed_result = _exec_examples(example_file, run_args)
        openapi_result = _exec_openapi_examples(example_file, openapi_args)

        if executed_result:
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
        if openapi_result:
            nodes.append(_create_openapi_admonition(openapi_result))
        return nodes

    def _generate_nodes(
        self,
        file_path: Path,
        imports_data: tuple[_ImportsSpoiler, int] | None,
    ) -> list[Node]:
        nodes = self._render_literalinclude_nodes(imports_data)
        nodes = self._inject_imports_spoiler(nodes, imports_data)
        return self._inject_source_link(nodes, file_path)

    def _get_imports_data(
        self,
        file_path: Path,
    ) -> tuple[_ImportsSpoiler, int] | None:
        if 'no-imports-spoiler' in self.options:
            return None

        hidden_lines, start_line = self._extract_hidden_lines(file_path)
        if not hidden_lines:
            return None

        return (
            self._create_imports_spoiler_node(hidden_lines, start_line),
            start_line,
        )

    def _render_literalinclude_nodes(
        self,
        imports_data: tuple[_ImportsSpoiler, int] | None,
    ) -> list[Node]:
        original_lines = self.options.get('lines')
        should_expand_literalinclude = (
            imports_data is not None and original_lines is not None
        )
        if should_expand_literalinclude:
            self.options.pop('lines', None)
            rendered_nodes = _LiteralInclude.run(self)
            if original_lines is not None:
                self.options['lines'] = original_lines
            return rendered_nodes
        return _LiteralInclude.run(self)

    def _inject_imports_spoiler(
        self,
        rendered_nodes: list[Node],
        imports_data: tuple[_ImportsSpoiler, int] | None,
    ) -> list[Node]:
        if imports_data is None or not rendered_nodes:
            return rendered_nodes

        spoiler_node, _ = imports_data
        first_node = rendered_nodes[0]

        if self._is_literal_block_wrapper(first_node):
            wrapper_node = cast(container, first_node)
            self._add_wrapper_class(wrapper_node, 'imports-inline-enabled')
            self._insert_spoiler_before_literal_block(
                wrapper_node,
                spoiler_node,
            )
            return rendered_nodes

        if isinstance(first_node, literal_block):
            wrapper = container(
                '',
                literal_block=True,
                classes=['literal-block-wrapper', 'imports-inline-enabled'],
            )
            wrapper += spoiler_node
            wrapper += first_node
            rendered_nodes[0] = wrapper
            return rendered_nodes

        rendered_nodes.insert(0, spoiler_node)
        return rendered_nodes

    def _insert_spoiler_before_literal_block(
        self,
        wrapper: container,
        spoiler_node: _ImportsSpoiler,
    ) -> None:
        for index, child in enumerate(wrapper.children):
            if isinstance(child, literal_block):
                wrapper.insert(index, spoiler_node)
                return
        wrapper += spoiler_node

    def _extract_hidden_lines(self, file_path: Path) -> tuple[list[str], int]:
        file_content = file_path.read_text(encoding='utf-8')
        source_lines = file_content.splitlines()
        last_import_line = _find_imports_block_end_line(file_content)
        if last_import_line <= 0:
            return [], 1

        hidden_until_line = _extend_with_trailing_blank_lines(
            source_lines,
            last_import_line,
        )
        hidden_lines = source_lines[:hidden_until_line]

        hidden_lines = [
            line
            for line in hidden_lines
            if (
                not _RGX_RUN_COMMENT.match(line)
                and not _RGX_OPENAPI_COMMENT.match(line)
            )
        ]

        return hidden_lines, hidden_until_line + 1

    def _create_imports_spoiler_node(
        self,
        hidden_lines: list[str],
        start_line: int,
    ) -> _ImportsSpoiler:
        node = _ImportsSpoiler(classes=['imports-inline-spoiler'])
        node['imports_from_line'] = start_line
        summary_text = self._get_imports_summary_text(hidden_lines)
        summary_node = _ImportsSpoilerSummary()
        summary_node['collapsed_title'] = summary_text
        summary_node['expanded_title'] = 'Hide imports'
        summary_node += Text(summary_text)
        node += summary_node
        return node

    def _get_imports_summary_text(self, hidden_lines: list[str]) -> str:
        custom_title = self.options.get('imports-spoiler-title')
        if isinstance(custom_title, str):
            return custom_title

        hidden_lines_count = len(hidden_lines)
        lines_word = 'line' if hidden_lines_count == 1 else 'lines'
        return f'Show imports... {hidden_lines_count} {lines_word} hidden'

    def _build_github_url(self, file_path: Path) -> str:
        """Build GitHub URL for the source file."""
        docs_dir = self._get_docs_dir()
        relative_path = self._get_source_relative_path(file_path, docs_dir)
        return f'{self._get_source_base_url()}/{relative_path.as_posix()}'

    def _get_docs_dir(self) -> Path:
        cwd = Path.cwd()
        return cwd if cwd.name == 'docs' else cwd / 'docs'

    def _get_source_relative_path(
        self,
        file_path: Path,
        docs_dir: Path,
    ) -> Path:
        if file_path.is_relative_to(docs_dir):
            return Path('docs') / file_path.relative_to(docs_dir)
        return file_path

    def _get_source_base_url(self) -> str:
        html_context = self.env.app.config.html_context
        source_user = html_context.get('source_user', 'wemake-services')
        source_repo = html_context.get('source_repo', 'django-modern-rest')
        source_version = html_context.get('source_version', 'master')
        return (
            f'https://github.com/{source_user}/{source_repo}/'
            f'blob/{source_version}'
        )

    def _inject_source_link(
        self,
        rendered_nodes: list[Node],
        file_path: Path,
    ) -> list[Node]:
        """Inject GitHub source link into rendered nodes."""
        if not rendered_nodes:
            return rendered_nodes

        github_url = self._build_github_url(file_path)
        github_link_node = _GithubSourceLink()
        github_link_node['github_url'] = github_url

        first_node = rendered_nodes[0]
        if self._is_literal_block_wrapper(first_node):
            wrapper_node = cast(container, first_node)
            self._add_wrapper_class(wrapper_node, 'github-link-enabled')
            self._insert_source_link(
                wrapper_node,
                github_link_node,
            )
            return rendered_nodes

        if isinstance(first_node, literal_block):
            wrapper = container(
                '',
                literal_block=True,
                classes=['literal-block-wrapper', 'github-link-enabled'],
            )
            self._insert_source_link(wrapper, github_link_node)
            wrapper += first_node
            rendered_nodes[0] = wrapper
            return rendered_nodes

        rendered_nodes.insert(0, github_link_node)
        return rendered_nodes

    def _is_literal_block_wrapper(self, node: Node) -> bool:
        return isinstance(node, container) and (
            'literal-block-wrapper' in node.get('classes', [])
        )

    def _add_wrapper_class(self, wrapper: container, class_name: str) -> None:
        if class_name not in wrapper['classes']:
            wrapper['classes'].append(class_name)

    def _insert_source_link(
        self,
        wrapper: container,
        github_link_node: _GithubSourceLink,
    ) -> None:
        for index, child in enumerate(wrapper.children):
            if isinstance(child, literal_block):
                wrapper.insert(index, github_link_node)
                return
        wrapper.insert(0, github_link_node)

    def _need_to_run(self, file_path: Path) -> bool:
        language = self.options.get('language', '')
        no_run_in_options = 'no-run' in self.options
        not_python_file = language != 'python' and file_path.suffix != '.py'
        return not (not_python_file or no_run_in_options)

    def _execute_code(
        self,
        file_path: Path,
    ) -> tuple[str, list[_AppRunArgs], list[_OpenAPIRunArgs]]:
        file_content = file_path.read_text(encoding='utf-8')
        return _extract_run_args(file_content)

    def _create_tmp_example_file(
        self,
        file_path: Path,
        clean_content: str,
    ) -> None:
        cwd = Path.cwd()
        docs_dir = cwd if cwd.name == 'docs' else cwd / 'docs'
        relative_example_path = _resolve_tmp_example_relative_path(
            file_path,
            docs_dir,
        )
        tmp_file = (
            docs_dir
            / _PATH_TO_TMP_EXAMPLES
            / str(relative_example_path).replace('/', '_')
        )

        self.arguments[0] = f'/{tmp_file.relative_to(docs_dir)!s}'
        tmp_file.write_text(clean_content)


def setup(app: Sphinx) -> None:
    """Register Sphinx extension directives."""
    tmp_examples_path = Path.cwd() / _PATH_TO_TMP_EXAMPLES
    tmp_examples_path.mkdir(exist_ok=True, parents=True)
    app.add_node(
        _ImportsSpoiler,
        html=(_visit_imports_spoiler, _depart_imports_spoiler),
    )
    app.add_node(
        _ImportsSpoilerSummary,
        html=(
            _visit_imports_spoiler_summary,
            _depart_imports_spoiler_summary,
        ),
    )
    app.add_node(
        _GithubSourceLink,
        html=(_visit_github_source_link, _depart_github_source_link),
    )
    app.add_node(
        _OpenAPIResultToggle,
        html=(_visit_openapi_result_toggle, _depart_openapi_result_toggle),
    )
    app.add_node(
        _OpenAPIResultToggleSummary,
        html=(
            _visit_openapi_result_toggle_summary,
            _depart_openapi_result_toggle_summary,
        ),
    )
    app.add_css_file('css/literalinclude-imports.css')
    app.add_js_file('js/literalinclude-imports.js')

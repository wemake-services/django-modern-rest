"""
This file contains code adapted from Litestar.

See:
https://github.com/litestar-org/litestar/blob/main/tools/sphinx_ext/run_examples.py
"""

from __future__ import annotations

import ast
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
from typing import TYPE_CHECKING, Any, ClassVar, Final, TypeAlias, cast, final
from urllib.parse import urlencode

import httpx
import uvicorn
import xmltodict
from django.conf import settings
from django.core.handlers.asgi import ASGIHandler
from django.urls import path
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

if TYPE_CHECKING:
    from sphinx.writers.html5 import HTML5Translator

if platform.system() in {'Darwin', 'Linux'}:
    multiprocessing.set_start_method('fork', force=True)

_PATH_TO_TMP_EXAMPLES: Final = '_build/_tmp_example/'
_RGX_RUN: Final = re.compile(r'# +?run:(.*)')
_RGX_RUN_COMMENT: Final = re.compile(r'^\s*#\s*run:')

_AppRunArgs: TypeAlias = dict[str, Any]

logger: Final = logging.getLogger(__name__)
ignore_missing_output: Final = True


@final
class _StartupError(RuntimeError):
    """Raised when application fails to start."""


@final
class _ImportsSpoiler(General, Element):
    """Imports toggle container node."""


@final
class _ImportsSpoilerSummary(General, Element):
    """Imports toggle control node."""


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
    self.body.append(
        (
            '<button type="button" class="imports-spoiler-toggle" '
            f'data-collapsed-title="{collapsed_title}" '
            'data-expanded-title="Hide imports">'
        ),
    )


def _depart_imports_spoiler_summary(
    self: HTML5Translator,
    node: _ImportsSpoilerSummary,
) -> None:
    self.body.append('</button>\n')


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

    def __init__(self, file_path: Path, config: _AppRunArgs) -> None:
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
            # Needed for HTTP Basic auth example:
            HTTP_BASIC_USERNAME='admin',
            HTTP_BASIC_PASSWORD='pass',  # noqa: S106
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


def _get_url_path_from_run_args(run_args: _AppRunArgs) -> str:
    controller_name = run_args['controller'].lower()
    url: str = run_args.get(
        'url',
        f'/api/{controller_name}/',
    )
    return url


@contextmanager
def _run_app(path: Path, config: _AppRunArgs) -> Iterator[int]:
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


def _extract_run_args(file_content: str) -> tuple[str, list[_AppRunArgs]]:
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


def _exec_examples(app_file: Path, run_configs: list[_AppRunArgs]) -> str:
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


_CurlArgs: TypeAlias = list[str]
_CurlCleanArgs: TypeAlias = list[str]


def _build_curl_request(
    app_file: Path,
    run_args: _AppRunArgs,
    port: int,
    url_path: str,
) -> tuple[_CurlArgs, _CurlCleanArgs]:
    query = run_args.pop('query', '')
    args = [
        'curl',
        '-v',
        '-s',
        f'http://127.0.0.1:{port}{url_path}{query}',
    ]
    if run_args.pop('fail-with-body', True):
        args.append('--fail-with-body')

    clean_args = ['curl', f'http://127.0.0.1:8000{url_path}{query}']

    _add_curl_flags(args, clean_args, run_args)
    _add_method(args, clean_args, run_args)
    _add_body_and_content_type(app_file, args, clean_args, run_args)
    _add_headers(args, clean_args, run_args)

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


def _add_body_and_content_type(  # noqa: C901, WPS213, WPS231
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
    if content_type == 'application/json' or content_type is None:
        body_data = json.dumps(run_args['body'])
        args.extend(['-d', body_data])
        clean_args.extend(['-d', body_data])
    elif content_type == 'application/xml':
        body_data = xmltodict.unparse(run_args['body'], full_document=False)
        args.extend(['-d', body_data])
        clean_args.extend(['-d', body_data])
    elif content_type == 'application/x-www-form-urlencoded':
        body_data = urlencode(run_args['body'])
        args.extend(['-d', body_data])
        clean_args.extend(['-d', body_data])
    elif content_type == 'multipart/form-data':
        for body_key, body_value in run_args.get('body', {}).items():
            body_args = ['-F', f'{body_key}={body_value}']
            args.extend(body_args)
            clean_args.extend(body_args)
        for body_key, body_value in run_args.get('files', {}).items():
            clean_args.extend(['-F', f'{body_key}=@{body_value}'])
            body_value = str(app_file.parent / body_value)  # noqa: PLW2901
            args.extend(['-F', f'{body_key}=@{body_value}'])
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
    for header_name, header_value in run_args.get('headers', {}).items():
        args.extend([header_flag, f'{header_name}: {header_value}'])
        clean_args.extend([header_flag, f'{header_name}: {header_value}'])


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


@final
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
            rendered_nodes = self._render_literalinclude_nodes(imports_data)
            return self._inject_imports_spoiler(rendered_nodes, imports_data)

        clean_content, run_args = self._execute_code(file_path)
        if not run_args:
            rendered_nodes = self._render_literalinclude_nodes(imports_data)
            return self._inject_imports_spoiler(rendered_nodes, imports_data)
        self._create_tmp_example_file(file_path, clean_content)

        rendered_nodes = self._render_literalinclude_nodes(imports_data)
        nodes = self._inject_imports_spoiler(rendered_nodes, imports_data)

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

        if isinstance(
            first_node,
            container,
        ) and 'literal-block-wrapper' in first_node.get('classes', []):
            if 'imports-inline-enabled' not in first_node['classes']:
                first_node['classes'].append('imports-inline-enabled')
            self._insert_spoiler_before_literal_block(first_node, spoiler_node)
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
            line for line in hidden_lines if not _RGX_RUN_COMMENT.match(line)
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

    def _need_to_run(self, file_path: Path) -> bool:
        language = self.options.get('language', '')
        no_run_in_options = 'no-run' in self.options
        not_python_file = language != 'python' and file_path.suffix != '.py'
        return not (not_python_file or no_run_in_options)

    def _execute_code(
        self,
        file_path: Path,
    ) -> tuple[str, list[_AppRunArgs]]:
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
            docs_dir
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
    app.add_css_file('css/literalinclude-imports.css')
    app.add_js_file('js/literalinclude-imports.js')

from __future__ import annotations

import ast
import importlib
import inspect
import re
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

from docutils.utils import get_source_line

if TYPE_CHECKING:
    from collections.abc import Generator
    from typing import Any, TypeAlias

    from docutils.nodes import Element, Node
    from sphinx.addnodes import pending_xref
    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment


IgnoreRefs: TypeAlias = dict[
    str | re.Pattern[str],
    set[str] | re.Pattern[str],
]


@cache
def _get_module_ast(source_file: str) -> ast.AST | ast.Module:
    return ast.parse(Path(source_file).read_text(encoding='utf-8'))


def _get_import_nodes(
    nodes: list[ast.stmt],
) -> Generator[ast.Import | ast.ImportFrom, None, None]:
    for node in nodes:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            yield node
        elif (
            isinstance(node, ast.If)
            and getattr(node.test, 'id', None) == 'TYPE_CHECKING'
        ):
            yield from _get_import_nodes(node.body)


@cache
def get_module_global_imports(
    module_import_path: str,
    reference_target_source_obj: str,
) -> set[str]:
    """
    Return a set of names imported globally within the containing module.

    Includes imports in ``if TYPE_CHECKING`` blocks.
    """
    module = importlib.import_module(module_import_path)
    module_obj = getattr(module, reference_target_source_obj)

    try:
        tree = _get_module_ast(inspect.getsourcefile(module_obj))
    except TypeError:
        return set()

    import_nodes = _get_import_nodes(tree.body)  # type: ignore[attr-defined]
    return {
        path.asname or path.name
        for import_node in import_nodes
        for path in import_node.names
    }


def on_warn_missing_reference(
    app: Sphinx,
    domain: str,
    node: Node,
) -> bool | None:
    """Suppress specific missing reference warnings based on configuration."""
    if not _is_relevant_xref_node(node):
        return None

    ignore_refs: IgnoreRefs = app.config['ignore_missing_refs']

    attributes = node.attributes  # type: ignore[attr-defined]
    target = attributes['reftarget']

    if _is_valid_python_reference(attributes, target):
        return True

    if _is_ignored_reference(node, target, ignore_refs):
        return True

    return None


def _is_relevant_xref_node(node: Node) -> bool:
    """Check if node is a pending_xref with attributes."""
    if node.tagname != 'pending_xref':  # type: ignore[attr-defined]
        return False
    return hasattr(node, 'attributes')


def _is_valid_python_reference(attributes: dict[str, Any], target: str) -> bool:
    """Check if reference targets a valid Python global import."""
    reference_target_source_obj = attributes.get(
        'py:class',
        attributes.get('py:meth', attributes.get('py:func')),
    )

    if not reference_target_source_obj:
        return False

    global_names = get_module_global_imports(
        attributes['py:module'],
        reference_target_source_obj,
    )

    return target in global_names


def _is_ignored_reference(
    node: Node,
    target: str,
    ignore_refs: IgnoreRefs,
) -> bool:
    """Check if reference matches any ignore patterns."""
    source_line = get_source_line(node)[0]
    source = source_line.split(' ')[-1]

    if target in ignore_refs.get(source, []):  # type: ignore[operator]
        return True

    return _matches_pattern_ignore(source, target, ignore_refs)


def _matches_pattern_ignore(
    source: str,
    target: str,
    ignore_refs: IgnoreRefs,
) -> bool:
    """Check if source/target matches any regex patterns in ignore_refs."""
    pattern_ignore_refs = {
        pattern: targets
        for pattern, targets in ignore_refs.items()
        if isinstance(pattern, re.Pattern)
    }

    for pattern, targets in pattern_ignore_refs.items():
        if not pattern.match(source):
            continue

        if _target_matches_pattern_targets(target, targets):
            return True

    return False


def _target_matches_pattern_targets(
    target: str,
    targets: set[str] | re.Pattern[str],
) -> bool:
    """Check if target matches the pattern targets."""
    if isinstance(targets, set):
        return target in targets
    return targets.match(target) is not None


def on_missing_reference(
    app: Sphinx,
    env: BuildEnvironment,
    node: pending_xref,
    contnode: Element,
) -> Any:
    """Handle missing references by trying Python domain resolution."""
    if not hasattr(node, 'attributes'):
        return None

    target = node.attributes['reftarget']
    py_domain = env.domains['py']

    # autodoc sometimes incorrectly resolves these types, so we try to resolve
    # them as py:data fist and fall back to any
    new_node = py_domain.resolve_xref(
        env,
        node['refdoc'],
        app.builder,
        'data',
        target,
        node,
        contnode,
    )
    if new_node is None:
        resolved_xrefs = py_domain.resolve_any_xref(
            env,
            node['refdoc'],
            app.builder,
            target,
            node,
            contnode,
        )
        for ref in resolved_xrefs:
            if ref:
                return ref[1]
    return new_node


def on_env_before_read_docs(
    app: Sphinx,
    env: BuildEnvironment,
    docnames: set[str],
) -> None:
    """Create temporary directory for examples before reading docs."""
    tmp_examples_path = Path.cwd() / 'docs/_build/_tmp_examples'
    tmp_examples_path.mkdir(exist_ok=True, parents=True)
    env.tmp_examples_path = tmp_examples_path


def setup(app: Sphinx) -> dict[str, bool]:
    """Configure Sphinx extension events and settings."""
    app.connect('env-before-read-docs', on_env_before_read_docs)
    app.connect('missing-reference', on_missing_reference)
    app.connect('warn-missing-reference', on_warn_missing_reference)
    app.add_config_value('ignore_missing_refs', default={}, rebuild='')

    return {'parallel_read_safe': True, 'parallel_write_safe': True}

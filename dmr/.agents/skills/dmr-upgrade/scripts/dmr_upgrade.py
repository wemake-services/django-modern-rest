#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["libcst>=1.9,<2", "typing-extensions>=4.12"]
# ///
"""
Codemods for upgrading a project to a newer ``django-modern-rest`` release.

The mechanical parts of every breaking release are described
in ``references/renames.json`` next to this script:

- ``symbols`` are fully qualified renames, rewritten with ``libcst``
  (imports and usages),
- ``keywords`` are keyword arguments renamed on calls to a given callee,
- ``removed`` and ``manual`` are reported with file locations,
  they need a human or an agent to decide what to do.

Usage (from the root of the project that is being upgraded)::

    uv run --with libcst python dmr_upgrade.py --target 0.16.0 .
    uv run --with libcst python dmr_upgrade.py --target 0.16.0 --dry-run src/

Or standalone, ``uv`` installs the dependencies from the inline metadata::

    uv run dmr_upgrade.py --current 0.14.0 --target 0.16.0 .

``--current`` defaults to the installed ``django-modern-rest`` version.
Pass it explicitly when the script runs outside of the project environment,
and after the dependency was already bumped: the installed version is
the target one by then, so nothing would be selected.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterator, Sequence
from importlib import metadata
from pathlib import Path
from typing import Final

import libcst as cst
from libcst.codemod import CodemodContext
from libcst.codemod.commands.rename import RenameCommand
from typing_extensions import TypedDict, override

_RENAMES_FILE: Final = (
    Path(__file__).resolve().parent.parent / 'references' / 'renames.json'
)
_SKIP_DIRS: Final = frozenset((
    '.git',
    '.venv',
    'venv',
    'node_modules',
    '__pycache__',
    '.mypy_cache',
    'site-packages',
))


class SymbolRename(TypedDict):
    """Fully qualified symbol rename, applied with ``libcst``."""

    old: str
    new: str


class KeywordRename(TypedDict):
    """Keyword argument rename on calls to ``callee``."""

    callee: str
    old: str
    new: str


class ManualCheck(TypedDict):
    """Regex that flags code which needs a human decision."""

    pattern: str
    message: str


class Release(TypedDict):
    """One breaking release from ``renames.json``."""

    to: str
    prompt: str
    symbols: list[SymbolRename]
    keywords: list[KeywordRename]
    removed: list[str]
    manual: list[ManualCheck]


def parse_version(text: str) -> tuple[int, ...]:
    """Convert ``'0.16'`` or ``'0.16.0rc1'`` into a comparable tuple."""
    numbers = re.findall(r'\d+', text.split('+', maxsplit=1)[0])[:3]
    return tuple(int(part) for part in numbers + ['0'] * (3 - len(numbers)))


def detect_current_version() -> str | None:
    """Return the installed ``django-modern-rest`` version, if any."""
    try:
        return metadata.version('django-modern-rest')
    except metadata.PackageNotFoundError:
        return None


def load_releases() -> list[Release]:
    """Read the codemod table shipped next to this script."""
    with _RENAMES_FILE.open(encoding='utf-8') as renames_file:
        releases: list[Release] = json.load(renames_file)['releases']
    return releases


def select_releases(
    releases: Sequence[Release],
    current: str,
    target: str,
) -> list[Release]:
    """Keep releases that lie in ``(current, target]``, oldest first."""
    low = parse_version(current)
    high = parse_version(target)
    selected = [
        release
        for release in releases
        if low < parse_version(release['to']) <= high
    ]
    return sorted(selected, key=lambda release: parse_version(release['to']))


def iter_python_files(paths: Sequence[Path]) -> Iterator[Path]:
    """Yield ``.py`` files under ``paths``, skipping virtualenvs and caches."""
    for path in paths:
        if path.is_file():
            yield path
            continue
        for file_path in sorted(path.rglob('*.py')):
            if _SKIP_DIRS.isdisjoint(file_path.parts):
                yield file_path


def _dotted_name(node: cst.BaseExpression) -> str | None:
    if isinstance(node, cst.Name):
        return node.value
    if isinstance(node, cst.Attribute):
        base = _dotted_name(node.value)
        return None if base is None else f'{base}.{node.attr.value}'
    return None


def _is_dmr_module(name: str) -> bool:
    return name == 'dmr' or name.startswith('dmr.')


def _imported_as(alias: cst.ImportAlias) -> str | None:
    asname = alias.asname
    if asname is not None:
        return _dotted_name(asname.name)
    dotted = _dotted_name(alias.name)
    return None if dotted is None else dotted.split('.')[0]


class DmrNames(cst.CSTVisitor):
    """Collect the names that refer to ``dmr`` objects in one module."""

    def __init__(self) -> None:
        """Start with an empty name set."""
        super().__init__()
        self.names: set[str] = set()

    @override
    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        """Remember every name imported from a ``dmr`` module."""
        module = node.module
        if module is None or isinstance(node.names, cst.ImportStar):
            return
        dotted = _dotted_name(module)
        if dotted is None or not _is_dmr_module(dotted):
            return
        self.names.update(
            name for alias in node.names if (name := _imported_as(alias))
        )

    @override
    def visit_Import(self, node: cst.Import) -> None:
        """Remember ``import dmr.something`` and its alias."""
        for alias in node.names:
            dotted = _dotted_name(alias.name)
            name = _imported_as(alias)
            if name and dotted is not None and _is_dmr_module(dotted):
                self.names.add(name)


class KeywordRenamer(cst.CSTTransformer):
    """Rename keyword arguments of calls to the configured callees."""

    def __init__(
        self,
        keywords: Sequence[KeywordRename],
        dmr_names: frozenset[str],
    ) -> None:
        """Remember the renames, ``changed`` is set when any applied."""
        super().__init__()
        self._keywords = keywords
        self._dmr_names = dmr_names
        self.changed = False

    @override
    def leave_Call(
        self,
        original_node: cst.Call,
        updated_node: cst.Call,
    ) -> cst.Call:
        """Rewrite keyword names on matching calls."""
        callee = _dotted_name(updated_node.func)
        if callee is None or not self._is_dmr_call(callee):
            return updated_node
        renames = {
            keyword['old']: keyword['new']
            for keyword in self._keywords
            if keyword['callee'] == callee.rsplit('.', 1)[-1]
        }
        if not renames:
            return updated_node
        return updated_node.with_changes(
            args=[self._rename_arg(arg, renames) for arg in updated_node.args],
        )

    def _is_dmr_call(self, callee: str) -> bool:
        # Callees are matched by their last name only, so a call is rewritten
        # only when that name, or the module it is called on, comes from
        # ``dmr``. Otherwise `marshmallow.Schema(then=...)` would be renamed.
        parts = callee.split('.')
        return parts[-1] in self._dmr_names or parts[0] in self._dmr_names

    def _rename_arg(self, arg: cst.Arg, renames: dict[str, str]) -> cst.Arg:
        if arg.keyword is None or arg.keyword.value not in renames:
            return arg
        self.changed = True
        return arg.with_changes(
            keyword=arg.keyword.with_changes(value=renames[arg.keyword.value]),
        )


def rewrite_module(
    source: str,
    filename: str,
    release: Release,
) -> str:
    """Apply ``symbols`` and ``keywords`` of a release to one module."""
    module = cst.parse_module(source)
    for symbol in release['symbols']:
        context = CodemodContext(filename=filename)
        command = RenameCommand(context, symbol['old'], symbol['new'])
        module = command.transform_module(module)
    dmr_names = DmrNames()
    module.visit(dmr_names)
    renamer = KeywordRenamer(release['keywords'], frozenset(dmr_names.names))
    module = module.visit(renamer)
    return module.code


def report_manual_checks(
    path: Path,
    source: str,
    release: Release,
) -> int:
    """Print every line that matches a manual check, return the count."""
    checks = [
        (re.compile(check['pattern']), check['message'])
        for check in release['manual']
    ]
    removed = [
        (re.compile(r'\b' + re.escape(name.rsplit('.', 1)[-1]) + r'\b'), name)
        for name in release['removed']
    ]
    found = 0
    for lineno, line in enumerate(source.splitlines(), start=1):
        for pattern, message in checks:
            if pattern.search(line):
                print(f'{path}:{lineno}: [{release["to"]}] {message}')
                found += 1
        for pattern, name in removed:
            if pattern.search(line):
                print(f'{path}:{lineno}: [{release["to"]}] {name} was removed')
                found += 1
    return found


def upgrade_file(
    path: Path,
    releases: Sequence[Release],
    *,
    dry_run: bool,
) -> tuple[bool, int]:
    """Rewrite one file across all releases, return (changed, manual_hits)."""
    original = path.read_text(encoding='utf-8')
    source = original
    manual_hits = 0
    for release in releases:
        # Manual checks describe the API *before* this release,
        # so they must not see what its own codemod has just written:
        manual_hits += report_manual_checks(path, source, release)
        if not (release['symbols'] or release['keywords']):
            continue
        try:
            source = rewrite_module(source, str(path), release)
        except cst.ParserSyntaxError as exc:
            print(f'{path}: cannot parse, skipped: {exc}', file=sys.stderr)
            return False, manual_hits
    changed = source != original
    if changed and not dry_run:
        path.write_text(source, encoding='utf-8')
    return changed, manual_hits


def build_parser() -> argparse.ArgumentParser:
    """Command line interface."""
    parser = argparse.ArgumentParser(
        description='Apply django-modern-rest upgrade codemods.',
    )
    parser.add_argument(
        'paths',
        nargs='+',
        type=Path,
        help='Files or directories to upgrade',
    )
    parser.add_argument(
        '--target',
        required=True,
        help='Version to upgrade to, for example 0.16.0',
    )
    parser.add_argument(
        '--current',
        default=None,
        help='Version to upgrade from, defaults to the installed one',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Report changes without writing files',
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point, returns the process exit code."""
    args = build_parser().parse_args(argv)
    current = args.current or detect_current_version()
    if current is None:
        print(
            'django-modern-rest is not installed here, pass --current',
            file=sys.stderr,
        )
        return 2
    releases = select_releases(load_releases(), current, args.target)
    if not releases:
        print(f'Nothing to do between {current} and {args.target}')
        return 0
    print(
        'Applying releases: {}'.format(
            ', '.join(release['to'] for release in releases),
        ),
    )
    rewritten = 'would be rewritten' if args.dry_run else 'rewritten'
    changed_files = 0
    manual_hits = 0
    for path in iter_python_files(args.paths):
        changed, hits = upgrade_file(path, releases, dry_run=args.dry_run)
        changed_files += int(changed)
        manual_hits += hits
        if changed:
            print(f'{path}: {rewritten}')
    print(
        f'{changed_files} file(s) {rewritten}, {manual_hits} manual check(s). '
        + 'Now read the migration prompts: '
        + ', '.join(f'references/{release["prompt"]}' for release in releases),
    )
    return 0


if __name__ == '__main__':
    sys.exit(main())

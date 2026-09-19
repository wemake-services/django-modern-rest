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

``--current`` defaults to the installed ``django-modern-rest`` version,
pass it explicitly when the script runs outside of the project environment.
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
    """Convert ``'0.16.0'`` into a comparable tuple."""
    return tuple(int(part) for part in text.split('.'))


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


def _callee_name(func: cst.BaseExpression) -> str | None:
    if isinstance(func, cst.Name):
        return func.value
    if isinstance(func, cst.Attribute):
        return func.attr.value
    return None


class KeywordRenamer(cst.CSTTransformer):
    """Rename keyword arguments of calls to the configured callees."""

    def __init__(self, keywords: Sequence[KeywordRename]) -> None:
        """Remember the renames, ``changed`` is set when any applied."""
        super().__init__()
        self._keywords = keywords
        self.changed = False

    @override
    def leave_Call(
        self,
        original_node: cst.Call,
        updated_node: cst.Call,
    ) -> cst.Call:
        """Rewrite keyword names on matching calls."""
        callee = _callee_name(updated_node.func)
        renames = {
            keyword['old']: keyword['new']
            for keyword in self._keywords
            if keyword['callee'] == callee
        }
        if not renames:
            return updated_node
        return updated_node.with_changes(
            args=[self._rename_arg(arg, renames) for arg in updated_node.args],
        )

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
    renamer = KeywordRenamer(release['keywords'])
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
        (re.compile(re.escape(name.rsplit('.', 1)[-1]) + r'\b'), name)
        for name in release['removed']
    ]
    found = 0
    for lineno, line in enumerate(source.splitlines(), start=1):
        for pattern, message in checks:
            if pattern.search(line):
                print(f'{path}:{lineno}: [{release["to"]}] {message}')  # noqa: WPS421
                found += 1
        for pattern, name in removed:
            if pattern.search(line):
                print(f'{path}:{lineno}: [{release["to"]}] {name} was removed')  # noqa: WPS421
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
        if release['symbols'] or release['keywords']:
            source = rewrite_module(source, str(path), release)
        manual_hits += report_manual_checks(path, source, release)
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
        print(  # noqa: WPS421
            'django-modern-rest is not installed here, pass --current',
            file=sys.stderr,
        )
        return 2
    releases = select_releases(load_releases(), current, args.target)
    if not releases:
        print(f'Nothing to do between {current} and {args.target}')  # noqa: WPS421
        return 0
    print(  # noqa: WPS421
        'Applying releases: {}'.format(
            ', '.join(release['to'] for release in releases),
        ),
    )
    changed_files = 0
    manual_hits = 0
    for path in iter_python_files(args.paths):
        changed, hits = upgrade_file(path, releases, dry_run=args.dry_run)
        changed_files += int(changed)
        manual_hits += hits
        if changed:
            print(f'{path}: rewritten')  # noqa: WPS421
    print(  # noqa: WPS421
        f'{changed_files} file(s) rewritten, {manual_hits} manual check(s). '
        + 'Now read the migration prompts: '
        + ', '.join(f'references/{release["prompt"]}' for release in releases),
    )
    return 0


if __name__ == '__main__':
    sys.exit(main())

"""
Tests for the codemod shipped with the ``dmr-upgrade`` agent skill.

The script is a standalone tool that runs in other projects, so it is not
importable as a module of our package: it is loaded from its own path.
``libcst`` is a dev dependency, the wheel test environment does not have it.
"""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Any, Final

import pytest

import dmr

pytest.importorskip('libcst')

_SCRIPT: Final = (
    Path(dmr.__file__).parent
    / '.agents'
    / 'skills'
    / 'dmr-upgrade'
    / 'scripts'
    / 'dmr_upgrade.py'
)


def _load_script() -> ModuleType:
    spec = spec_from_file_location('dmr_upgrade', _SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _release(**kwargs: Any) -> dict[str, Any]:
    release = {
        'to': '0.13.0',
        'prompt': '0.12-to-0.13.md',
        'symbols': [],
        'keywords': [],
        'removed': [],
        'manual': [],
    }
    return release | kwargs


@pytest.fixture(scope='module')
def codemod() -> ModuleType:
    """The codemod script, loaded from the skill directory."""
    return _load_script()


@pytest.mark.parametrize(
    ('version', 'expected'),
    [
        ('0.16.0', (0, 16, 0)),
        ('0.16', (0, 16, 0)),
        ('1', (1, 0, 0)),
        ('0.16.0rc1', (0, 16, 0)),
        ('0.16.0.dev1', (0, 16, 0)),
        ('0.16.0+local.1', (0, 16, 0)),
    ],
)
def test_parse_version(
    codemod: ModuleType,
    version: str,
    expected: tuple[int, ...],
) -> None:
    """Every version we can meet in the wild is comparable."""
    assert codemod.parse_version(version) == expected


def test_select_releases(codemod: ModuleType) -> None:
    """Releases in ``(current, target]`` are selected, oldest first."""
    releases = codemod.load_releases()

    selected = codemod.select_releases(releases, '0.12.0', '0.16.0')

    assert [release['to'] for release in selected] == [
        '0.13.0',
        '0.14.0',
        '0.15.0',
        '0.16.0',
    ]


def test_select_releases_short_target(codemod: ModuleType) -> None:
    """``0.16`` and ``0.16.0`` mean the same release."""
    releases = codemod.load_releases()

    assert codemod.select_releases(
        releases,
        '0.15.0',
        '0.16',
    ) == codemod.select_releases(releases, '0.15.0', '0.16.0')


def test_select_releases_already_upgraded(codemod: ModuleType) -> None:
    """Nothing is selected when the target version is the current one."""
    releases = codemod.load_releases()

    assert not codemod.select_releases(releases, '0.16.0', '0.16.0')


def test_shipped_renames_are_applied(
    codemod: ModuleType,
    tmp_path: Path,
) -> None:
    """A real rename from ``renames.json`` rewrites imports and usages."""
    module = tmp_path / 'views.py'
    module.write_text(
        'from dmr.openapi.dump import json_dump\n\ndumped = json_dump({})\n',
        encoding='utf-8',
    )
    releases = codemod.select_releases(
        codemod.load_releases(),
        '0.14.0',
        '0.15.0',
    )

    changed, manual_hits = codemod.upgrade_file(
        module,
        releases,
        dry_run=False,
    )

    assert changed
    assert not manual_hits
    assert module.read_text(encoding='utf-8') == (
        'from dmr.openapi.dump import json_dumps\n\ndumped = json_dumps({})\n'
    )


def test_keyword_rename_needs_a_dmr_import(
    codemod: ModuleType,
    tmp_path: Path,
) -> None:
    """Keywords are matched by name, other libraries must not be touched."""
    source = 'from marshmallow import Schema\n\nschema = Schema(then=1)\n'
    module = tmp_path / 'schemas.py'
    module.write_text(source, encoding='utf-8')
    release = _release(
        keywords=[{'callee': 'Schema', 'old': 'then', 'new': 'schema_then'}],
    )

    changed, _ = codemod.upgrade_file(module, [release], dry_run=False)

    assert not changed
    assert module.read_text(encoding='utf-8') == source


@pytest.mark.parametrize(
    'source',
    [
        'from dmr.openapi.objects import Schema\n\nschema = Schema(then=1)\n',
        'import dmr\n\nschema = dmr.Schema(then=1)\n',
    ],
)
def test_keyword_rename_applies_to_dmr(
    codemod: ModuleType,
    tmp_path: Path,
    source: str,
) -> None:
    """Our own calls are renamed, imported directly or through a module."""
    module = tmp_path / 'schemas.py'
    module.write_text(source, encoding='utf-8')
    release = _release(
        keywords=[{'callee': 'Schema', 'old': 'then', 'new': 'schema_then'}],
    )

    changed, _ = codemod.upgrade_file(module, [release], dry_run=False)

    assert changed
    assert 'schema_then=1' in module.read_text(encoding='utf-8')


def test_manual_checks_do_not_see_the_rewrite(
    codemod: ModuleType,
    tmp_path: Path,
) -> None:
    """A release must not report the code its own codemod has written."""
    module = tmp_path / 'views.py'
    module.write_text(
        'from dmr.openapi.objects.openapi import ConvertedSchema\n\n'
        'schema: ConvertedSchema\n',
        encoding='utf-8',
    )
    releases = codemod.select_releases(
        codemod.load_releases(),
        '0.12.0',
        '0.13.0',
    )

    changed, manual_hits = codemod.upgrade_file(
        module,
        releases,
        dry_run=False,
    )

    assert changed
    assert not manual_hits
    assert 'DumpedSchema' in module.read_text(encoding='utf-8')


def test_removed_symbols_need_a_whole_word(
    codemod: ModuleType,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``dmr.test.types`` must not match ``content_types``."""
    module = tmp_path / 'views.py'
    module.write_text(
        'CONTENT_TYPES = ()\n'
        '# a comment about content_types\n'
        'import dmr.test.types\n',
        encoding='utf-8',
    )

    _, manual_hits = codemod.upgrade_file(
        module,
        [_release(removed=['dmr.test.types'])],
        dry_run=False,
    )

    assert manual_hits == 1
    assert 'views.py:3' in capsys.readouterr().out


def test_unparsable_file_is_skipped(
    codemod: ModuleType,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A file we cannot parse does not abort the whole run."""
    source = 'def broken(:\n    pass\n'
    module = tmp_path / 'broken.py'
    module.write_text(source, encoding='utf-8')
    release = _release(
        symbols=[{'old': 'dmr.old.Name', 'new': 'dmr.new.Name'}],
    )

    changed, _ = codemod.upgrade_file(module, [release], dry_run=False)

    assert not changed
    assert module.read_text(encoding='utf-8') == source
    assert 'cannot parse' in capsys.readouterr().err


def test_dry_run_does_not_write(
    codemod: ModuleType,
    tmp_path: Path,
) -> None:
    """``--dry-run`` reports the change without touching the file."""
    source = 'from dmr.openapi.dump import json_dump\n'
    module = tmp_path / 'views.py'
    module.write_text(source, encoding='utf-8')
    releases = codemod.select_releases(
        codemod.load_releases(),
        '0.14.0',
        '0.15.0',
    )

    changed, _ = codemod.upgrade_file(module, releases, dry_run=True)

    assert changed
    assert module.read_text(encoding='utf-8') == source


def test_main_without_releases(
    codemod: ModuleType,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Nothing to do between two versions without breaking changes."""
    exit_code = codemod.main(
        ['--current', '0.16.0', '--target', '0.16.0', str(tmp_path)],
    )

    assert not exit_code
    assert 'Nothing to do' in capsys.readouterr().out


def test_main_rewrites_the_project(
    codemod: ModuleType,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """End to end run over a directory, as the skill documents it."""
    module = tmp_path / 'views.py'
    module.write_text(
        'from dmr.openapi.dump import json_dump\n\ndumped = json_dump({})\n',
        encoding='utf-8',
    )

    exit_code = codemod.main(
        [
            '--current',
            '0.14.0',
            '--target',
            '0.15.0',
            '--dry-run',
            str(tmp_path),
        ],
    )

    assert not exit_code
    assert 'would be rewritten' in capsys.readouterr().out
    assert 'json_dump(' in module.read_text(encoding='utf-8')


def test_main_without_a_version(
    codemod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """We ask for ``--current`` when the package is not installed."""
    monkeypatch.setattr(codemod, 'detect_current_version', lambda: None)

    exit_code = codemod.main(['--target', '0.16.0', str(tmp_path)])

    assert exit_code == 2
    assert 'pass --current' in capsys.readouterr().err


def test_python_files_skip_caches(
    codemod: ModuleType,
    tmp_path: Path,
) -> None:
    """Virtualenvs and caches are not upgraded."""
    (tmp_path / '.venv').mkdir()
    (tmp_path / '.venv' / 'ignored.py').touch()
    (tmp_path / 'app.py').touch()

    found = list(codemod.iter_python_files([tmp_path]))

    assert found == [tmp_path / 'app.py']

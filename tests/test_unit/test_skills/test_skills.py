"""
Structural checks for the agent skills shipped inside the ``dmr`` package.

They keep the skills valid for every agent that follows
https://agentskills.io/specification and keep the Claude Code
marketplace in sync with the package contents.
"""

import json
import re
from pathlib import Path
from typing import Final

import pytest
import yaml

import dmr

_SKILLS_DIR: Final = Path(dmr.__file__).parent / '.agents' / 'skills'
_REPO_ROOT: Final = Path(__file__).resolve().parents[3]
_MARKETPLACE: Final = _REPO_ROOT / '.claude-plugin' / 'marketplace.json'
_SKILL_NAME: Final = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')
_MAX_NAME_LENGTH: Final = 64
_MAX_DESCRIPTION_LENGTH: Final = 1024
_MAX_BODY_LINES: Final = 500
_AGENT_NAMES: Final = ('Codex', 'Claude', 'Cursor', 'Copilot', 'Gemini')
_LOCAL_LINK: Final = re.compile(r'\]\(((?:references|scripts)/[^)#]+)')

_SKILLS: Final = sorted(
    path for path in _SKILLS_DIR.iterdir() if (path / 'SKILL.md').is_file()
)


def _split_frontmatter(skill_dir: Path) -> tuple[dict[str, object], str]:
    _, frontmatter, body = (
        (skill_dir / 'SKILL.md')
        .read_text()
        .split(
            '---\n',
            2,
        )
    )
    return yaml.safe_load(frontmatter), body


@pytest.mark.parametrize('skill_dir', _SKILLS, ids=lambda path: path.name)
def test_skill_frontmatter(skill_dir: Path) -> None:
    """Skills follow the Agent Skills specification."""
    frontmatter, body = _split_frontmatter(skill_dir)

    name = frontmatter['name']
    description = frontmatter['description']
    assert isinstance(name, str)
    assert isinstance(description, str)
    assert name == skill_dir.name
    assert _SKILL_NAME.match(name)
    assert len(name) <= _MAX_NAME_LENGTH
    assert 0 < len(description) <= _MAX_DESCRIPTION_LENGTH
    assert description.startswith(('Write', 'Migrate', 'Generate', 'Upgrade'))
    # Skills are cross-agent, descriptions must not target a single host:
    assert not any(agent in description for agent in _AGENT_NAMES)
    assert body.count('\n') <= _MAX_BODY_LINES


@pytest.mark.parametrize('skill_dir', _SKILLS, ids=lambda path: path.name)
def test_skill_local_links(skill_dir: Path) -> None:
    """Every referenced local file exists, progressive disclosure works."""
    markdown_files = [skill_dir / 'SKILL.md']
    markdown_files.extend((skill_dir / 'references').glob('*.md'))

    for markdown_file in markdown_files:
        for link in _LOCAL_LINK.findall(markdown_file.read_text()):
            assert (skill_dir / link).is_file(), f'{markdown_file}: {link}'


@pytest.mark.parametrize('skill_dir', _SKILLS, ids=lambda path: path.name)
def test_skill_host_metadata(skill_dir: Path) -> None:
    """Claude Code plugin and Codex metadata match the skill."""
    plugin = json.loads(
        (skill_dir / '.claude-plugin' / 'plugin.json').read_text(),
    )
    codex = yaml.safe_load((skill_dir / 'agents' / 'openai.yaml').read_text())

    assert plugin['name'] == skill_dir.name
    assert plugin['skills'] == ['./']
    assert codex['interface']['display_name']
    assert skill_dir.name in codex['interface']['default_prompt']


def test_marketplace_lists_every_skill() -> None:
    """The marketplace manifest points at every shipped skill."""
    marketplace = json.loads(_MARKETPLACE.read_text())
    plugins = {plugin['name']: plugin for plugin in marketplace['plugins']}

    assert set(plugins) == {skill_dir.name for skill_dir in _SKILLS}
    for name, plugin in plugins.items():
        assert plugin['source'] == f'./dmr/.agents/skills/{name}'
        assert (_REPO_ROOT / plugin['source'] / 'SKILL.md').is_file()
        assert plugin['keywords']
        assert plugin['license'] == 'MIT'


def test_upgrade_prompts_are_indexed() -> None:
    """Every migration prompt is known to the codemod, in version order."""
    upgrade_dir = _SKILLS_DIR / 'dmr-upgrade'
    releases = json.loads(
        (upgrade_dir / 'references' / 'renames.json').read_text(),
    )['releases']
    prompts = {release['prompt'] for release in releases}
    versions = [
        tuple(int(part) for part in release['to'].split('.'))
        for release in releases
    ]

    assert versions == sorted(versions)
    assert prompts == {
        path.name for path in (upgrade_dir / 'references').glob('*-to-*.md')
    }
    for prompt in prompts:
        assert (
            (upgrade_dir / 'references' / prompt)
            .read_text()
            .startswith(
                '# Upgrade django-modern-rest from',
            )
        )


def test_docs_mention_every_skill() -> None:
    """The docs advertise every skill by its ``$name``."""
    docs = (
        _REPO_ROOT / 'docs' / 'pages' / 'ai' / 'agent-skills.rst'
    ).read_text()

    for skill_dir in _SKILLS:
        assert f'``${skill_dir.name}``' in docs

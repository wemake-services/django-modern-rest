---
name: dmr-upgrade
description: Upgrade a project to a newer django-modern-rest (dmr) release. Use when bumping the django-modern-rest version, when a dependency update breaks imports from `dmr`, or when asked to migrate to a new dmr release. Runs the bundled codemods first, then applies the official migration prompt of every release in between.
license: MIT
metadata:
  author: wemake-services
  homepage: https://django-modern-rest.readthedocs.io/en/latest/pages/ai/dmr-upgrade.html
---

# DMR upgrade

## Overview

Every breaking `django-modern-rest` release ships an official migration prompt.
They all live in this skill, one file per release in [references/](references/),
together with a `libcst` codemod for the mechanical renames.
The `CHANGELOG.md` of the package lists the breaking changes themselves.

Do not guess how an API changed. Read the prompt for every release
between the installed version and the target version and apply all of it.

## Workflow

### 1. Find the current and the target versions

- Current: `uv pip show django-modern-rest`, `pip show django-modern-rest`,
  or the pinned version in `uv.lock`, `poetry.lock`, or `requirements.txt`.
- Target: the version the user asked for, otherwise the latest release
  on https://pypi.org/project/django-modern-rest/.
- Tell the user which releases lie in between and that each one
  is applied in order. Never skip a release.

### 2. Bump the dependency

Update `pyproject.toml` (or the requirements file) to the target version
and install it, so the codemod can detect the version
and the type checker sees the new API.

### 3. Run the codemod

From the root of the project being upgraded:

```bash
uv run --with libcst python <path-to-this-skill>/scripts/dmr_upgrade.py \
  --target <target-version> .
```

Pass `--current <version>` when `django-modern-rest` is not importable
in that environment and `--dry-run` to preview. The script:

- rewrites moved and renamed symbols, including imports,
- renames keyword arguments on the affected calls,
- prints `path:line: [release] message` for everything that needs
  a decision, and lists the prompts to read next.

Commit or stash the codemod result separately from the manual edits,
so the user can review both.

### 4. Apply each migration prompt

Read the prompt files for the selected releases, oldest first,
and apply every numbered item to the whole project
(source, tests, fixtures, settings, management commands):

| Upgrade across | Prompt |
| --- | --- |
| 0.3 to 0.4 | [references/0.3-to-0.4.md](references/0.3-to-0.4.md) |
| 0.6 to 0.7 | [references/0.6-to-0.7.md](references/0.6-to-0.7.md) |
| 0.7 to 0.8 | [references/0.7-to-0.8.md](references/0.7-to-0.8.md) |
| 0.9 to 0.10 | [references/0.9-to-0.10.md](references/0.9-to-0.10.md) |
| 0.12 to 0.13 | [references/0.12-to-0.13.md](references/0.12-to-0.13.md) |
| 0.13 to 0.14 | [references/0.13-to-0.14.md](references/0.13-to-0.14.md) |
| 0.14 to 0.15 | [references/0.14-to-0.15.md](references/0.14-to-0.15.md) |
| 0.15 to 0.16 | [references/0.15-to-0.16.md](references/0.15-to-0.16.md) |

Releases that are not listed had no breaking changes.
[references/renames.json](references/renames.json) is the machine-readable
index that the codemod uses, it names the prompt file of every release.

When the installed docs matter, load the version-specific index:
`https://django-modern-rest.readthedocs.io/en/<version>/llms.txt`
(every page is also served as Markdown, replace `.html` with `.md`).

### 5. Verify

- Run the type checker of the project, it catches most renamed
  and re-typed APIs.
- Run the test suite.
- Run `python manage.py check` and, when OpenAPI is used,
  `python manage.py dmr_export_schema <schema-path>` and diff the output
  against the previous schema: only intended changes should appear.
- Search the project for every symbol named in the prompts,
  the upgrade is complete when none is left.

## Reporting

Finish with a short report:

- releases applied, in order,
- what the codemod rewrote,
- every manual change, grouped by prompt item,
- items that could not be resolved and why (for example, a removed feature
  with no replacement), with the exact file and line.

Do not change business logic, response contracts, or settings
beyond what a prompt item requires. If a prompt item conflicts with
project behavior the user wants to keep, stop and ask.

---
name: dmr-upgrade
description: Upgrade a project to a newer django-modern-rest (dmr) release. Use when bumping the django-modern-rest version, when a dependency update breaks imports from `dmr`, or when asked to migrate to a new dmr release. Applies bundled migration prompts in order and checks release notes and the changelog for other releases.
license: MIT
metadata:
  author: wemake-services
  homepage: https://django-modern-rest.readthedocs.io/en/latest/pages/ai/dmr-upgrade.html
---

# DMR upgrade

## Overview

This skill bundles migration prompts in [references/](references/).
The table below highlights the three latest releases with breaking changes.
Older prompts can remain bundled for historical transitions.
The prompts are based on `CHANGELOG.md`, release notes, and tagged sources,
using the official release prompt when one is published.

## Workflow

### Find the current and the target versions

- Current: `uv pip show django-modern-rest`, `pip show django-modern-rest`,
  or the pinned version in `uv.lock`, `poetry.lock`, or `requirements.txt`.
- Target: the version the user asked for, otherwise the latest release
  on https://pypi.org/project/django-modern-rest/.
- If the current and target versions are the same, report that there is
  nothing to upgrade and stop.

### Resolve the migration path

Before editing dependencies or installing anything, list every published
release in `installed < release <= target`, using the project's version
ordering. Check them oldest first and tell the user which ones you will cross.
For each release, select its bundled prompt by destination version:

| Upgrade across | Prompt |
| --- | --- |
| 0.14 to 0.15 | [references/0.14-to-0.15.md](references/0.14-to-0.15.md) |
| 0.15 to 0.16 | [references/0.15-to-0.16.md](references/0.15-to-0.16.md) |
| 0.16 to 0.17 | [references/0.16-to-0.17.md](references/0.16-to-0.17.md) |

For `0.13` to `0.14`, read the bundled
[historical prompt](references/0.13-to-0.14.md). The
[copy in the `0.17.0` tag](https://raw.githubusercontent.com/wemake-services/django-modern-rest/0.17.0/dmr/.agents/skills/dmr-upgrade/references/0.13-to-0.14.md)
is the fallback if the local file is missing. The `0.14.0` release notes
have the right `ExternalURL` to `external_path` replacement but the wrong
transition in the preamble and an obsolete `llms-full.txt` link.

Do not assume unlisted releases have no breaking changes. For a release
without a bundled prompt, check its exact release notes and `CHANGELOG.md`
before ruling out incompatibilities. Before `0.13.0`, use `CHANGELOG.md`
as the primary source. If no official prompt is available, corroborate
the migration steps against the docs and sources of the release tag.

If you cannot establish the full release sequence or confirm an applicable
transition, report what is unresolved and why. Stop before changing the
dependency, lockfile, or environment.

### Bump the dependency

Update `pyproject.toml` (or the requirements file) to the target version
and install it, so the type checker sees the new API.

### Apply each migration prompt

Apply the confirmed steps from oldest to newest. Search the whole project,
including source, tests, fixtures, settings, and management commands.

Apply one release at a time and keep its edits together,
so the user can review them release by release.

When the installed docs matter, load the version-specific index:
`https://django-modern-rest.readthedocs.io/en/<version>/llms.txt`
(every page is also served as Markdown, replace `.html` with `.md`).

### Verify

- Run the type checker of the project, it catches most renamed
  and re-typed APIs.
- Run the test suite.
- Run `python manage.py check` and, when OpenAPI is used,
  `python manage.py dmr_export_schema <schema-path>` and diff the output
  against the previous schema: only intended changes should appear.
- For each transition you crossed, search for the API forms that became
  outdated in that transition. Check the actual usages, not just imports.
  Leave usages that are still valid on the requested target version alone.

## Reporting

Finish with a short report:

- releases applied, in order,
- every change, grouped by prompt item,
- items that could not be resolved and why (for example, a removed feature
  with no replacement), with the exact file and line.

Do not change business logic, response contracts, or settings
beyond what a prompt item requires. If a prompt item conflicts with
project behavior the user wants to keep, stop and ask.

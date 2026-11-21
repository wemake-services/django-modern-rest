---
name: dmr-upgrade
description: Upgrade a project to a newer django-modern-rest (dmr) release. Use when bumping the django-modern-rest version, when a dependency update breaks imports from `dmr`, or when asked to migrate to a new dmr release. Applies the bundled migration guides for the supported releases in order, and checks the release notes for the rest.
license: MIT
metadata:
  author: wemake-services
  homepage: https://django-modern-rest.readthedocs.io/en/latest/pages/ai/dmr-upgrade.html
---

# DMR upgrade

## Overview

The migration guides of the three latest `django-modern-rest` releases
with breaking changes live in this skill, one file per release in
[references/](references/).
They are based on the package `CHANGELOG.md` and the release notes,
using the official migration prompt where one is published.
The `CHANGELOG.md` of the package lists the breaking changes themselves.

Do not guess how an API changed. Read the bundled guide or the release
notes for every release between the installed version and the target
version and apply all of it.

## Workflow

### Find the current and the target versions

- Current: `uv pip show django-modern-rest`, `pip show django-modern-rest`,
  or the pinned version in `uv.lock`, `poetry.lock`, or `requirements.txt`.
- Target: the version the user asked for, otherwise the latest release
  on https://pypi.org/project/django-modern-rest/.
- Tell the user which releases lie in between and that each one
  is applied in order. Never skip a release.

### Bump the dependency

Update `pyproject.toml` (or the requirements file) to the target version
and install it, so the type checker sees the new API.

### Apply each migration prompt

Read the prompt files for the selected releases, oldest first,
and apply every numbered item to the whole project
(source, tests, fixtures, settings, management commands):

| Upgrade across | Prompt |
| --- | --- |
| 0.14 to 0.15 | [references/0.14-to-0.15.md](references/0.14-to-0.15.md) |
| 0.15 to 0.16 | [references/0.15-to-0.16.md](references/0.15-to-0.16.md) |
| 0.16 to 0.17 | [references/0.16-to-0.17.md](references/0.16-to-0.17.md) |

For `0.13` to `0.14`, read the pinned copy of the prompt in the `0.17.0` tag:
https://raw.githubusercontent.com/wemake-services/django-modern-rest/0.17.0/dmr/.agents/skills/dmr-upgrade/references/0.13-to-0.14.md

It is the corrected copy of the `0.14.0` release notes: the release page
mistakenly calls the transition `0.12.0` to `0.13.0` and links the removed
`llms-full.txt`. If the raw URL is not reachable, read
`dmr/.agents/skills/dmr-upgrade/references/0.13-to-0.14.md` from the
`0.17.0` git tag, or the `0.14.0` release notes, and use the
`ExternalURL` to `external_path` replacement from it. Ignore the wrong
versions and the `llms-full.txt` link in the release notes preamble.

Do not assume that a release missing from the table had no breaking
changes. Check every release in `installed < release <= target` against its
release notes and `CHANGELOG.md` before concluding that nothing is
incompatible. Pick a bundled guide by its destination version, and use the
pinned `0.13` to `0.14` archive for `0.14.0`. For any other release since
`0.13.0` without a bundled guide, read the release notes of that exact
release; before `0.13.0`, read `CHANGELOG.md`.

When a release has no official migration prompt, check its
`Breaking changes` section and the docs and sources of its tag, and apply
only the changes they confirm. If the sources are unavailable and an
incompatibility cannot be excluded, list that release and the reason among
the unresolved items; do not move through an unverified transition.
Apply the releases from the oldest to the newest, the same way.

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
- Search for the remaining outdated forms of the changed APIs, not for
  the presence of the new names. An `EMPTY` import does not remove a
  `Sentinel` annotation, a `TypeForm` import does not fix an override still
  typed `Any`, a bare `csrf_security_scheme()` call is still the old
  signature, and a cookie-mode requirement that lists `csrf` without
  `csrf_header` is still outdated. The upgrade is complete when no
  outdated usage remains.

## Reporting

Finish with a short report:

- releases applied, in order,
- every change, grouped by prompt item,
- items that could not be resolved and why (for example, a removed feature
  with no replacement), with the exact file and line.

Do not change business logic, response contracts, or settings
beyond what a prompt item requires. If a prompt item conflicts with
project behavior the user wants to keep, stop and ask.

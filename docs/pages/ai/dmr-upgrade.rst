Upgrading with an agent
=======================

By example, you can use agent skill
`dmr-upgrade <https://github.com/wemake-services/django-modern-rest/tree/master/dmr/.agents/skills/dmr-upgrade>`_
to upgrade a project to a newer ``django-modern-rest`` release.

Every release with breaking changes ships an official migration prompt.
All of them live in the skill, one file per release in its ``references/``
directory, together with a ``libcst`` codemod for the mechanical renames.
The :doc:`changelog <../deep-dive/changelog>` lists the breaking changes themselves.

.. important::

  Read the codemod output and the agent's report before running your app.
  The codemod only rewrites renamed symbols and keyword arguments,
  everything that changes behavior is described in the prompts
  and needs a human decision.


How to use in Codex
-------------------

1. Bump ``django-modern-rest`` in your dependencies and install it.
2. Ask Codex to use the skill ``$dmr-upgrade``.
3. Review the report: releases applied, codemod changes, manual changes,
   and unresolved items.

You can use a prompt like this:

.. code-block:: text

   $dmr-upgrade Upgrade this project from django-modern-rest 0.14.0
   to 0.16.0. Run the codemod first, then apply every migration prompt
   in order, run mypy and the test suite after each release,
   and list every change you could not resolve.

How to use in Claude Code
-------------------------

1. Add the marketplace and install the plugin:

.. code-block:: text

   /plugin marketplace add wemake-services/django-modern-rest
   /plugin install dmr-upgrade@django-modern-rest

2. Verify the plugin is installed and enabled:

.. code-block:: text

   /plugin

3. Invoke the skill:

.. code-block:: text

   /dmr-upgrade

4. Then name the target version and any constraints in a normal prompt.

See :doc:`agent-skills` for other agents.


Running the codemod by hand
---------------------------

The codemod does not need an agent. From the root of your project:

.. code-block:: bash

   uv run --with libcst python \
     .agents/skills/dmr-upgrade/scripts/dmr_upgrade.py --target 0.16.0 .

It detects the installed version (pass ``--current`` otherwise),
rewrites moved and renamed symbols including their imports,
renames keyword arguments on the affected calls,
and prints ``path:line: [release] message`` for everything
that needs a decision. Use ``--dry-run`` to preview.


What is migrated
----------------

- Renamed and moved classes, functions, and modules, including imports
- Renamed keyword arguments, like ``FileResponseSpec(file_body=...)``
- Everything else is reported with the file, line, and the reason,
  and described step by step in the migration prompt of that release

Business logic, response contracts, and settings are not changed
unless a migration prompt requires it.

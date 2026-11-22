Upgrading with an agent
=======================

By example, you can use agent skill
`dmr-upgrade <https://github.com/wemake-services/django-modern-rest/tree/master/dmr/.agents/skills/dmr-upgrade>`_
to upgrade a project to a newer ``django-modern-rest`` release.

The skill lists migration prompts for the three latest releases with
breaking changes and keeps the historical prompt for ``0.13.0`` to
``0.14.0`` bundled. If that file is missing, it uses the corrected copy
in the ``0.17.0`` tag, not the uncorrected release prompt.
For transitions without a bundled prompt, the skill uses the release notes
and the :doc:`changelog <../deep-dive/changelog>` to check what changed.

.. important::

  Read the agent's report and the diff before running your app.
  Everything that changes behavior needs a human decision.


How to use in Codex
-------------------

1. Note the version you are on. Leave your installed dependency unchanged.
2. Ask Codex to use the skill ``$dmr-upgrade``, naming both the old and
   the new version. It checks the migration path before updating the dependency.
3. Review the report: releases applied, changes made,
   and unresolved items.

You can use a prompt like this:

.. code-block:: text

   $dmr-upgrade Upgrade this project from django-modern-rest 0.14.0
   to 0.17.0. Check the migration path before updating the dependency.
   Apply the migration prompts in order, run mypy and the test suite,
   and list every change you could not resolve.

This example crosses three releases, so the skill applies three migration
prompts, oldest first.

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


What is migrated
----------------

- Renamed and moved classes, functions, and modules, including imports
- Renamed keyword arguments, like ``FileResponseSpec(file_body=...)``
- Other applicable release changes identified in the migration prompts
  or release notes

Business logic, response contracts, and settings are not changed
unless an applicable migration step requires it.

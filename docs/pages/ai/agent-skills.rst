Agent skills
============

``django-modern-rest`` ships official
`Agent Skills <https://agentskills.io>`_ inside the ``dmr`` package,
in ``dmr/.agents/skills/``. Skills are folders with a ``SKILL.md`` file
that coding agents load on demand: Claude Code, Codex, Cursor, Gemini CLI,
GitHub Copilot, and
`many others <https://agentskills.io/clients>`_ read the same format.

Because the skills live in the package, the skills you install always match
the version of ``django-modern-rest`` you have installed.

Available skills:

- ``$dmr`` to write ``django-modern-rest`` code with the recommended
  patterns, and to review existing code for common mistakes
- ``$dmr-upgrade`` to :doc:`upgrade to a newer release <dmr-upgrade>`
  with the official migration prompts
- ``$dmr-openapi-skeleton`` to :doc:`generate a project skeleton <spec-first>`
  from a single ``openapi.json`` file (the "Spec First" approach)
- ``$dmr-from-django-ninja`` to help with
  :doc:`migrating from Django Ninja <dmr-from-ninja>`
- ``$dmr-from-drf`` to help with
  :doc:`migrating from Django REST Framework <dmr-from-drf>`
- ``$dmr-from-dj-rest-auth`` to help with
  :doc:`migrating from dj-rest-auth <dmr-from-dj-rest-auth>`


Installation
------------

Any agent
~~~~~~~~~

`Library Skills <https://library-skills.io>`_ finds the skills bundled
with the libraries installed in your project and links them
into ``.agents/skills/``, where agents discover them:

.. code-block:: bash

  uvx library-skills            # -> .agents/skills/dmr, ...
  uvx library-skills --claude   # also .claude/skills/ for Claude Code

Run it again after upgrading ``django-modern-rest``,
the links follow the installed version.

Claude Code
~~~~~~~~~~~

Skills are also published as plugins in our marketplace:

.. code-block:: text

   /plugin marketplace add wemake-services/django-modern-rest
   /plugin install dmr@django-modern-rest

Replace ``dmr`` with any other skill name to install it.
Then invoke a skill as ``/dmr`` or just describe the task,
skills activate on their own when the request matches their description.

Codex
~~~~~

Codex reads ``.agents/skills/`` of the project directly,
so ``uvx library-skills`` is enough. Mention a skill with ``$dmr``
in a prompt to force it.


Documentation for LLMs
----------------------

Every skill tells the agent to read the documentation
of the installed version. These are the entry points:

- https://django-modern-rest.readthedocs.io/llms.txt
  is the index of all pages, with the version in its header
- https://django-modern-rest.readthedocs.io/llms-full.txt
  is the complete documentation in a single file
- every page is also published as Markdown: replace ``.html``
  with ``.md`` in its URL, for example
  https://django-modern-rest.readthedocs.io/en/latest/pages/routing.md
- the "Copy page" button on every page copies that Markdown,
  and its menu opens the page in ChatGPT or Claude
- `Context7 <https://context7.com/wemake-services/django-modern-rest>`_
  and `DeepWiki <https://deepwiki.com/wemake-services/django-modern-rest>`_
  index the same documentation

Use ``/en/<version>/`` in the URLs above to read the docs
of a specific release.


How skills are tested
---------------------

Skills are code and are tested like code:

- ``agentskills validate`` from the reference implementation
  runs in ``just lint`` on every skill
- unit tests check the frontmatter, local links,
  and that the Claude Code marketplace lists every skill
- `Claude Code plugin evals <https://code.claude.com/docs/en/plugin-evals>`_
  in ``dmr/.agents/skills/dmr/evals`` run real prompts with and without
  the skill and compare the results, see the ``skill-evals`` workflow

.. important::

  LLM-generated code cannot guarantee correctness.
  Always review the output, run the type checker and the test suite,
  and treat every skill as a draft assistant, not a decision maker.

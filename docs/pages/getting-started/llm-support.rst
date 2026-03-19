LLM and AI support
==================

If you use AI coding assistants (Cursor, GitHub Copilot, ChatGPT, etc.)
you can provide them up-to-date ``django-modern-rest`` documentation.
This page describes the formats we provide and the use cases we officially
support.


Documentation for AI context
----------------------------

Use the following URLs to supply documentation to your LLM or RAG pipeline.
Choose the format that fits your context window and workflow.

`Index (llms.txt) <https://django-modern-rest.readthedocs.io/llms.txt>`_ —
Structured index with links to sections and topics.
Use when the assistant has a limited context window or you want to point
it to specific pages.

.. code-block:: text

   https://django-modern-rest.readthedocs.io/llms.txt

`Full documentation (llms-full.txt) <https://django-modern-rest.readthedocs.io/llms-full.txt>`_ —
Complete documentation in a single plain-text file. Use when the model
supports large context or you need the entire reference in one place.

.. code-block:: text

   https://django-modern-rest.readthedocs.io/llms-full.txt

.. tip::

   If your assistant has a limited context window, start with the index
   (llms.txt) and add specific page URLs from it as needed.


Third-party integrations
------------------------

- **Context7** — `Context7 <https://context7.com/wemake-services/django-modern-rest>`_
  provides up-to-date documentation for LLMs; you can use it as a context
  source in supported tools.

- **DeepWiki** — Learn ``django-modern-rest`` with
  `DeepWiki <https://deepwiki.com/wemake-services/django-modern-rest>`_,
  which uses our docs for AI-assisted learning and exploration.


Supported use cases
-------------------
We support these workflows with LLMs:

.. note::
  LLM-generated output is not guaranteed to fully match your contract.
  Always review and validate generated routes/schemas, media types,
  status codes, headers, authentication/throttling, and error semantics
  before production use.

- **Learning** — Use `DeepWiki <https://deepwiki.com/wemake-services/django-modern-rest>`_
  for AI-assisted exploration.

- **Spec-first / boilerplate from OpenAPI** — Use :doc:`spec-first generation <../ai/spec-first>`
  with agent skill `dmr-openapi-skeleton <https://github.com/wemake-services/django-modern-rest/tree/master/.agents/skills/dmr-openapi-skeleton>`_
  to generate a runnable skeleton from a single ``openapi.json`` (OpenAPI ``3.1+``).

- **Migration from Django Ninja** — Use :doc:`Django Ninja migration <../ai/dmr-from-ninja>`
  with agent skill `dmr-from-django-ninja <https://github.com/wemake-services/django-modern-rest/tree/master/.agents/skills/dmr-from-django-ninja>`_
  to migrate the transport layer incrementally.

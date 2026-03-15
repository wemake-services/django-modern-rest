LLM and AI support
============================

If you use AI coding assistants (Cursor, GitHub Copilot, ChatGPT, etc.)
you can give them up-to-date documentation about ``django-modern-rest``.
This page describes the formats we provide and the use cases we officially
support.


Documentation for AI context
----------------------------

Use the following URLs to supply documentation to your LLM or RAG pipeline.
Choose the format that fits your context window and workflow.

**Index (llms.txt)** — Structured index with links to sections and topics.
Use when the assistant has a limited context window or you want to point
it to specific pages.

.. code-block:: text

   https://django-modern-rest.readthedocs.io/llms.txt

**Full documentation (llms-full.txt)** — Complete documentation in a single
plain-text file. Use when the model supports large context or you need the
entire reference in one place.

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

- **Learning** — Use DeepWiki (see above) to explore the framework with
  AI assistance.

- **Spec-first / boilerplate from OpenAPI** — LLMs can help generate a
  :doc:`working project boilerplate <../openapi/spec-first>` (models,
  controllers, etc.) from a single ``openapi.json`` file (Spec First
  approach). Note that LLM-generated code cannot guarantee strict
  compliance; review and test the output.

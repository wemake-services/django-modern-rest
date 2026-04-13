Getting started
===============


Installation
------------

Works for:

- CPython 3.11+ or PyPy 3.11+
- Django 4.2+

.. tabs::

  .. tab:: :iconify:`material-icon-theme:uv` uv

    .. code-block:: bash

      uv add django-modern-rest

  .. tab:: :iconify:`devicon:poetry` poetry

    .. code-block:: bash

      poetry add django-modern-rest

  .. tab:: :iconify:`devicon:pypi` pip

    .. code-block:: bash

      pip install django-modern-rest


Extras for different serializers:

- ``'django-modern-rest[pydantic]'`` for ``pydantic`` support
- ``'django-modern-rest[attrs]'`` for ``attrs`` support
- ``'django-modern-rest[msgspec]'`` for ``msgspec`` support
  and the fastest ``json`` parsing

Extras for different features:

- ``'django-modern-rest[jwt]'`` for
  `jwt <https://pyjwt.readthedocs.io>`_ support
- ``'django-modern-rest[openapi]'`` for
  `OpenAPI schema validation <https://github.com/python-openapi/openapi-spec-validator>`_
  and better examples generation


.. important::

  We highly recommend to always install
  `msgspec <https://github.com/jcrist/msgspec>`_, even when using just
  `pydantic <https://github.com/pydantic/pydantic>`_ for APIs,
  because we use ``msgspec`` to parse ``json``, when it is available,
  since it is `the fastest <https://jcristharif.com/msgspec/benchmarks.html>`_
  library out there for this task.

  We also recommend to always install
  `django-stubs <https://github.com/typeddjango/django-stubs>`_
  for typing the Django itself.

.. note::

  You don't need to add ``'dmr'`` to the ``INSTALLED_APPS``,
  unless you want to serve static files for the OpenAPI.


LLMs support
------------

Are you using AI for assisted coding?
We got you covered, use these files for context to make sure that the LLM
knows our framework:

- https://django-modern-rest.readthedocs.io/llms.txt
  for indexes with links to different pages and topics
- https://django-modern-rest.readthedocs.io/llms-full.txt
  for complete docs

We also support
`Context7 <https://context7.com/wemake-services/django-modern-rest>`_
for up-to-date docs for the LLMs.

Use cases we officially support:

- Learning ``django-modern-rest`` with the help
  of `DeepWiki <https://deepwiki.com/wemake-services/django-modern-rest>`_
- AI-guided migrations for any API changes.
  We break something? We provide a prompt for you, so you can automatically
  upgrade to a newer version using an AI tool of your choice

We support several custom agent skills:

- ``$dmr`` to enforce ``django-modern-rest`` best practices
  with fast and secure approaches
- ``$dmr-openapi-skeleton`` to generate
  a :doc:`working project boilerplate <ai/spec-first>`
  from a single ``openapi.json`` file (the "Spec First" approach)
- ``$dmr-from-django-ninja`` to help with
  :doc:`migrating from Django Ninja <ai/dmr-from-ninja>`
- ``$dmr-from-drf`` to help with
  :doc:`migrating from Django REST Framework <ai/dmr-from-drf>`


Showcase
--------

Let's see the basics and learn how to use ``dmr`` in a single example:

.. tabs::

  .. tab:: msgspec

    We support :class:`msgspec.Struct`
    via :class:`~dmr.plugins.msgspec.MsgspecSerializer`.

    .. literalinclude:: /examples/getting_started/msgspec_controller.py
      :caption: views.py
      :language: python
      :linenos:

  .. tab:: pydantic

    We support :class:`pydantic.BaseModel`
    via :class:`~dmr.plugins.pydantic.PydanticSerializer`.

    .. tip::

      If you only use ``json`` :doc:`parsers and renderers <negotiation>`,
      it would be faster to use
      :class:`~dmr.plugins.pydantic.PydanticFastSerializer` instead.

    .. literalinclude:: /examples/getting_started/pydantic_controller.py
      :caption: views.py
      :language: python
      :linenos:

  .. tab:: attrs

    We support :func:`attrs.define`
    via :class:`~dmr.plugins.msgspec.MsgspecSerializer`.
    See `msgspec docs <https://jcristharif.com/msgspec/supported-types.html#attrs>`_
    on ``attrs`` support.

    .. literalinclude:: /examples/getting_started/attrs_controller.py
      :caption: views.py
      :language: python
      :linenos:

  .. tab:: dataclasses

    We support :func:`dataclasses.dataclass` via both
    :class:`~dmr.plugins.msgspec.MsgspecSerializer`
    and :class:`~dmr.plugins.pydantic.PydanticSerializer`.

    .. literalinclude:: /examples/getting_started/dataclasses_controller.py
      :caption: views.py
      :language: python
      :linenos:

  .. tab:: TypedDict

    We support :class:`typing.TypedDict` via both
    :class:`~dmr.plugins.msgspec.MsgspecSerializer`
    and :class:`~dmr.plugins.pydantic.PydanticSerializer`.

    .. literalinclude:: /examples/getting_started/typed_dict_controller.py
      :caption: views.py
      :language: python
      :linenos:

  .. tab:: NamedTuple

    We support :class:`typing.NamedTuple`
    via :class:`~dmr.plugins.pydantic.PydanticSerializer`.

    .. literalinclude:: /examples/getting_started/named_tuple_controller.py
      :caption: views.py
      :language: python
      :linenos:

.. important::

  You can choose a serializer per controller, which will give you
  the freedom to choose the best serializer and model for the job.
  ``msgspec`` gives you more speed,
  while ``pydantic`` gives you more flexibility.


In this example:

1. We defined regular ``pydantic``, ``msgspec``, or whatever models
   that we will use for our API
2. We added two component parsers: one for request's
   :data:`~dmr.components.Body` and one
   for :data:`~dmr.components.Headers`
   which will parse them into the typed models
   that we pass to these components as type parameters
3. Next we created
   a :class:`~dmr.controller.Controller` class
   with :class:`~dmr.plugins.pydantic.PydanticSerializer`
   or :class:`~dmr.plugins.msgspec.MsgspecSerializer`
   to serialize input and output data for us
4. We also defined ``post`` API endpoint and returned
   a simple model response from it, it will be automatically
   transformed into :class:`django.http.HttpResponse` instance
   by ``django-modern-rest``

Now, let's add our controller to the list of URLs:

.. literalinclude:: /examples/getting_started/urls.py
  :caption: urls.py
  :language: python
  :linenos:

Your first ``django-modern-rest`` API is ready.
Next, you can learn:

- How to generate OpenAPI schema
- How to handle errors
- How to customize controllers and endpoints


Full example
------------

If you were ever told that Django is too big and complicated,
that was misleading, to say the least.

Here's a :doc:`single-file application <structure/micro-framework>`
that looks pretty much the same as any other micro-framework, like:
FastAPI, Litestar, or Flask.

.. literalinclude:: /examples/structure/micro_framework/single_file_asgi.py
   :language: python
   :linenos:

You can copy it by clicking "Copy" in the right upper corner of the example,
it shows up on hovering the code example. Paste it as ``example.py``,
install the ``django-modern-rest`` and run it with:

.. tabs::

    .. tab:: :iconify:`material-icon-theme:uv` uv

        .. code-block:: bash

            uv run example.py runserver

    .. tab:: :iconify:`devicon:poetry` poetry

        .. code-block:: bash

            poetry run python example.py runserver

    .. tab:: :iconify:`devicon:pypi` pip

        .. code-block:: bash

            python example.py runserver

Your API is now live:

- ``POST`` http://localhost:8000/api/user/ — create a user

And then visit https://localhost:8000/docs/swagger/ for the interactive docs.

.. image:: /_static/images/swagger.png
   :alt: Swagger view
   :align: center

That's it, enjoy your new project!


But, this is too simple for my use-case!
----------------------------------------

What is great about Django is that it scales.
You can start with a single file app and scale it up to a full
featured monolith with strict context boundaries, DDD, reusable apps, etc.

We recommend starting new big projects with
https://github.com/wemake-services/wemake-django-template

It is strict, security-first, battle-proven, highload-tested boilerplate
for real apps of the modern age.


Next up
-------

.. grid:: 1 1 2 2
    :class-row: surface
    :padding: 0
    :gutter: 2

    .. grid-item-card:: :octicon:`rocket` Core Concepts
      :link: core-concepts
      :link-type: doc

      Learn the fundamentals.

    .. grid-item-card:: :octicon:`gear` Configuration
      :link: configuration
      :link-type: doc

      Learn how to configure ``django-modern-rest``.

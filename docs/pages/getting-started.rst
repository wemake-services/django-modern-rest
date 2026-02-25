Getting started
===============


Installation
------------

Works for:

- Python 3.11+
- Django 5.2+

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
- ``'django-modern-rest[msgspec]'`` for ``msgspec`` support
  and the fastest ``json`` parsing

Extras for different features:

- ``'django-modern-rest[jwt]'`` for
  `jwt <https://pyjwt.readthedocs.io>`_ support


.. important::

  We highly recommend to always install
  `msgspec <https://github.com/jcrist/msgspec>`_, even when using just
  `pydantic <https://github.com/pydantic/pydantic>`_ for APIs,
  because we use ``msgspec`` to parse ``json``, when it is available,
  since it is `the fastest <https://jcristharif.com/msgspec/benchmarks.html>`_
  library out there for this task.

.. note::

  You don't need to add ``'django-modern-rest'`` to the ``INSTALLED_APPS``,
  unless you want to serve static files for the OpenAPI.


Showcase
--------

Quick example:

.. tabs::

    .. tab:: msgspec

      .. literalinclude:: /examples/getting_started/msgspec_controller.py
        :caption: views.py
        :language: python
        :linenos:
        :emphasize-lines: 6, 22

    .. tab:: pydantic

      .. literalinclude:: /examples/getting_started/pydantic_controller.py
        :caption: views.py
        :language: python
        :linenos:
        :emphasize-lines: 6, 22

In this example:

1. We defined regular ``pydantic`` and ``msgspec`` models
   that we will use for our API
2. We added two component parsers: one for request's
   :class:`~dmr.components.Body` and one
   for :class:`~dmr.components.Headers`
   which will parse them into typed models
   (:class:`pydantic.BaseModel` or :class:`msgspec.Struct` based) that we pass
   to these components as type parameters
3. You can see how we created
   a :class:`~dmr.controller.Controller` class
   with :class:`~dmr.plugins.pydantic.PydanticSerializer`
   or :class:`~dmr.plugins.msgspec.MsgspecSerializer`
4. And how we defined ``post`` endpoint and returned
   a simple model response from it, it will automatically
   transformed into :class:`django.http.HttpResponse` instance by the framework

Now, let's add our API to the list of URLs:

.. literalinclude:: /examples/getting_started/urls.py
  :caption: urls.py
  :language: python
  :linenos:

Basically - that's it! Your first ``django-modern-rest`` API is ready.
Next, you can learn:

- How to generate OpenAPI schema
- How to handle errors
- How to customize controllers and endpoints


But, Django is complicated!
---------------------------

No, it is not :)

Here's a :doc:`single-file application <structure/micro-framework>`
that looks pretty much the same as any other micro-framework, like:
FastAPI, Litestar, or Flask.

.. literalinclude:: /examples/structure/micro_framework/single_file_asgi.py
   :language: python
   :linenos:

You can copy it by clicking "Copy" in the right upper corner of the example,
it shows up on hovering the code example. Paste it as ``example.py``,
install the ``django-modern-rest`` and run it with:

.. code-block:: bash

  python example.py runserver

And then visit: https://localhost:8000/docs/swagger

That's it, enjoy your new project!


But, this is too simple for my use-case!
----------------------------------------

What is great about Django is that it scales.
You can start with a single file app and scale it up to a full
featured monolith with scrict context boundaries, DDD, reusable apps, etc.

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

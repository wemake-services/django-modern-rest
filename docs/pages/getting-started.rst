Getting started
===============


Installation
------------

Works for:

- Python 3.11+
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


Available extras:

- ``'django-modern-rest[pydantic]'`` for ``pydantic`` support
- ``'django-modern-rest[msgspec]'`` for ``msgspec`` support
  and the fastest ``json`` parsing


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


Project template
----------------

Jump start your new ``django-modern-rest`` project with
`wemake-django-template <https://github.com/wemake-services/wemake-django-template>`_!


Showcase
--------

Quick example:

.. tabs::

    .. tab:: msgspec

      .. literalinclude:: /examples/getting_started/msgspec_controller.py
        :caption: views.py
        :linenos:
        :emphasize-lines: 7, 24

    .. tab:: pydantic

      .. literalinclude:: /examples/getting_started/pydantic_controller.py
        :caption: views.py
        :linenos:
        :emphasize-lines: 7, 24

In this example:

1. We defined regular ``pydantic`` and ``msgspec`` models
   that we will use for our API
2. We added two component parsers: one for request's
   :class:`~django_modern_rest.components.Body` and one
   for :class:`~django_modern_rest.components.Headers`
   which will parse them into typed models
   (:class:`pydantic.BaseModel` or :class:`msgspec.Struct` based) that we pass
   to these components as type parameters
3. You can see how we created
   a :class:`~django_modern_rest.controller.Controller` class
   with :class:`~django_modern_rest.plugins.pydantic.PydanticSerializer`
   or :class:`~django_modern_rest.plugins.msgspec.MsgspecSerializer`
4. And how we defined ``post`` endpoint and returned
   a simple model response from it, it will automatically
   transformed into :class:`django.http.HttpResponse` instance by the framework

Now, let's add our API to the list of URLs:

.. literalinclude:: /examples/getting_started/urls.py
  :caption: urls.py
  :linenos:
  :lines: 3-

Basically - that's it! Your first ``django-modern-rest`` API is ready.
Next, you can learn:

- How to generate OpenAPI schema
- How to handle errors
- How to customize controllers and endpoints


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

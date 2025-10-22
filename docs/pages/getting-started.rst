Getting Started
===============


Installation
------------


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

  I highly recommend to always install
  `msgspec <https://github.com/jcrist/msgspec>`_, even when using just
  `pydantic <https://github.com/pydantic/pydantic>`_ for APIs,
  because we use ``msgspec`` to parse ``json``, when it is available,
  since it is `the fastest <https://jcristharif.com/msgspec/benchmarks.html>`_
  library out there for this task.

.. note::

  You don't need to add ``django-modern-rest`` to the list of installed apps.


Showcase
--------

Quick example:

.. tabs::

    .. tab:: msgspec

      .. literalinclude:: /examples/getting_started/msgspec_controller.py
        :linenos:
        :emphasize-lines: 6, 22

    .. tab:: pydantic

      .. literalinclude:: /examples/getting_started/pydantic_controller.py
        :linenos:
        :emphasize-lines: 6, 22

In this example:

1. We defined regular ``pydantic`` and ``msgspec`` models
   that we will use for our API
2. We added two component parsers one for request's
   :class:`~django_modern_rest.components.Body` and one
   for :class:`~django_modern_rest.components.Headers`
   which will parse them into a typed model
3. You can see how we created
   a :class:`~django_modern_rest.controller.Controller` class
   with ``pydantic`` and ``msgspec`` serializers
4. How we defined ``post`` endpoint and returned
   a simple model response from it, it will automatically
   transformed into ``HttpResponse`` instance by the framework

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

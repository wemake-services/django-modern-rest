Your first API
==============

.. attention::
   Before starting this tutorial, make sure you have completed
   the :doc:`../getting-started/installation` guide and verified
   that your project runs successfully.

**Prerequisites:** A Django project with ``django-modern-rest``.
We'll add one controller and wire it in your URLs.

**What you'll build:** A ``POST`` endpoint that accepts a JSON body and
a header, and returns a typed JSON response.


Step 1: Define models
---------------------

Define the request and response as ``pydantic`` or ``msgspec`` models.
These will be used by the controller for parsing and serialization.

.. tabs::

    .. tab:: msgspec

      .. literalinclude:: /examples/getting_started/msgspec_controller.py
        :caption: views.py
        :language: python
        :linenos:
        :lines: 1-16
        :no-imports-spoiler:

    .. tab:: pydantic

      .. literalinclude:: /examples/getting_started/pydantic_controller.py
        :caption: views.py
        :language: python
        :linenos:
        :lines: 1-16
        :no-imports-spoiler:


Step 2: Create the controller
-----------------------------

Add a :class:`~dmr.controller.Controller` with :class:`~dmr.components.Body`
and :class:`~dmr.components.Headers` so the request body and headers are
parsed into the models above. Use :class:`~dmr.plugins.pydantic.PydanticSerializer`
or :class:`~dmr.plugins.msgspec.MsgspecSerializer` for serialization.
Define a ``post`` method that returns a model instance; ``dmr`` will turn
it into a :class:`django.http.HttpResponse`.

.. tabs::

    .. tab:: msgspec

      .. literalinclude:: /examples/getting_started/msgspec_controller.py
        :caption: views.py
        :language: python
        :linenos:
        :emphasize-lines: 6, 26

    .. tab:: pydantic

      .. literalinclude:: /examples/getting_started/pydantic_controller.py
        :caption: views.py
        :language: python
        :linenos:
        :emphasize-lines: 6, 26


Step 3: Wire the controller in URLs
-----------------------------------

In your project's root ``urls.py``, use :class:`~dmr.routing.Router` and
:func:`~dmr.routing.path` to register the controller. Replace the import
with your app's views module (e.g. ``from myapp.views import UserController``).
See :doc:`../routing` for how routing works.

.. literalinclude:: /examples/getting_started/urls.py
  :caption: urls.py
  :language: python
  :linenos:

Your first ``django-modern-rest`` API is ready. Run the server and try
``POST /api/user/`` with a JSON body and the ``X-API-Consumer`` header.


Next steps
----------

Once you've completed a tutorial, explore these guides and reference:

.. grid:: 1 1 2 2
    :class-row: surface
    :padding: 0
    :gutter: 2

    .. grid-item-card:: :octicon:`tools` Controllers and endpoints
      :link: ../using-controller
      :link-type: doc

      Learn how to customize controllers and endpoints.

    .. grid-item-card:: :octicon:`alert` Error handling
      :link: ../error-handling
      :link-type: doc

      Handle validation errors and exceptions.

    .. grid-item-card:: :octicon:`git-branch` Routing
      :link: ../routing
      :link-type: doc

      Understand how ``Router`` and ``path`` work.

    .. grid-item-card:: :octicon:`file-badge` OpenAPI
      :link: ../openapi/openapi
      :link-type: doc

      Generate and explore your OpenAPI schema.

.. tip::

  To discover more projects, templates, and tools built with
  ``django-modern-rest``, check out the curated
  `awesome-django-modern-rest <https://github.com/kondratevdev/awesome-django-modern-rest>`_
  list.

For fundamentals and configuration:

.. grid:: 1 1 2 2
    :class-row: surface
    :padding: 0
    :gutter: 2

    .. grid-item-card:: :octicon:`rocket` Core Concepts
      :link: ../core-concepts
      :link-type: doc

      Learn the fundamentals.

    .. grid-item-card:: :octicon:`gear` Configuration
      :link: ../configuration
      :link-type: doc

      Learn how to configure ``django-modern-rest``.

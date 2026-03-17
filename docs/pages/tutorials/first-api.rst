Tutorial 1: Your first API
==========================

**Prerequisites:** A Django project with ``django-modern-rest`` installed
(see :doc:`../getting-started/installation`). We'll add one controller
and wire it in your URLs.

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

- :doc:`How routing and Router work <../routing>`
- :doc:`How to customize controllers and endpoints <../using-controller>`
- :doc:`How to handle errors <../error-handling>`
- :doc:`How to generate OpenAPI schema <../openapi/openapi>`

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

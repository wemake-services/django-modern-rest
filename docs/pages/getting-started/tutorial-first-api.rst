Tutorial 1: Your first API
==========================

**Prerequisites:** A Django project with ``django-modern-rest`` installed
(see :doc:`installation`). We'll add one controller and wire it in your URLs.

**What you'll build:** A ``POST`` endpoint that accepts a JSON body and
a header, and returns a typed JSON response.

Put the code below in your app's ``views.py`` (create the file if needed).
Use either the msgspec or pydantic; the structure is the same.


Step 1: Define models
---------------------

Define the request/response and header shapes as plain ``pydantic`` or
``msgspec`` models. These will be used by the controller for parsing and
serialization.

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

See :ref:`getting-started-next-steps` for guides on routing, controllers,
error handling, and OpenAPI. Or continue with :doc:`tutorial-single-file`
for a single-file app example.

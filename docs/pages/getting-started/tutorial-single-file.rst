Tutorial 2: Single-file app
===========================

**Prerequisites:** ``django-modern-rest`` installed (see :doc:`installation`).
No Django project required, everything runs from one file.

**What you'll build:** A single-file API with one ``POST`` endpoint and
interactive Swagger docs. Same ideas as :doc:`tutorial-first-api`, but without
``django-admin startproject``. Great for trying DMR or small services.

Save the code below as ``example.py`` (or any name). Use either pydantic
(as shown) or msgspec; the structure is the same.


Step 1: Configure Django in one file
------------------------------------

We use :func:`django.conf.settings.configure` so Django runs without a
project. The app serves OpenAPI UI, so we need ``'dmr'`` and
``django.contrib.staticfiles`` in ``INSTALLED_APPS``.

.. literalinclude:: /examples/structure/micro_framework/single_file_asgi.py
  :caption: example.py
  :language: python
  :linenos:
  :lines: 1-35
  :no-imports-spoiler:
  :no-run:


Step 2: Define models and controller
------------------------------------

Define the request and response model and a :class:`~dmr.controller.Controller`
with :class:`~dmr.components.Body`. This is the same pattern as in
:doc:`tutorial-first-api`, just in the same file.

.. literalinclude:: /examples/structure/micro_framework/single_file_asgi.py
  :caption: example.py
  :language: python
  :linenos:
  :lines: 38-51
  :no-imports-spoiler:
  :no-run:


Step 3: Router, schema, and URL patterns
----------------------------------------

Build a :class:`~dmr.routing.Router`, generate the OpenAPI schema with
:func:`~dmr.openapi.build_schema`, and expose the API and Swagger UI
on :file:`urlpatterns`.

.. literalinclude:: /examples/structure/micro_framework/single_file_asgi.py
  :caption: example.py
  :language: python
  :linenos:
  :lines: 54-71
  :no-imports-spoiler:
  :no-run:


Step 4: Run the app
-------------------

Use Django's so you can run ``python example.py runserver``.
Install ``django-modern-rest`` first if you haven't (see :doc:`installation`).

.. literalinclude:: /examples/structure/micro_framework/single_file_asgi.py
  :caption: example.py
  :language: python
  :linenos:
  :lines: 68-71
  :no-imports-spoiler:

Then start the server:

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


Your API is now live
--------------------

- ``POST`` http://localhost:8000/api/user/ — create a user
- http://localhost:8000/docs/swagger/ — interactive API docs

.. image:: /_static/images/swagger.png
  :alt: Swagger view
  :align: center

For more on this style, see :doc:`../structure/micro-framework`.


But this is too simple for my use case!
---------------------------------------

Django scales. You can grow from a single file to a full monolith with
clear boundaries, DDD, and reusable apps. We recommend starting larger
projects with the `wemake-django-template
<https://github.com/wemake-services/wemake-django-template>`_: strict,
security-first, battle-tested boilerplate.


Next steps
----------

See :ref:`getting-started-next-steps` for guides on routing, controllers,
error handling, and OpenAPI. For the single-file style in depth, see
:doc:`../structure/micro-framework`. Or try :doc:`tutorial-first-api` in a
full Django project.

Or explore:

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

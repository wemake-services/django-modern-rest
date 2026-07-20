Micro-framework out of Django
=============================

Single file Django
------------------

You don't need microframeworks to build small APIs, because
Django is a microframework itself. With the only difference: it scales!

.. literalinclude:: /examples/structure/micro_framework/single_file_asgi.py
   :language: python
   :linenos:


µDjango style
-------------

`µDjango <https://github.com/pauloxnet/uDjango>`_ by Paolo Melchiorre
is a demo of exactly this idea: a whole Django app in a single file,
exposed as a plain ``ASGIHandler``
and served by any ASGI server.

It is not a package you install, so there is nothing to integrate with.
It is a shape your own file can take, and ``django-modern-rest``
fits into it without any glue code:

.. literalinclude:: /examples/structure/micro_framework/udjango_style_asgi.py
   :language: python
   :linenos:

Run it with any ASGI server:

.. code:: bash

  uvicorn udjango_style_asgi:app --reload

.. note::

  µDjango itself is explicitly a demonstration project
  and is not meant for production.
  The pattern it shows, however, is just regular Django.


nanodjango
----------

`nanodjango <https://github.com/radiac/nanodjango>`_ is a real package
that wraps the single file idea into a Flask-like API:
it configures the settings for you and collects urls via decorators.

Two things are needed to use it with ``django-modern-rest``:

1. Add ``dmr`` to ``EXTRA_APPS``, so its templates and static files
   are found. ``EXTRA_APPS`` is appended to nanodjango's
   own ``INSTALLED_APPS`` defaults
2. Mount a :class:`~dmr.routing.Router` with ``app.path()``
   called as a *function* with :func:`~django.urls.include`,
   not as a decorator

.. literalinclude:: /examples/structure/micro_framework/nanodjango_app.py
   :language: python
   :linenos:

Single controllers can also be registered with the decorator form,
since ``app.path()`` handles class-based views:

.. code:: python

  @app.path('user/')
  class UserController(Controller[PydanticSerializer]): ...

But you lose the OpenAPI schema this way,
because it is built from a :class:`~dmr.routing.Router`.

.. warning::

  ``app.run()`` picks ``uvicorn`` over Django's ``runserver``
  only when nanodjango detects async views, and it detects them
  by inspecting the functions passed to its own decorators.
  Controllers mounted via :func:`~django.urls.include` are invisible
  to that check, so an app with only async controllers
  will still be served over WSGI.

  Async views keep working, Django adapts them.
  But to actually serve them over ASGI, run the app directly:

  .. code:: bash

    uvicorn nanodjango_app:app.asgi --interface asgi3

  Note that ``app.asgi`` serves in nanodjango's production mode,
  where static files are served by ``whitenoise`` from ``STATIC_ROOT``.
  Run ``app.manage(['collectstatic'])`` once beforehand,
  otherwise the Swagger UI assets will 404.


Scaling it for real projects
----------------------------

However, all projects tend to grow while they are alive.
Microframeworks handle the scale poorly, because
they are not designed for this task.

We recommend using https://github.com/wemake-services/wemake-django-template
to set up production ready Django boilerplate code with all the best practices.

It can handle any scale!

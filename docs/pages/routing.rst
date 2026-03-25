Routing
=======

Our :term:`Controller` is built without knowing anything
about its future URL. Why so?

1. Because Django already has an amazing URL
   `routing system <https://docs.djangoproject.com/en/5.2/topics/http/urls/>`_
   and we don't need to duplicate it
2. Because all controllers might be used in multiple URLs,
   for example in ``api/v1`` and ``api/v2``. Our way allows any customizations

.. note::

  If you want to parse path parameters, see :doc:`components/path`
  and :class:`dmr.components.Path`.

However, there are several rules (and validation errors)
attached to this behaviour:

1. Controllers to be composed can't have duplicate endpoints, otherwise,
   it would be not clear which endpoint from which controller needs to called.
   This includes :ref:`meta <meta>` method for ``OPTION`` HTTP calls as well
2. All controllers have to be either sync or async,
   otherwise it would be hard to run them
3. Controllers must have the same :term:`serializer`,
   because otherwise parsing can probably error out
4. Controllers to be composed must have at least one endpoint


Handling 404 errors
-------------------

By default, Django returns HTML 404 pages.
This is not what we want for API endpoints.
Instead, we want to return API responses with proper error structure and
content negotiation (e.g. JSON or XML based on the ``Accept`` header).

But, we still want HTML 404 pages for non API views.

.. important::

  Overriding :data:`django.conf.urls.handler404` has no effect
  while ``DEBUG = True`` is set.

  This is how Django behaves:
  https://docs.djangoproject.com/en/stable/ref/views/#the-404-page-not-found-view

To achieve this, you can use
:func:`~dmr.routing.build_404_handler` helper.
It creates a handler that returns API-style 404 responses for specific path
prefixes (using the same serializer and renderers as your API), and falls back
to Django's default handler for everything else.

Here is how you can use it in your root ``urls.py``
(in your `ROOT_URLCONF <https://docs.djangoproject.com/en/stable/ref/settings/#root-urlconf>`_):

.. literalinclude:: /examples/routing/handler404.py
  :caption: urls.py
  :language: python
  :linenos:

This returns json responses for ``api/`` prefixed paths.
But, will still return html responses for any other path.


.. _handler500:

Handling 500 errors
-------------------

By default, Django returns HTML 500 pages.
This is not what we want for API endpoints.
Instead, we want to return API responses with proper error structure and
content negotiation (e.g. JSON or XML based on the ``Accept`` header).

But, we still want HTML 500 pages for non API views.

.. important::

  Overriding :data:`django.conf.urls.handler500` has no effect
  while ``DEBUG = True`` is set.

  This is how Django behaves:
  https://docs.djangoproject.com/en/stable/ref/views/#the-500-server-error-view

To achieve this, you can use
:func:`~dmr.routing.build_500_handler` helper.
It creates a handler that returns API-style 500 responses for specific path
prefixes (using the same serializer and renderers as your API), and falls back
to Django's default handler for everything else.

Here is how you can use it in your root ``urls.py``
(in your `ROOT_URLCONF <https://docs.djangoproject.com/en/stable/ref/settings/#root-urlconf>`_):

.. literalinclude:: /examples/routing/handler500.py
  :caption: views.py
  :language: python
  :linenos:

.. seealso::

  :doc:`error-handling` if you want to learn how to handle
  different errors on different levels and fix these ``500``
  exceptions.


Optimized URL Routing
---------------------

``django-modern-rest`` provides
an optimized :func:`dmr.routing.path` function
that is a **drop-in replacement** for Django's :func:`django.urls.path`.

The custom implementation uses prefix-based pattern matching
for faster routing. Instead of immediately running Django's regex engine
on every request, it performs a quick prefix check first.

Performance Impact
~~~~~~~~~~~~~~~~~~

Benchmark results on MacBook Pro M4 Pro:

- **Best case**: 9% faster (match found in first few URL patterns)
- **Average case**: 13% faster (match found in middle of URL patterns list)
- **Worst case**: 31% faster (404 Not Found, all patterns checked)

The prefix-based optimization dramatically reduces regex operations:

- **Static routes**: Simple string comparison (no regex at all)
- **Dynamic routes**: Regex only runs when prefix matches
- **Failed matches**: Eliminated in one operation (startswith check)

This is especially beneficial for applications with:

- Large number of routes
- High traffic

Migration
~~~~~~~~~

Simply replace Django's ``path`` with :func:`dmr.routing.path`:

.. code:: python

    # Instead of ``from django.urls import path``:
    from dmr.routing import path
    from django.urls import include

    urlpatterns = [
        path('api/', include('myapp.urls')),
    ]

This is a drop-in replacement with no API changes required.

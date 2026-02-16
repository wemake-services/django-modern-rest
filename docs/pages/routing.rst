Routing
=======

Our :term:`Controller` is built without knowing anything
about its future URL. Why so?

1. Because Django already has an amazing URL
   `routing system <https://docs.djangoproject.com/en/5.2/topics/http/urls/>`_
   and we don't need to duplicate it
2. Because all controllers might be used in multiple URLs,
   for example in ``api/v1`` and ``api/v2``. Our way allows any customizations


To register a controller what you do is:

So, how do you compose different controllers with different parsing
behaviours into a single URL? For this we use
:func:`~django_modern_rest.routing.compose_blueprints` function:


But, no second validation ever happens, because we respect your time!

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

Controllers in ``django-modern-rest`` are not built
to be extended, but composed!


.. _composed-meta:

Handling meta endpoint
----------------------

When using :func:`~django_modern_rest.routing.compose_blueprints`,
duplicate ``meta`` methods will be a import-time error. To solve this,
remove ``meta`` method from individual controllers
and use ``meta_mixin=`` keyword parameter to ``compose_blueprints``.

Example:

.. code:: python

  from django_modern_rest import AsyncMetaMixin

  composed = compose_blueprints(
      UserPut,
      UserPatch,
      # If controllers are sync, use `MetaMixin`
      meta_mixin=AsyncMetaMixin,
  )

This will create an ``async def meta`` endpoint in the composed controller.
All methods from ``UserPut`` and ``UserPatch`` will be listed
in the response's ``Allow`` header.

.. warning::

  As usually, we validate that the resulting ``Controller``
  won't have a mix of sync and async endpoints.


Optimized URL Routing
---------------------

``django-modern-rest`` provides
an optimized :func:`~django_modern_rest.routing.path` function
that is a **drop-in replacement** for Django's :func:`django.urls.path`.

What's Changed?
^^^^^^^^^^^^^^^

The custom implementation uses prefix-based pattern matching
for faster routing. Instead of immediately running Django's regex engine
on every request, it performs a quick prefix check first.

How It Works
^^^^^^^^^^^^

The optimizer works in two stages:

**At router creation time:**

1. Extract static prefix from route (everything before first ``<``)

**On every request:**

2. Prefix Check: fast ``str.startswith()`` comparison
3. Pattern Resolution: only if prefix matches, run Django's
   full pattern matching to extract parameters

Example Workflow
~~~~~~~~~~~~~~~~

Let's say you have this URL configuration:

.. literalinclude:: /examples/routing/simple_router.py
  :caption: urls.py
  :language: python

.. code-block::
  :caption: Traditional Django ``path()`` behavior

    Request: GET /api/v1/comments/

    Django matches ALL patterns:
    ❌ Try 'api/v1/users/'
        Run regex... no match
    ❌ Try 'api/v1/posts/'
        Run regex... no match
    ❌ Try 'api/v1/users/<int:id>/'
        Run regex... no match
    ❌ 404 Not Found

.. code-block::
  :caption: Our optimized ``path()`` behavior

    Request: GET /api/v1/comments/

    Django-modern-rest matches:
    ✓ Check prefix 'api/v1/users/'
        'api/v1/comments/'.startswith('api/v1/users/') = False
        Skip regex entirely

    ✓ Check prefix 'api/v1/posts/'
        'api/v1/comments/'.startswith('api/v1/posts/') = False
        Skip regex entirely

    ✓ Check prefix 'api/v1/users/'
        'api/v1/comments/'.startswith('api/v1/users/') = False
        Skip regex entirely

    ❌ 404 Not Found

The key optimization: regex is only executed if the prefix matches!

Static Routes
~~~~~~~~~~~~~

Zero regex!

For routes without parameters, the optimizer uses simple string comparison:

.. code:: python

    path('api/users/', view)

Matching flow::

    Request: GET /api/users/

    Match 'api/users/':
        path == 'api/users/' ? Yes ✓
        Return immediately (no regex at all!)

Dynamic Routes (Prefix Pre-filtering)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For routes with parameters, prefix checking filters out most failed matches:

.. code:: python

    path('api/v1/users/<int:id>/', view)

Matching flow::

    Request: GET /api/v1/users/123/

    Match 'api/v1/users/<int:id>/':
        'api/v1/users/123/'.startswith('api/v1/users/') ? Yes ✓
        Now run Django's regex to extract 'id'
        Extract: id = 123
        Return match

    Request: GET /api/v1/posts/123/

    Match 'api/v1/users/<int:id>/':
        'api/v1/posts/123/'.startswith('api/v1/users/') ? No ✓
        Skip regex entirely, try next pattern

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

Simply replace Django's ``path`` with ``django_modern_rest.routing.path``:

.. code:: python

    # Instead of ``from django.urls import path``:
    from django_modern_rest.routing import path

    urlpatterns = [
        path('api/', include('myapp.urls')),
    ]

This is a drop-in replacement with no API changes required.

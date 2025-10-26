Routing
=======

Our :term:`Controller` is built without knowing anything
about its future URL. Why so?

1. Because Django already has an amazing URL
   `routing system <https://docs.djangoproject.com/en/5.2/topics/http/urls/>`_
   and we don't need to duplicate it
2. Because all controllers might be used in multiple URLs,
   for example in ``api/v1`` and ``api/v2``. Our way allows any customizations

So, how do you compose different controllers with different parsing
behaviours into a single URL? For this we use
:func:`~django_modern_rest.routing.compose_controllers` function:

.. code:: python

  from django.urls import include
  from django_modern_rest import Router, compose_controllers, path

  router = Router([
    path(
        'user/',
        compose_controllers(
            views.UserCreateController,
            views.UserListController,
            # Can compose as many controllers as you need!
        ).as_view(),
        name='users',
    ),
  ]

  urlpatterns = [
      path('api/', include((router.urls, 'server'), namespace='api')),
  ]

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

When using :func:`~django_modern_rest.routing.compose_controllers`,
duplicate ``meta`` methods will be a import-time error. To solve this,
remove ``meta`` method from individual controllers
and use ``meta_mixin=`` keyword parameter to ``compose_controllers``.

Example:

.. code:: python

  from django_modern_rest import AsyncMetaMixin

  composed = compose_controllers(
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

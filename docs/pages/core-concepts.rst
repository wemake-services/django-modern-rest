Core Concepts
=============

To learn ``django-modern-rest`` you have to learn just a couple of things:

.. glossary::

  Endpoint
    :class:`~django_modern_rest.endpoint.Endpoint`
    is a single API route. It is defined
    by its name – HTTP method – and its :term:`Metadata`, what response schema
    it returns, what status codes it can return, etc.

  Controller
    :class:`~django_modern_rest.controller.Controller`
    is a collection of one or more :term:`endpoints <Endpoint>`.
    Controller is defined by incoming data parsing.
    So, if some endpoints expect the same data – they might live
    in the same controller.

  Component
    Controllers parse data via components like
    :class:`~django_modern_rest.components.Body`
    or :class:`~django_modern_rest.components.Headers`.
    You can write your own components.

  Metadata
    A collection of all the things each :term:`Endpoint` accepts and returns.
    It is used for request parsing, response validation, and OpenAPI schema.

  Serializer
    :class:`~django_modern_rest.serialization.BaseSerializer` subclass
    that knows how to load and dump raw data into models.
    We have 2 bundled serializers in :ref:`plugins`\ : for ``pydantic``
    and ``msgspec``, you can write your own serializers for other libraries.

  Routing
    Routing is a mapping of URLs to controllers.
    If some controllers need the same URLs, but different data parsing, we can
    :ref:`compose <routing>` them.

Example:

.. literalinclude:: /examples/core_concepts/glossary.py
  :caption: views.py
  :linenos:
  :lines: 10-


.. _plugins:

Plugins
-------

To be able to support multiple :term:`serializer` models
like ``pydantic`` and ``msgspec``, we have a concept of a plugin.

There are several bundled ones, but you can write your own as well.
To do that see our advanced :ref:`serializer` guide.

As a user you are only interested in choosing the right plugin
for the :term:`controller` definition.

.. tabs::

    .. tab:: msgspec

      .. code:: python

        from django_modern_rest.plugins.msgspec import MsgspecSerializer

    .. tab:: pydantic

      .. code:: python

        from django_modern_rest.plugins.pydantic import PydanticSerializer


.. _routing:

Routing
-------

Our :term:`Controller` is built without knowing anything
about its future URL. Why so?

1. Because Django already has an amazing URL
   `routing system <https://docs.djangoproject.com/en/5.2/topics/http/urls/>`_
   and we don't need to duplicate it
2. Because all controllers might be used in multiple URLs,
   for example in ``api/v1`` and ``api/v2``. Our way allows any customizations

So, how do you compose different controllers with different parsing
behaviour into a single URL? For this we use
:func:`~django_modern_rest.routing.compose_controllers` function.
It composes different controllers with different parsing
strategies into a single one:

.. code:: python

  from django.urls import include, path
  from django_modern_rest import Router, compose_controllers

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
   This includes :ref:`meta <meta>` method for `OPTION` HTTP calls as well
2. All controllers have to be either sync or async,
   otherwise it would be hard to run them
3. Controllers must have the same :term:`serializer`,
   because otherwise parsing can probably error out
4. Controllers to be composed must have at least one endpoint

Controllers in ``django-modern-rest`` are not built
to be extended, but composed!


Returning responses
-------------------

By default, all responses are validated at runtime to match the schema.
This allows us to be super strict about schema generation as a pro,
but as a con, it is slower than can possibly be.

You can disable response validation via configuration:
per endpoint, per controller, and globally.


.. _meta:

Defining OPTIONS or meta method
-------------------------------

`RFC 9110 <https://www.rfc-editor.org/rfc/rfc9110.html#name-options>`_
defines the ``OPTIONS`` HTTP method, but sadly Django's
:class:`~django.views.generic.base.View` which we use as a base class
for all controllers, already have
:meth:`django.views.generic.base.View.options` method.

It would generate a typing error to redefine it with a different
signature that we need for our endpoints.

That's why we created ``meta`` controller method as a replacement
for older ``options`` name.

To use it you have two options:

1. Define the implementation yourself
2. Use :class:`~django_modern_rest.options_mixins.MetaMixin`
   or :class:`~django_modern_rest.options_mixins.AsyncMetaMixin`
   with the default implementation: provide ``Allow`` header
   with all the allowed HTTP method in this controller

When using :func:`~django_modern_rest.routing.compose_controllers`,
duplicate ``meta`` methods will be a import-time error. To solve this,
remove ``meta`` method from individual controllers
and use ``meta_mixin=`` keyword parameter to ``compose_controllers``.

Example:

.. code:: python

  from django_modern_rest import AsyncMetaMixin

  composed = compose_controllers(UserPut, UserPatch, meta_mixin=AsyncMetaMixin)

This will create an ``async def meta`` endpoint in the composed controller.
All methods from ``UserPut`` and ``UserPatch`` will be listed
in the response's ``Allow`` header.


Maximum integration with Django
-------------------------------

Works best with `django-stubs <https://github.com/typeddjango/django-stubs>`_.
Read next: our :doc:`integrations` guide.

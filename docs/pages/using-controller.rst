Using controller
================

:term:`Controller` is defined by the unity of incoming data.


Creating endpoints
------------------

Controllers consist of :class:`~django_modern_rest.endpoint.Endpoint` objects.
Each HTTP method is an independent endpoint.

The simplest way to create and endpoint is to define sync
or async method with the right name:

.. code:: python

  >>> from django_modern_rest import Controller
  >>> from django_modern_rest.plugins.pydantic import PydanticSerializer

  >>> class MyController(Controller[PydanticSerializer]):
  ...     def post(self) -> str:
  ...         return 'ok'

There will be several things that ``django-modern-rest`` will do for you here:

1. It will know that ``post`` endpoint will handle ``POST`` HTTP method,
   it is true for all HTTP methods, except :ref:`OPTIONS <meta>`.
2. It will know that ``post`` will return :class:`str` as a response type spec.
   There's **no** implicit type conversions in ``django-modern-rest``.
   If your endpoint declares something to be returned, it must return this type
3. It will infer the default status code for ``post``, which will be ``201``.
   All other endpoints would have ``200`` as the default
4. All this metadata will be used to validate responses from this endpoint.
   Returning ``[]`` from ``post`` would trigger
   :exc:`~django_modern_rest.exceptions.ResponseSerializationError`,
   unless :ref:`response_validation` is explicitly turned off
5. The same metadata will be used to render OpenAPI spec

``django-modern-rest`` never creates implicit methods for you.
No ``HEAD``, no :ref:`OPTIONS <meta>`,
if you need them – create them explicitly.

modify
~~~~~~

But, what if you need to add response headers? Or change the status code?
That's where :func:`~django_modern_rest.endpoint.modify` comes in handy:

.. code:: python

  >>> from http import HTTPStatus
  >>> from django_modern_rest import NewHeader, modify

  >>> class MyController(Controller[PydanticSerializer]):
  ...     @modify(
  ...         status_code=HTTPStatus.OK,
  ...         headers={'X-Handled-By': NewHeader(value='myapi')},
  ...     )
  ...     def post(self) -> str:
  ...         return 'ok'

Now we would:

1. Change the default inferred response status code from ``201``
   to explicitly set ``200``
2. Add a new header ``'X-Handled-By'`` with a static value ``'myapi'``

validate
~~~~~~~~

Ok, but what if we need full control over the response?
To return raw :class:`~django.http.HttpResponse` object,
we can use :func:`~django_modern_rest.endpoint.validate` decorator.
It will not modify anything, but will just attach metadata
to any endpoint that returns ``HttpResponse`` objects:

.. code:: python

  >>> from django.http import HttpResponse
  >>> from django_modern_rest import (
  ...     HeaderSpec, ResponseSpec, validate,
  ... )

  >>> class MyController(Controller[PydanticSerializer]):
  ...     @validate(
  ...         ResponseSpec(
  ...             str,
  ...             status_code=HTTPStatus.OK,
  ...             headers={'X-Handled-By': HeaderSpec()},
  ...         ),
  ...     )
  ...     def post(self) -> HttpResponse:
  ...         return self.to_response(
  ...             'ok',
  ...             status_code=HTTPStatus.OK,
  ...             headers={'X-Handled-By': 'myapi'},
  ...         )

This is the most verbose, but the most flexible
method of metadata specification.
Both ``@modify`` and ``@validate`` can specify multiple different
response descriptions (or "schemas"), if you need explicit cases for errors.

See :doc:`returning-responses` for more.


Composing Blueprints into Controllers
-------------------------------------

When modeling your endpoints and data, you might find yourself
in a situation when you would need to have different data
parsing rules for different endpoints on the same URL:

- ``GET /users`` does not a body and just returns the list of users
- ``POST /users`` requires a request body of some ``UserInput`` type
  to create a new user with the pre-defined set of fields

To achieve that we have a special composition primitive called
:class:`~django_modern_rest.controller.Blueprint`.

It is used to define parsing rules / :doc:`error handling <error-handling>`
for a set of endpoints that share the same logic.

Here's an example:

.. literalinclude:: /examples/using_controller/blueprints.py
  :caption: views.py
  :linenos:
  :lines: 13-

Unlike controllers, they can't be used in routing directly.
First, they need to be composed into a controller:

- Via :attr:`~django_modern_rest.controller.Controller.blueprints` attribute

.. literalinclude:: /examples/using_controller/compose_blueprints.py
  :caption: views.py
  :linenos:
  :lines: 12-

- Via :func:`~django_modern_rest.routing.compose_blueprints` function.
  See our :doc:`routing` guide for more details.


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

1. Define the ``meta`` endpoint yourself and provide an implementation
2. Use :class:`~django_modern_rest.options_mixins.MetaMixin`
   or :class:`~django_modern_rest.options_mixins.AsyncMetaMixin`
   with the default implementation: which provides ``Allow`` header
   with all the allowed HTTP methods in this controller

Here's an example of a custom ``meta`` implementation:

.. literalinclude:: /examples/using_controller/custom_meta.py
  :caption: views.py
  :linenos:


See how you can use :ref:`composed-meta`
with :func:`~django_modern_rest.routing.compose_blueprints`.


Customizing controllers
-----------------------

``Controller`` is built to be customized with a class-level API.
If you need granual control, you can change anything.

Here are feature that you can enable or disable easily:

- :attr:`~django_modern_rest.controller.Controller.enable_semantic_responses`
  set it to ``False`` to disable automatic responses metadata
  generation for component parsers, can be useful
  when you create your own exceptions handlers

Check out our API for the advanced features:

- :attr:`~django_modern_rest.controller.Controller.http_methods`
  to support custom HTTP methods like ``QUERY``
  or your custom DSLs on top of HTTP
- :attr:`~django_modern_rest.controller.Controller.endpoint_cls`
  to customize how endpoints are created
- :attr:`~django_modern_rest.controller.Controller.serializer_context_cls`
  to customize how model for serialization of incoming data is created


Next up
-------

.. grid:: 1 1 2 2
    :class-row: surface
    :padding: 0
    :gutter: 2

    .. grid-item-card:: :octicon:`comment-discussion` Returning responses
      :link: returning-responses
      :link-type: doc

      Learn how you can return a response from your endpoint.

    .. grid-item-card:: :octicon:`git-merge-queue` Routing
      :link: routing
      :link-type: doc

      Learn how routing works.

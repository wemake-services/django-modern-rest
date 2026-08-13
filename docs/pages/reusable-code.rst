Reusable code
=============

One of the worst things about the current generation of
Python REST frameworks is code re-usability.

- ``django-rest-framework`` is very flexible, but all the flexibility
  comes from importing fully qualified object's path
  strings taken from app's settings.
  It is very hard to properly type a code base like this.
  Using it is also really hard, because you can't easily
  navigate in your source code.
- ``fastapi`` does not even offer a way to write reusable code,
  because it is based on functions, which are really hard to reuse and modify.
  That's why you have to copy paste lots of code just to,
  for example, use the most common things such as JWT auth.

What does ``django-modern-rest`` offer instead?


.. _reusable-controllers:

Reusable controllers
--------------------

We offer a concept of a "reusable controllers".

To make a reusable controller, you need
to provide :class:`typing.TypeVar` instead of a
real :class:`~dmr.serializer.BaseSerializer` type.

Here's an example:

.. literalinclude:: /examples/reusable_code/reusable_controller.py
  :caption: views.py
  :linenos:
  :language: python

This code can work with both ``pydantic`` and ``msgspec`` as serializers.
Let's try to create two exact controllers with exact serializers:

.. tabs::

    .. tab:: msgspec

      .. literalinclude:: /examples/reusable_code/msgspec_controller.py
        :caption: views.py
        :linenos:
        :language: python

    .. tab:: pydantic

      .. literalinclude:: /examples/reusable_code/pydantic_controller.py
        :caption: views.py
        :linenos:
        :language: python

Basically - we just specify what kind of serializer to use. And that's it.
But, this is just the first step. We can do much more!


Generic parsing and response models
-----------------------------------

Next, let's define a reusable controller that will have:

- customizable serializer
- customizable request model
- customizable response body

The process will look exactly the same:

.. literalinclude:: /examples/reusable_code/reusable_parsing.py
  :caption: views.py
  :linenos:
  :language: python

Here we use 3 type variables. One of each of the parts we want to customize.

Important part here is that we defined our own abstract ``convert`` method
to convert unknown request model into an unknown response body.

We would need to implement this method in all of our concrete controllers.

.. tabs::

  .. tab:: msgspec

    .. literalinclude:: /examples/reusable_code/parsing_msgspec.py
      :caption: views.py
      :linenos:
      :language: python

  .. tab:: pydantic

    .. literalinclude:: /examples/reusable_code/parsing_pydantic.py
      :caption: views.py
      :linenos:
      :language: python

Note that ``msgspec`` and ``pydantic`` controllers in this
case have completely different request and response bodies
and completely different OpenAPI schemas.

We can completely customize each controller and all parsing components
and return type validation.

.. important::

  All schema generation and validation rules work
  the same way for concrete controllers.

  We infer the passed values during import time and use real types.

Real endpoints support
~~~~~~~~~~~~~~~~~~~~~~

.. versionadded:: 0.14.0

The same would work with endpoints defined
with :func:`~dmr.endpoint.validate` function.

The logic is the same, but syntax is a bit different.

.. tip::

  By default ``mypy`` and other type-checkers won't allow to write
  ``ResponseSpec(_TypeT, status_code=OK)``, because type vars can't be used
  in such places according
  to the `typing spec <https://typing.python.org/en/latest/#specification>`_.

  So, we provide :func:`dmr.types.safe_typevar` helper
  to get rid of the type-checking errors.

Here's how we can do the same example, but with ``@validate``.
The reusable part:

.. literalinclude:: /examples/reusable_code/validate_reusable.py
  :caption: views.py
  :linenos:
  :language: python

And then - implementations:

.. tabs::

  .. tab:: msgspec

    .. literalinclude:: /examples/reusable_code/validate_msgspec.py
      :caption: views.py
      :linenos:
      :language: python

  .. tab:: pydantic

    .. literalinclude:: /examples/reusable_code/validate_pydantic.py
      :caption: views.py
      :linenos:
      :language: python

This way offers you more controll over the response headers, cookies, etc.
Choose the one that fits best of the job.


Where is it actually helpful in practice?
-----------------------------------------

We use this feature a lot in the pre-defined views
we provide with the framework.

For example, we use this in :doc:`auth/jwt` obtain views:

1. :class:`~dmr.security.jwt.views.ObtainTokensSyncController`
   for sync controllers
2. :class:`~dmr.security.jwt.views.ObtainTokensAsyncController`
   for async controllers

Usage example:

.. literalinclude:: /examples/auth/jwt/jwt_obtain_tokens.py
  :caption: views.py
  :linenos:
  :language: python

Why is it useful?

1. We can work with any serializer
2. We can change our request payload to be whatever we need,
   it would be correctly rendered in the final OpenAPI schema
3. We can change the response schema,
   which would also be correctly rendered in the OpenAPI

This feature allows us to have type-safe
and OpenAPI-first approach to code reusability,
great DX, and Python-native abstractions.

Users / plugin developers can do the same
to provide universal customizable controllers.

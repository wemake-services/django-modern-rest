Reusable code
=============

One of the worst thing about current generation of
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
  for example, use JWT auth.

What does ``django-modern-rest`` offer instead?


Reusable controllers
--------------------

We offer a concept of a "reusable controllers"
(and "reusable blueprints" as well).

To make a reusable controller, you need
to provide :class:`typing.TypeVar` instead of a
real :class:`~django_modern_rest.serializer.BaseSerializer` type.

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
case have completely different request and response bodies.

We can completely customize each controller and all parsing components
and return type validation.

.. important::

  All schema generation and validation rules work
  the same way for concrete controllers.

  We infer the passed values during import time and use real types.

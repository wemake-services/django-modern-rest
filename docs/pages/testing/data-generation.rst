Structured data generation
==========================

Since ``django-modern-rest`` is already built around an idea
that we use models for everything, it is quite natural to reuse
these models for tests as well.

For example, one can use
`Polyfactory <https://polyfactory.litestar.dev/latest/>`_
to build test data from ``pydantic``, ``msgspec``,
``@dataclass``, or even ``TypedDict`` models.

Let's say you have this code for your controller, using ``pydantic`` models:

.. literalinclude:: /examples/testing/pydantic_controller.py
  :caption: views.py
  :language: python
  :linenos:

Let's reuse the models for data generation in tests!

.. literalinclude:: /examples/testing/polyfactory_usage.py
  :caption: test_user_create.py
  :language: python
  :linenos:

Which will make your tests simple, fast,
and will help you find unexpected corner cases.

You can use any library of your choice for data generation for your models.
